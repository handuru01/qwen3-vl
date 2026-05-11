"""
Qwen3-VL Web Service - FastAPI 백엔드
로컬 Ollama(:11434)의 qwen3-vl:8b 모델을 호출해 텍스트·이미지 멀티모달 채팅 응답을 반환한다.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ─── 설정 ────────────────────────────────────────────────────────────────────
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "180"))
MAX_IMAGE_BYTES: int = int(os.getenv("MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))  # 10 MB

STATIC_DIR = Path(__file__).parent / "static"


# ─── 요청/응답 모델 ───────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant | system")
    content: str
    images: list[str] = Field(
        default_factory=list,
        description="base64 인코딩 이미지 문자열 배열 (data URI 접두사 포함 가능)",
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    model: str


# ─── 앱 생명주기: httpx.AsyncClient를 앱 전역에서 재사용 ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="Qwen3-VL Web Service", lifespan=lifespan)


# ─── 이미지 유틸 ──────────────────────────────────────────────────────────────
def strip_data_uri(b64: str) -> str:
    """data URI 접두사(data:image/...;base64,)를 제거하고 순수 base64를 반환한다."""
    if "," in b64:
        return b64.split(",", 1)[1]
    return b64


def validate_image_size(b64: str, index: int) -> None:
    """base64 크기를 바이트로 추산해 제한을 초과하면 예외를 발생시킨다."""
    pure = strip_data_uri(b64)
    # base64는 원본 바이트의 약 4/3배 크기
    estimated = len(pure) * 3 // 4
    if estimated > MAX_IMAGE_BYTES:
        limit_mb = MAX_IMAGE_BYTES // 1024 // 1024
        actual_mb = estimated / 1024 / 1024
        raise HTTPException(
            status_code=413,
            detail=f"이미지 {index + 1}의 크기({actual_mb:.1f} MB)가 제한({limit_mb} MB)을 초과합니다.",
        )


def build_ollama_messages(messages: list[ChatMessage]) -> list[dict]:
    """Ollama API 포맷으로 메시지를 변환한다. 이미지는 순수 base64만 포함한다."""
    result = []
    for msg in messages:
        item: dict = {"role": msg.role, "content": msg.content}
        if msg.images:
            item["images"] = [strip_data_uri(img) for img in msg.images]
        result.append(item)
    return result


# ─── 헬스체크 ─────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health() -> dict:
    client: httpx.AsyncClient = app.state.client
    try:
        r = await client.get(f"{OLLAMA_HOST}/api/tags")
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama에 연결할 수 없습니다: {e}",
        )

    tags = r.json().get("models", [])
    model_names = [m.get("name", "") for m in tags]
    model_ready = any(name.startswith(OLLAMA_MODEL) for name in model_names)

    return {
        "ollama": "ok",
        "target_model": OLLAMA_MODEL,
        "model_ready": model_ready,
        "available_models": model_names,
    }


# ─── SSE 스트리밍 제너레이터 ──────────────────────────────────────────────────
async def stream_ollama(client: httpx.AsyncClient, payload: dict):
    """Ollama 스트리밍 응답을 SSE 포맷으로 변환한다."""
    try:
        async with client.stream(
            "POST", f"{OLLAMA_HOST}/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                done = data.get("done", False)
                yield f"data: {json.dumps({'token': token, 'done': done})}\n\n"
                if done:
                    return
    except httpx.HTTPError as e:
        yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"


# ─── 채팅 엔드포인트 ──────────────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages가 비어 있습니다.")

    # 모든 메시지의 이미지 크기 검증
    for msg in req.messages:
        for idx, img in enumerate(msg.images):
            validate_image_size(img, idx)

    client: httpx.AsyncClient = app.state.client
    payload = {
        "model": OLLAMA_MODEL,
        "messages": build_ollama_messages(req.messages),
        "stream": req.stream,
    }

    if req.stream:
        return StreamingResponse(
            stream_ollama(client, payload),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # 비스트리밍
    try:
        r = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Ollama 호출 실패: {e}")

    data = r.json()
    content = data.get("message", {}).get("content", "")
    return ChatResponse(response=content, model=OLLAMA_MODEL)


# ─── 정적 파일 서빙 ───────────────────────────────────────────────────────────
@app.get("/")
@app.get("/index.html")
async def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

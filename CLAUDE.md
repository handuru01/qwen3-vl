# Qwen3-VL Web Service by 김상민

## 개요
로컬 Ollama(http://localhost:11434)에 설치된 qwen3-vl:8b 모델을
웹 채팅 인터페이스로 노출하는 서비스.
텍스트 대화 외에 이미지를 업로드해 시각적 질문·분석이 가능하다.
외부에서 https://atpia.com/qwen3-vl/index.html 로 접속 가능.

## 기술 스택
- Backend: Python 3.11, FastAPI, httpx (Ollama API 호출), python-multipart (이미지 업로드)
- Frontend: 단일 HTML + Vanilla JS (의존성 최소화)
- 통신: REST + Server-Sent Events(SSE)로 스트리밍 응답
- 이미지 전달: 클라이언트에서 base64 인코딩 후 JSON 페이로드에 포함
- 배포: Apache reverse proxy + systemd (로컬), Docker 컨테이너화 가능

## qwen3:8b(텍스트)와의 차이점
| 항목 | qwen3:8b | qwen3-vl:8b |
|------|----------|-------------|
| 입력 | 텍스트 전용 | 텍스트 + 이미지(멀티모달) |
| 포트 | 8000 | 8001 |
| 서브패스 | /qwen/ | /qwen3-vl/ |
| 이미지 필드 | 없음 | messages[].images (base64 배열) |

## 환경
- OS: Ubuntu 26.04 LTS
- Python: 3.11 (conda env: ocr 또는 별도 venv)
- 작업 디렉토리(개발): /mnt/data/handuru/qwen3-vl
- 작업 디렉토리(운영): /var/www/atpia.com/public_html/qwen3-vl
- GPU: NVIDIA GTX 1070 8GB (Ollama가 자동 활용)

## 제약사항
- Hugging Face Transformers 직접 사용 금지 (Ollama가 추론 담당)
- GPU 코드 직접 작성 금지 (TensorRT, CUDA 호출 등)
- 모델 호출은 반드시 Ollama HTTP API 경유
- 외부 클라우드 API 호출 금지 (전부 로컬에서 동작)
- 코드 주석은 한국어, 변수/함수명은 영어
- 의존성은 requirements.txt에 명시, 가능한 한 최소화
- 이미지는 서버에 저장하지 않음: base64 변환 후 메모리에서만 처리
- 업로드 이미지 최대 크기: 10 MB (클라이언트 + 서버 양쪽 검증)

## 프로젝트 구조
```
qwen3-vl/
├── main.py              # FastAPI 앱 (이미지 멀티모달 지원)
├── requirements.txt     # Python 의존성
├── .env                 # 환경변수 파일 (systemd EnvironmentFile 참조)
├── CLAUDE.md            # 본 문서
├── Dockerfile           # 컨테이너 빌드
├── docker-compose.yml   # Docker Compose 설정
├── apache-qwen3-vl.conf # Apache reverse proxy 설정 참고용
├── qwen3-vl.service     # systemd 서비스 파일
├── conversation.txt     # 개발 대화 기록
└── static/
    └── index.html       # 채팅 UI (이미지 업로드 포함, 단일 파일)
```

## 실행 방법

### 로컬 개발
```bash
# 1) Ollama가 떠 있고 모델이 있는지 확인
curl http://localhost:11434/api/tags | grep qwen3-vl

# 2) 모델이 없으면 pull
ollama pull qwen3-vl:8b

# 3) 의존성 설치
pip install -r requirements.txt

# 4) 서버 기동 (포트 8001 — qwen3:8b 서비스와 충돌 방지)
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 5) 브라우저에서 접속
http://localhost:8001/index.html
```

### 운영 서버 배포
```bash
# 1) 파일 복사
cp -r /mnt/data/handuru/qwen3-vl/. /var/www/atpia.com/public_html/qwen3-vl/

# 2) 의존성 설치
cd /var/www/atpia.com/public_html/qwen3-vl
/home/handuru/miniconda3/bin/pip install -r requirements.txt

# 3) systemd 서비스 등록 및 부팅 자동시작 설정
sudo cp qwen3-vl.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qwen3-vl

# 4) Apache 설정 적용 (atpia.com-le-ssl.conf 에 추가 후)
sudo a2enmod proxy proxy_http headers
sudo systemctl reload apache2

# 5) 동작 확인
curl http://127.0.0.1:8001/api/health
```

### Docker
```bash
docker compose up --build
```

## API 설계

### POST /api/chat
멀티모달 채팅. 이미지는 base64 인코딩 문자열 배열로 전달한다.

요청 바디:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "이 이미지에 무엇이 있나요?",
      "images": ["<base64_string>", "..."]
    }
  ],
  "stream": true
}
```
- `images` 필드는 선택(생략 시 텍스트 전용 대화)
- 이미지는 클라이언트에서 FileReader API로 base64 변환 후 전송
- 응답(비스트리밍): `{"response": "...", "model": "qwen3-vl:8b"}`
- 응답(스트리밍): SSE — `data: {"token": "...", "done": false|true}`

### GET /api/health
Ollama 연결 상태 및 모델 존재 여부 확인.
```json
{
  "ollama": "ok",
  "target_model": "qwen3-vl:8b",
  "model_ready": true,
  "available_models": ["qwen3-vl:8b", "qwen3:14b", "qwen3:8b"]
}
```

### GET / 또는 GET /index.html
`static/index.html` 반환.

### GET /static/*
정적 파일 서빙.

## Ollama 호출 규약
- 엔드포인트: `http://localhost:11434/api/chat`
- 모델명: `qwen3-vl:8b` (환경변수 `OLLAMA_MODEL`로 변경 가능)
- 이미지 필드: Ollama messages 포맷의 `images` 배열 (순수 base64, data URI 접두사 제거)
- 타임아웃: 180초 (이미지 처리 시간 고려, 환경변수 `REQUEST_TIMEOUT`으로 변경 가능)

Ollama API 페이로드 예시:
```json
{
  "model": "qwen3-vl:8b",
  "messages": [
    {
      "role": "user",
      "content": "이미지를 설명해 주세요.",
      "images": ["iVBORw0KGgoAAAANS..."]
    }
  ],
  "stream": true
}
```

## Apache reverse proxy 설정
atpia.com-le-ssl.conf 에 추가:

```apache
# ── Qwen3-VL FastAPI (uvicorn @ 127.0.0.1:8001) ──────────
ProxyPreserveHost On
ProxyPass        /qwen3-vl/ http://127.0.0.1:8001/ flushpackets=on timeout=185
ProxyPassReverse /qwen3-vl/ http://127.0.0.1:8001/
LimitRequestBody 15728640
# ─────────────────────────────────────────────────────────
```

- `flushpackets=on`: SSE 스트리밍 시 Apache 버퍼링 비활성화
- `timeout=185`: uvicorn 180초 타임아웃보다 5초 크게 설정
- `LimitRequestBody 15728640`: 15 MB (10 MB + base64 오버헤드 33%)
- 외부 접속 URL: https://atpia.com/qwen3-vl/index.html

## 환경변수
환경변수는 `.env` 파일로 관리하며, systemd 서비스에서 `EnvironmentFile=`로 참조한다.

| 변수명           | 기본값                   | 설명                         |
|-----------------|-------------------------|------------------------------|
| OLLAMA_HOST     | http://localhost:11434  | Ollama 서버 주소              |
| OLLAMA_MODEL    | qwen3-vl:8b             | 사용 모델명                   |
| REQUEST_TIMEOUT | 180                     | 요청 타임아웃(초)             |
| MAX_IMAGE_BYTES | 10485760                | 업로드 이미지 최대 크기(10MB) |
| APP_PORT        | 8001                    | uvicorn 기동 포트             |

## systemd 서비스 주요 설정
- `After=network-online.target`: 네트워크 완전 연결 후 기동
- `Wants=ollama.service`: Ollama 먼저 기동 보장
- `EnvironmentFile=.env`: 환경변수 파일 참조
- `Restart=always`: 어떤 이유로든 종료 시 자동 재시작
- `TimeoutStartSec=60`: 부팅 직후 Ollama 로드 시간 고려

부팅 자동시작 등록:
```bash
sudo systemctl enable qwen3-vl
```

## 구현 로드맵
1. [x] `/api/chat` 동기 호출 + 텍스트 전용 (qwen3:8b 서비스 포팅)
2. [x] SSE 스트리밍 지원
3. [x] 이미지 업로드 UI (드래그&드롭, 클립보드 붙여넣기, 파일 선택)
4. [x] 멀티모달 메시지 전송 (이미지 + 텍스트 혼합)
5. [x] 채팅 히스토리에 이미지 썸네일 표시
6. [x] 멀티턴 대화에서 이미지 포함 메시지 히스토리 관리
7. [x] Dockerfile + docker-compose
8. [x] systemd 서비스 파일 (부팅 자동시작 포함)

## 프론트엔드 주요 기능
- 이미지 업로드: 파일 선택 버튼, 드래그&드롭, 클립보드 Ctrl+V 지원
- 이미지 미리보기: 전송 전 썸네일로 확인, 개별 제거 가능
- 채팅 버블 안에 이미지 썸네일 표시 (클릭 시 라이트박스 확대)
- 스트리밍/비스트리밍 토글
- `<think>` 블록 자동 감지 → 접을 수 있는 "생각 중…" 섹션
- 스트리밍 중 타이핑 커서 애니메이션
- Enter 전송 / Shift+Enter 줄바꿈
- API_BASE 자동 감지: 서브패스 배포 시에도 올바른 경로로 API 호출

## 코딩 스타일
- 함수 단위로 작게 쪼갤 것
- 타입 힌트 필수 (Python 3.11 문법: `list[str]`, `dict | None` 등)
- async 함수에는 비동기 클라이언트(httpx.AsyncClient)만 사용
- 에러는 HTTPException으로 변환해 클라이언트에 전달
- 이미지는 서버 디스크에 저장하지 않고 메모리에서만 처리
- 주석은 한국어

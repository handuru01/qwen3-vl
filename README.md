# Qwen3-VL Multimodal Chat Web Service

This is a chat service that allows you to use the **qwen3-vl:8b** vision-language model, which runs on local Ollama, directly in your web browser.  
In addition to text conversations, you can upload images to ask visual questions and perform analysis.

**🌐 Demo:** https://atpia.com/qwen3-vl/index.html  
**🇰🇷 한국어:** [README.ko.md](README.ko.md)

---

## Key Features

- **Multimodal Input** — Simultaneous processing of text and images (qwen3-vl:8b)
- **3 Ways to Attach Images** — File selection button / Drag & Drop / Clipboard (Ctrl+V)
- **Real-time Streaming** — Token-by-token responses via Server-Sent Events (SSE)
- **`<think>` Block UI** — Displays the model's thought process in a collapsible section
- **Image Lightbox** — Click a thumbnail in a chat bubble to enlarge it
- **Multi-turn Conversations** — Maintains conversation history, including images
- **Subpath Deployment Support** — Automatically detects API paths in reverse proxy environments
- **Fully Local Operation** — No external cloud APIs; local GPU inference

---

## Screenshots

> Screen showing how to attach an image and ask a question in the browser

---

## Tech Stack

| Area | Technology |
|------|------------|
| AI Inference | [Ollama](https://ollama.com) + qwen3-vl:8b |
| Backend | Python 3.11, FastAPI, httpx, uvicorn |
| Frontend | HTML5 + Vanilla JS (single-file) |
| Communication | REST API + SSE streaming |
| Deployment | Apache reverse proxy + systemd |

---

## Requirements

- Install and run [Ollama](https://ollama.com)
- Python 3.11+
- NVIDIA GPU (optional; works on CPU but is slow)

---

## Quick Start

### 1. Prepare the Ollama model

```bash
ollama pull qwen3-vl:8b
```

### 2. Clone the repository and install dependencies

```bash
git clone https://github.com/handuru01/qwen3-vl.git
cd qwen3-vl
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
cp .env.example .env
# Modify the .env file if necessary
```

### 4. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 5. Access via browser

```
http://localhost:8001/index.html
```

---

## Running with Docker

```bash
docker compose up --build
```

> To access the host's Ollama from the container, `extra_hosts: host.docker.internal:host-gateway` is configured in docker-compose.yml.

---

## Environment Variables

Copy `.env.example` to `.env` and modify as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `qwen3-vl:8b` | Model name |
| `REQUEST_TIMEOUT` | `180` | Request timeout (seconds) |
| `MAX_IMAGE_BYTES` | `10485760` | Max upload image size (10MB) |
| `APP_PORT` | `8001` | uvicorn port |

---

## API

### `POST /api/chat`

```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is in this image?",
      "images": ["<base64_string>"]
    }
  ],
  "stream": true
}
```

- `images` field is optional (omit for text-only conversation)
- Streaming response: `data: {"token": "...", "done": false|true}`
- Non-streaming response: `{"response": "...", "model": "qwen3-vl:8b"}`

### `GET /api/health`

```json
{
  "ollama": "ok",
  "target_model": "qwen3-vl:8b",
  "model_ready": true,
  "available_models": ["qwen3-vl:8b"]
}
```

---

## Production Deployment (Apache + systemd)

### Apache Reverse Proxy

Add to `/etc/apache2/sites-available/your-site.conf`:

```apache
ProxyPreserveHost On
ProxyPass        /qwen3-vl/ http://127.0.0.1:8001/ flushpackets=on timeout=185
ProxyPassReverse /qwen3-vl/ http://127.0.0.1:8001/
LimitRequestBody 15728640
```

### Register systemd Service

```bash
sudo cp qwen3-vl.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qwen3-vl
```

> Update the `ExecStart` path and `WorkingDirectory` in the service file to match your environment.

---

## Project Structure

```
qwen3-vl/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── Dockerfile
├── docker-compose.yml
├── apache-qwen3-vl.conf    # Apache config reference
├── qwen3-vl.service        # systemd service file
├── docs/                   # Documentation & reports
└── static/
    └── index.html          # Chat UI
```

---

## Constraints

- Images are processed in memory only — never saved to disk
- Max 4 images / 10 MB per message (validated on both client and server)
- All model inference goes through the Ollama HTTP API (no direct GPU code)

---

## Developer

**Sangmin Kim (김상민)**  
- Service: https://atpia.com/qwen3-vl/index.html  
- GitHub: https://github.com/handuru01

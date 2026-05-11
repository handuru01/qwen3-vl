# Qwen3-VL Multimodal Chat Web Service

This is a chat service that allows you to use the **qwen3-vl:8b** vision-language model, which runs on local Ollama, directly in your web browser.  
In addition to text conversations, you can upload images to ask visual questions and perform analysis.

**🌐 Demo:** https://atpia.com/qwen3-vl/index.html

---

## Key Features

- **Multimodal Input** — Simultaneous processing of text and images (qwen3-vl:8b)
- **3 Ways to Attach Images** — File selection button / Drag & Drop / Clipboard (Ctrl+V)
- **Real-time Streaming** — Token-by-token responses via Server-Sent Events (SSE)
- **`<think>` Block UI** — Displays the model’s thought process in a collapsible section
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
|------|------|
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

### 3. Set Environment Variables

```bash
cp .env.example .env
# Modify the .env file if necessary
```

### 4. Run the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 5. Access via Browser

```
http://localhost:8001/index.html
```

---

## Running with Docker

```bash
docker compose up --build
```

> To access the host's Ollama from the container, set `extra_hosts: host.docker.internal

Translated with DeepL.com (free version)

## Hesper Agent Mail (Aion)

A command-line app that reads IMAP emails and summarizes them using small language models (Small LLMs). Designed to run smoothly on a Raspberry Pi 5 (8 GB RAM). The app uses Ollama to run lightweight chat models and LangGraph to orchestrate a simple tool-calling flow.

### Highlights
- **Fast with small models**: Default model is `qwen2.5:3b` (Ollama), which runs smoothly on a Raspberry Pi 5 (8 GB).
- **Safe IMAP access**: Lists unread emails with `imap-tools` and summarizes a selected email.
- **LangGraph flow**: The model calls `list_unread_emails` and `summarize_email` tools when needed.

---

## Architecture at a Glance

- Two tools are defined in `main.py`:
  - `list_unread_emails`: Returns unread emails as JSON with `uid`, subject, date, and sender.
  - `summarize_email`: Summarizes the email body for a given `uid`.
- Model setup:
  - Two `init_chat_model` instances are used via Ollama: one for chat (tool-calling), one raw.
  - Default model is `qwen2.5:3b`. You can target a remote or local Ollama with `OLLAMA_HOST`.
- CLI loop: You type instructions, the graph runs, and the model calls tools when appropriate.

---

## Hardware and Model Suggestions (Raspberry Pi 5, 8 GB)

- On **Raspberry Pi 5 (8 GB)**, the following small models (Ollama) work well:
  - `qwen2.5:3b` (default) → Good quality/speed balance, supports tool-calling.
  - `phi3:3.8b` or `phi3:3.8b-mini` → Lightweight and fast; decent summarization quality.
  - `llama3.2:3b` → General-purpose; good speed.
  - `mistral:7b` → Heavier; can run at the edge of 8 GB. Prefer 3B class for responsiveness.

Tip: 3B-class models are the sweet spot on Pi 5. 7B+ models will be slower and closer to memory limits.

---

## Setup

### 1) Prerequisites

This project uses `uv` (a fast Python package manager) and Python 3.13.

```bash
# Install uv (Linux/ARM64 - Raspberry Pi OS example)
curl -LsSf https://astral.sh/uv/install.sh | sh

# If Python 3.13 is not available, install it via uv (optional)
uv python install 3.13
```

### 2) Clone and prepare the environment

```bash
git clone <this-repo-url> hesper-agent-mail
cd hesper-agent-mail

# Create the virtual environment and install deps
uv sync
```

`pyproject.toml` includes the core deps: `imap-tools`, `langchain`, `langchain-ollama`, `langgraph`, `python-dotenv`.

### 3) Install Ollama and pull a model

Install Ollama for Raspberry Pi 5 (ARM64):

```bash
# Install Ollama (Linux ARM64)
curl -fsSL https://ollama.com/install.sh | sh

# Start the service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull at least the default model
ollama pull qwen2.5:3b

# Optional lightweight alternatives
ollama pull phi3:3.8b
ollama pull llama3.2:3b
```

By default, Ollama listens on `http://127.0.0.1:11434`. If you use a remote Ollama host, configure it via `.env`.

### 4) Environment variables (.env)

The app reads IMAP and Ollama settings from `.env`:

```env
# IMAP
IMAP_HOST=imap.yourmail.com
IMAP_USER=example@yourmail.com
IMAP_PASSWORD=app_specific_password

# Ollama (usually not needed for local)
OLLAMA_HOST=http://127.0.0.1:11434
```

Tip: Providers like Gmail/Outlook often require an **app password**. Regular account passwords usually do not work for IMAP. Ensure IMAP access is enabled.

---

## Run

```bash
# Ensure you are inside the virtual environment
uv run python main.py

# or
python main.py
```

On start, the app prints the model and Ollama `base_url`. Then you can type natural language commands. Example flow:

- Type something like "List unread emails" → the model calls the `list_unread_emails` tool.
- Pick a UID from the output and say "Summarize UID 123" → the model calls `summarize_email` and prints a short summary.

Tips:
- Even with small models, be explicit: e.g., "List the last 10 unread emails".
- Specify whether you want a short or more detailed summary.

---

## Configuration

- Default model is `qwen2.5:3b`. You can adjust `CHAT_MODEL` in `main.py`.
- For a remote Ollama server, set `.env` `OLLAMA_HOST` like `http://<server-ip>:11434`.

Performance tuning (Ollama env vars):
- `OLLAMA_NUM_THREADS`: Match your CPU core count (e.g., 4–8 on Pi 5).
- `OLLAMA_NUM_PARALLEL`: Parallel token processing; keep small on low-power devices.

Raspberry Pi 5 tips:
- 3B models are ideal for balance. 7B+ models get slow and memory-heavy.
- Increasing swap can help but may reduce SD card lifespan. Prefer a USB 3.0 SSD.

---

## Security

- Never commit your `.env`.
- Use least-privilege app passwords for IMAP.
- If using a remote Ollama server, restrict network access and secure it properly.

---

## Troubleshooting

- "IMAP connection error":
  - Verify host, username, and app password.
  - Ensure IMAP is enabled in your provider's settings.

- "Model is unresponsive / too slow":
  - Try a lighter model (`phi3:3.8b`, `llama3.2:3b`).
  - Lower `OLLAMA_NUM_THREADS` and `OLLAMA_NUM_PARALLEL`.
  - Close heavy background tasks.

- "Cannot reach Ollama":
  - Check service status: `systemctl status ollama`.
  - Ping the API: `curl http://127.0.0.1:11434`.
  - If remote: verify `.env` `OLLAMA_HOST`.

---

## Development Notes

- `langchain`, `langchain-ollama`, and `langgraph` compose a simple tool-calling graph.
- `list_unread_emails` fetches headers only (`headers_only=True`) and does not mark as seen (`mark_seen=False`).
- `summarize_email` uses plain text body or falls back to HTML and prompts the raw model for a concise summary.

---

## License

Unless otherwise noted at the project root, assume a permissive MIT-style intent. You are responsible for complying with licenses/usage terms of the models and your email provider.

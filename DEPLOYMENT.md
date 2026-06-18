# Deployment Checklist

Required environment variables

- `SESSION_SECRET` — required. Flask session secret key (no default). Use a strong random value.

Optional environment variables

- `CHAT_LOG_PATH` — path for chat logs file. Default: `chat_logs.jsonl`.
- `ENABLE_CHAT_LOGS` — set to `1` to enable saving chat logs (default: `0`).
- `LOGS_PASSWORD` — optional password used by the logs UI if enabled.
- `LOGS_PER_PAGE` — pagination size for logs (default: `20`).
- `LOGS_POLL_INTERVAL` — frontend polling interval in seconds (default: `1.5`).
- `ENABLE_THINKING_MODE` — default DeepSeek thinking mode. `1` = enabled, `0` = disabled. Default: `1`.
- `DEEPSEEK_API_BASE` — override DeepSeek API base URL. Default: `https://api.deepseek.com`.
- `RATE_LIMIT_WINDOW` — seconds window for internal rate limiting (default: `60`).
- `MAX_CALLS_PER_MINUTE` — internal max calls per minute for certain endpoints (default: `10`).

Security notes

- Do not enable `ENABLE_CHAT_LOGS` in production unless you have a secure storage and access controls for logs (they may contain sensitive data).
- Always set a strong `SESSION_SECRET` when deploying publicly.
- If running multiple workers, use a shared file system and enable `portalocker` to avoid log corruption.

Quick example (bash) to set env and run with Gunicorn:

```bash
export SESSION_SECRET="replace_with_strong_secret"
export ENABLE_CHAT_LOGS=0
export ENABLE_THINKING_MODE=1
export CHAT_LOG_PATH="/var/lib/buzzbuuzz/chat_logs.jsonl"

# run locally with Flask for debug
python app.py

# or run production with gunicorn
gunicorn -w 2 -b 0.0.0.0:8080 wsgi:app
```

Troubleshooting

- If DeepSeek returns 400 errors mentioning `thinking` payloads, ensure client requests do not send raw booleans; the proxy maps booleans to the required structured object, but custom client payloads may need to follow the API docs.
- If you see unexpected model names, verify `DEFAULT_MODELS` includes the current DeepSeek v4 names; update `DEFAULT_MODELS` if DeepSeek adds new public model IDs.

Contact

- For DeepSeek billing/limits questions, check the official docs or contact `api-service@deepseek.com`.

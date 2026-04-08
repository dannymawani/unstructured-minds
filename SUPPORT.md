# Support

## Getting Help

Before opening an issue, please check the resources below — your question may already be answered.

### 📖 Documentation

| Resource | Description |
|----------|-------------|
| [README](README.md) | Overview, quick start, and configuration |
| [`.env.example`](.env.example) | All environment variables with comments |
| [`docs/`](docs/) | Self-hosting, LAN access, security |
| [`ai_docs/`](ai_docs/) | Deep technical reference (architecture, schemas, APIs) |

### 💬 GitHub Discussions

The best place to ask questions, share your setup, or discuss ideas:

👉 **[github.com/dannymawani/unstructured-minds/discussions](https://github.com/dannymawani/unstructured-minds/discussions)**

- **Q&A** — Ask anything about setup, configuration, or usage
- **Show & tell** — Share your setup or use case
- **Ideas** — Propose features or improvements

### 🐛 Bug Reports

If something is broken, please [open an issue](https://github.com/dannymawani/unstructured-minds/issues/new/choose) using the bug report template.

Include:
- Your OS, browser, and Docker version
- Storage mode (`local` or `postgres`)
- LLM provider (or `none`)
- Steps to reproduce
- Any relevant logs (`docker compose logs backend`)

### 💡 Feature Requests

Use the [feature request template](https://github.com/dannymawani/unstructured-minds/issues/new/choose) to propose new features or improvements.

---

## Common Issues

### Docker won't start

```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Rebuild from scratch
docker compose down -v
docker compose up --build
```

### AI features aren't working

1. Check your `.env` has `LLM_PROVIDER` and `LLM_API_KEY` set correctly
2. Verify via the settings page in the app (⚙️ icon)
3. For Ollama: make sure `ollama serve` is running before starting the app

### Vault notes not showing

Check `VAULT_PATH` in your `.env` points to the correct directory. Default is `./vault` relative to the project root.

### Postgres connection issues

Make sure `DATABASE_URL` is set and `STORAGE_MODE=postgres` in your `.env`. For the bundled Postgres:

```bash
docker compose --profile postgres up --build
```

---

## Professional Support

This is a personal open-source project. Professional or paid support is not available.

Community support is best-effort and provided by the maintainer and contributors in their free time. We appreciate your patience!

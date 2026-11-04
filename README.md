# AIRA — source for review (sanitized)

Private review copy of the AIRA application source, prepared for
independent analysis. This repo is review-only: nothing here deploys
or runs against live systems by itself.

Sanitization applied before push:
- Real `.env` excluded (only `.env.example` template included).
- Backup files (`.bak`) excluded.
- One historical local-dev database password mentioned in build notes
  redacted to a placeholder.
- No API keys, tokens, private keys, or wallet credentials are
  included. Any key-shaped value found by scan was removed or is a
  template/variable reference only.

Stack: Python backend (`api.py`, `src/`), Next.js frontend
(`frontend/`), Postgres migrations (`migrations/`, `infra/`), tests.

# Deploying on cPanel (Python hosting)

Layout: static frontend in `public_html/`, FastAPI mounted at `/api` through cPanel's **Setup Python App** (Passenger). Same origin, so no CORS or cookie changes. The VPS setup (`infra/setup-vps.sh`) is unchanged.

**Shortcut:** `python infra/cpanel/package.py` does steps 1-2 below and writes `dist/cpanel/frontend.zip` (unzip into the domain's document root) and `dist/cpanel/backend.zip` (unzip into `~/astronode/backend`). Then continue at step 3.

## 1. Build the frontend locally

```bash
cd frontend
npm ci
npm run build          # leave VITE_BACKEND_URL empty -> same-origin /api
```

Upload everything inside `frontend/dist/` to `public_html/` (File Manager or FTP), then copy [`htaccess`](htaccess) to `public_html/.htaccess`.

## 2. Upload the backend

Upload `backend/` to a folder **outside** `public_html`, e.g. `~/astronode/backend`. Skip `venv/`, `tests/`, `data/`, `.env*`. The `ephe/` folder (`*.se1`) must come along: calculations silently fail without it.

## 3. Create the Python app

cPanel > **Setup Python App** > Create Application:

| Field | Value |
|---|---|
| Python version | newest offered (3.10+ required; CI uses 3.12) |
| Application root | `astronode/backend` |
| Application URL | `astronode.in/api` |
| Startup file | `passenger_wsgi.py` |
| Entry point | `application` |

Then in the same screen:

1. **Configuration files** > add `requirements.txt` > **Run Pip Install**. (No SSH needed. `pyswisseph` needs a prebuilt wheel or a compiler on the host; if the install fails on it, ask the host to enable one.)
2. **Environment variables** (the UI replaces `.env.local`): `CORS_ORIGINS=https://astronode.in`, and optionally `SESSION_SECRET` (enables accounts; keep it stable), `API_KEYS`, Stripe / Google / Resend keys. Leave `SESSION_SECRET` unset to run without accounts.
3. **Restart**. After any later upload, restart again (or `touch tmp/restart.txt` in the app root).

Check `https://astronode.in/api/health`.

## What differs from the VPS

- `passenger_wsgi.py` wraps the ASGI app with `a2wsgi`. Requests run in Passenger's workers instead of uvicorn, so expect somewhat lower concurrency.
- PDFs render in-process (`PDF_IN_PROCESS=1` is set by the shim) instead of in a spawned worker process.
- `/metrics` and Grafana are not routed (Passenger only serves `/api`).
- The accounts SQLite file lives in `backend/data/app.db`, inside the app root. Back it up, or configure the D1 mirror (`python -m accounts.backup sync`) via a cPanel cron job if you have shell/cron access.
- Nginx security headers (CSP etc.) are not applied; `htaccess` only adds a minimal set. Add a CSP header there if needed.
- The Cloudflare / nginx `/health` alias does not exist; use `/api/health`.

## Automated deploys (GitHub Actions)

`.github/workflows/deploy-cpanel.yml` runs after CI passes on `main` (or manually from the Actions tab). It builds the frontend, uploads `frontend/dist` and `backend/` over explicit FTPS, uploads `tmp/restart.txt` so Passenger restarts, and checks `/api/health`.

Settings > Secrets and variables > Actions:

| Kind | Name | Value |
|---|---|---|
| Secret | `FTP_HOST` | your cPanel FTP server |
| Secret | `FTP_USERNAME` | the FTP account |
| Secret | `FTP_PASSWORD` | its password |
| Variable | `FTP_FRONTEND_DIR` | document root of the domain, relative to the FTP account's home, ending in `/` |
| Variable | `FTP_BACKEND_DIR` | the Python app root, e.g. `astronode/backend/` |

Not automated: `pip install`. When `backend/requirements.txt` changes the run prints a warning; click **Run Pip Install** in Setup Python App, then Restart. `backend/data/` and `.env*` are never uploaded, so the live database and settings are untouched.

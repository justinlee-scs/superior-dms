# DMS API Deployment Guide (Local + Company Intranet)

This project is a FastAPI-based Document Management System API backed by PostgreSQL.

Use this guide to:
- run it locally for development
- deploy it on another Linux server so everyone in your company can use it on your internal network

## 1. What This App Requires

- Python 3.10+
- PostgreSQL 14+
- `tesseract-ocr` (OCR engine)
- Poppler utilities (`pdftoppm`) for `pdf2image`
- Reverse proxy (Nginx) for HTTPS and stable public endpoint

## 2. Copy Project to a New Machine

```bash
git clone <your-repo-url> dms
cd dms
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Install OS Dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y \
  postgresql postgresql-contrib \
  tesseract-ocr \
  poppler-utils \
  nginx
```

## 4. Create PostgreSQL Database and User

```bash
sudo -u postgres psql
```

Inside `psql`:

```sql
CREATE USER dms_user WITH PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';
CREATE DATABASE dms OWNER dms_user;
GRANT ALL PRIVILEGES ON DATABASE dms TO dms_user;
\q
```

## 5. Configure Environment Variables

Copy the example file and edit values:

```bash
cp .env.example .env
```

Set at least:
- `APP_ENV=production`
- `DATABASE_URL=postgresql+psycopg://dms_user:<password>@127.0.0.1:5432/dms`
- `JWT_SECRET=<long-random-secret>`
- `CORS_ALLOW_ORIGINS=https://dms.company.local`

Generate a secure JWT secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## 6. Run the API Once (Smoke Test)

```bash
source .venv/bin/activate
set -a && source .env && set +a
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

From another terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

## 7. Bootstrap Admin/RBAC Data

Use your existing scripts as needed:

```bash
source .venv/bin/activate
set -a && source .env && set +a
python scripts/bootstrap_admin.py
python scripts/seeds_for_rbac.py
```

If your seed flow differs, run your internal bootstrap process here before exposing to users.

## 8. Run as a Systemd Service

Create `/etc/systemd/system/dms-api.service`:

```ini
[Unit]
Description=DMS FastAPI Service
After=network.target

[Service]
User=justinlee
Group=www-data
WorkingDirectory=/home/justinlee/dms
EnvironmentFile=/home/justinlee/dms/.env
ExecStart=/home/justinlee/dms/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Start and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dms-api
sudo systemctl status dms-api
```

## 9. Put Nginx in Front (Internal HTTPS)

Create `/etc/nginx/sites-available/dms`:

```nginx
server {
    listen 80;
    server_name dms.company.local;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name dms.company.local;

    ssl_certificate /etc/ssl/certs/dms.company.local.crt;
    ssl_certificate_key /etc/ssl/private/dms.company.local.key;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable config:

```bash
sudo ln -s /etc/nginx/sites-available/dms /etc/nginx/sites-enabled/dms
sudo nginx -t
sudo systemctl reload nginx
```

## 10. Restrict Access to Company Network

Example with UFW (adjust subnet):

```bash
sudo ufw allow from 10.0.0.0/8 to any port 443 proto tcp
sudo ufw deny 443/tcp
sudo ufw enable
sudo ufw status
```

Also ensure DNS for `dms.company.local` points to this server IP.

## 11. Access for Users

- API base URL: `https://dms.company.local`
- Health check: `https://dms.company.local/health`
- Interactive API docs: `https://dms.company.local/docs`

## 12. Production Checklist

- Set strong `JWT_SECRET` and DB password.
- Keep `APP_ENV=production`.
- Set `CORS_ALLOW_ORIGINS` to real frontend/internal URLs only.
- Run migrations during deploy: `alembic upgrade head`.
- Configure database backups and test restore.
- Monitor service logs:

```bash
sudo journalctl -u dms-api -f
```

## 13. Notes About Current Implementation

- Database schema is managed with Alembic migrations.
- Processing endpoints now queue work in-process using background threads.
- For higher volume, move processing to a dedicated queue/worker service (Redis + RQ/Celery or similar).

## 14. Alembic Migration Workflow

Use this workflow whenever models change.

Create a migration:

```bash
source .venv/bin/activate
set -a && source .env && set +a
alembic revision --autogenerate -m "describe_change"
```

Review the generated file in `app/db/migrations/versions/` before applying it.

Apply migrations:

```bash
alembic upgrade head
```

Show current migration:

```bash
alembic current
```

Rollback one revision:

## 15. Optional Integrations (Disabled by Default)

The repository now includes scaffold code for:
- S3/MinIO object storage backend (`app/storage/backends.py`)
- OpenCV preprocessing (`app/services/extraction/opencv_preprocess.py`)
- HuggingFace TrOCR provider (`app/services/extraction/trocr_hf_provider.py`)
- Label Studio API client + sync script (`app/services/labelstudio/client.py`, `scripts/labelstudio_sync.py`)

Runtime status:
- MinIO/S3, TrOCR HF, OpenCV, and Label Studio wiring are all placeholders only (commented/disabled).
- Enable them after review by uncommenting the noted blocks.
- `app/services/extraction/ocr_sync.py`
- `app/api/documents.py` (Label Studio hooks only)

To activate after review:
1. Install optional dependencies from `requirements.txt` (currently commented).
2. Configure optional env vars from `.env.example`.
3. Uncomment the marked "Optional (disabled)" blocks in the files above.

```bash
alembic downgrade -1
```

### Deploy Upgrade Sequence

1. Pull latest code on server.
2. Activate venv and install dependencies.
3. Load env vars.
4. Run `alembic upgrade head`.
5. Restart `dms-api` service.

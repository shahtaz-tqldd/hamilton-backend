# Hamilton Backend

FastAPI backend for privately organizing code snippets, encrypted environment variables, and uploaded files. PostgreSQL stores metadata, while file bodies are stored in Cloudflare R2.

## Features

- Email/password registration and JWT access/refresh tokens
- Email verification and password reset using expiring, single-use OTPs
- One automatic `Default` folder per account plus user-created, single-level folders
- CRUD APIs for code snippets
- Fernet-encrypted environment variable values; normal responses always show `********`
- Explicit authenticated reveal endpoint for decrypted values
- Multipart uploads to Cloudflare R2, SHA-256 checksums, private presigned downloads
- A combined paginated item listing across snippets, variables, and files
- Async PostgreSQL access with SQLAlchemy and Alembic migrations
- Docker development and production entrypoints

## Quick start with Docker

1. Create local configuration:

   ```bash
   cp .env.example .env
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

2. Put the generated value in `FERNET_KEY`, replace `SECRET_KEY`, then add your Cloudflare R2 and SMTP credentials.

3. Start the API and PostgreSQL:

   ```bash
   docker compose -f docker/docker-compose.yml up --build
   ```

4. Open Swagger UI at <http://localhost:8000/docs>. The health endpoint is `GET /health`.

Import [the Postman collection](<postman/Hamilton API.postman_collection.json>) and
[local Postman environment](<postman/Hamilton API.postman_environment.json>) for documented,
ready-to-run requests. The collection automatically stores authentication tokens and resource IDs.

The Docker entrypoint applies Alembic migrations before starting the server. In development it uses Uvicorn reload; when `APP_ENV=production`, it starts Gunicorn.

## Local start

Use Python 3.11 or newer and a reachable PostgreSQL database:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
./startapp.sh
```

`startapp.sh` runs migrations and starts the API. Its default database hostname is intended for Docker, so use `localhost` in `DATABASE_URL` when PostgreSQL runs locally.

## API overview

All application routes use the `/api/v1` prefix.

| Area | Important endpoints |
| --- | --- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/verify-otp`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/refresh`; `GET /auth/me` |
| Folders | `POST/GET /folders`, `DELETE /folders/{id}` |
| Snippets | `POST/GET /snippets`, `GET/PATCH/DELETE /snippets/{id}` |
| Environment | `POST/GET /env-variables`, `GET/PATCH/DELETE /env-variables/{id}`, `POST /env-variables/{id}/reveal` |
| Files | `POST /files/upload`, `GET /files`, `GET/DELETE /files/{id}`, `PATCH /files/{id}/folder` |
| Combined list | `GET /items` with optional `folder_id`, `item_type`, `limit`, and `offset` |

Pass the access token as `Authorization: Bearer <token>`. On create endpoints, omit `folder_id` to use the account's default folder. Nested folders are intentionally unsupported.

The folder, snippet, environment-variable, and file list endpoints accept `page` and
`page_size` and return this structure:

```json
{
  "data": [],
  "meta": {"count": 0, "current_page": 1, "page_size": 20}
}
```

`meta.count` is the total number of matching records, not only the number on the current page.
Folder pages default to 20 records, and every folder includes `total_items`, the combined count
of its snippets, environment-variable groups, and files.

### File upload example

```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "upload=@project.zip"
```

The metadata returned by `GET /files/{id}` includes either a time-limited R2 presigned URL or a public URL when `R2_PUBLIC_BASE_URL` is configured. For private user files, leave the public URL unset.

### Environment variable behavior

Each environment-variable resource is a named group, such as a complete production environment:

```json
{
  "name": "Production",
  "variables": [
    {"key": "DATABASE_URL", "value": "postgresql://..."},
    {"key": "REDIS_URL", "value": "redis://..."}
  ],
  "description": "Production service configuration"
}
```

Create, list, and detail responses include every key but return `"value": "********"` for
each value. Call `POST /env-variables/{id}/reveal` to decrypt all values in the group for its
authenticated owner. In `PATCH /env-variables/{id}`, an included `variables` array atomically
replaces the group's complete set; omit it to update only the name, description, or folder.

Changing `FERNET_KEY` makes existing encrypted values unreadable. Store it in a secret manager and back it up; never commit `.env`.

## Email development behavior

If `SMTP_HOST` is empty, OTP email content is written to the application log. This is convenient locally and must not be used as production delivery.

## Project layout

```text
app/
  core/           settings, logging, security
  db/             models, base classes, async session
  services/       reusable email, encryption, R2 clients
  modules/        auth, folders, snippets, env variables, files, combined items
alembic/           database migrations
docker/            Dockerfile, Compose file, entrypoint
```

## Quality checks

```bash
ruff check .
python -m compileall app alembic
pytest
```

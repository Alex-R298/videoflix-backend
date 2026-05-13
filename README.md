# Videoflix Backend

Django REST backend for **Videoflix**, a Netflix-style video streaming platform built as part of the Developer Akademie program. The backend handles user authentication with JWT cookies, video metadata, automatic HLS conversion in three resolutions, and HLS streaming (manifest + segments).

---

## Tech Stack

| Layer | Tech |
|---|---|
| Web framework | Django 6.0 + Django REST Framework |
| Auth | `djangorestframework_simplejwt` with HttpOnly cookie storage |
| Database | PostgreSQL 18 |
| Cache | Redis |
| Background jobs | `django-rq` (Redis Queue) |
| Video pipeline | `ffmpeg` — HLS conversion + thumbnail extraction |
| Static files | `whitenoise` |
| Server | `gunicorn` |
| Containerization | Docker + Docker Compose |
| Email (dev) | Console backend (mails land in container logs) |

---

## Prerequisites

- **Docker Desktop** (Windows / macOS / Linux) — engine must be running
- **Git**
- Roughly **2 GB free RAM** for the three containers
- Ports **8000** (backend) and **5432** / **6379** (internal) must be free

No local Python or Postgres installation required — everything runs in containers.

---

## Python Dependencies

All Python packages are pinned in [`requirements.txt`](./requirements.txt) and installed automatically inside the `web` container by `backend.Dockerfile`. You do **not** need to run `pip install` manually.

| Package | Purpose |
|---|---|
| `Django` | Web framework |
| `djangorestframework` | REST API toolkit |
| `djangorestframework_simplejwt` | JWT auth + token blacklist |
| `django-cors-headers` | CORS handling for the frontend |
| `django-rq` | Background task queue (Redis-backed) |
| `django-redis` | Django cache backend on Redis |
| `psycopg2-binary` | PostgreSQL driver |
| `python-dotenv` | Load `.env` into the Django settings |
| `whitenoise` | Static file serving in production |
| `gunicorn` | WSGI server used inside the container |

If you ever need a local virtual env for IDE autocomplete:

```bash
python -m venv env
env\Scripts\activate          # Windows
source env/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd videoflix-backend

# 2. Copy and configure the .env file (see template below)
cp .env.example .env
#    edit .env with your own SECRET_KEY, DB credentials, allowed origins

# 3. Build and start everything (DB, Redis, web + RQ worker via entrypoint)
docker compose up --build -d

# 4. Apply database migrations
docker compose exec web python manage.py migrate

# 5. Create a superuser (optional, only needed for Django admin)
docker compose exec web python manage.py createsuperuser
```

The backend is now reachable at **http://localhost:8000/**.

| URL | Purpose |
|---|---|
| `http://localhost:8000/admin/` | Django admin |
| `http://localhost:8000/django-rq/` | RQ queue dashboard |
| `http://localhost:8000/api/...` | REST API (see endpoint list) |

---

## Environment Variables (`.env`)

The `web` container is wired to a local `.env` file via `env_file: .env` in `docker-compose.yml`. A starter `.env` ships with the project — adjust `SECRET_KEY`, DB credentials, and `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` to match your frontend host before running the stack. All variable names are referenced in `core/settings.py` if you need to look them up.

---

## Running Tests

The project uses Django's built-in test runner with DRF's `APIClient`. All tests live in the top-level `tests/` folder.

```bash
docker compose exec web python manage.py test tests
```

Expected output: **45+ tests OK**.

Test coverage:

| File | What it covers |
|---|---|
| `tests/test_auth_register.py` | Registration: success, duplicates, password mismatch, missing fields |
| `tests/test_auth_activate.py` | Account activation via uidb64/token |
| `tests/test_auth_login.py` | Login + HttpOnly cookie setting |
| `tests/test_auth_logout.py` | Logout: refresh token blacklisting, cookie deletion |
| `tests/test_auth_token_refresh.py` | Access-token refresh from cookie |
| `tests/test_auth_password_reset.py` | Password-reset request + mail dispatch |
| `tests/test_auth_password_confirm.py` | Password-reset confirmation |
| `tests/test_video_list.py` | Video list endpoint (auth required) |
| `tests/test_video_manifest.py` | HLS manifest delivery |
| `tests/test_video_segment.py` | HLS segment delivery (with path-traversal guard) |

---

## API Endpoints

All routes are prefixed with `/api/`. Authentication uses **HttpOnly JWT cookies** (`access_token`, `refresh_token`) — the frontend never sees the tokens themselves.

### Authentication

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/api/register/` | Create user (inactive), send activation email | — |
| GET | `/api/activate/<uidb64>/<token>/` | Activate account from the email link | — |
| POST | `/api/login/` | Authenticate, set JWT + CSRF cookies | — |
| POST | `/api/logout/` | Blacklist refresh token, clear cookies | refresh cookie |
| POST | `/api/token/refresh/` | Issue a new access token | refresh cookie |
| POST | `/api/password_reset/` | Send password-reset email | — |
| POST | `/api/password_confirm/<uidb64>/<token>/` | Set a new password | — |

### Video

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/video/` | List all videos with metadata | JWT |
| GET | `/api/video/<id>/<resolution>/index.m3u8` | HLS master playlist | JWT |
| GET | `/api/video/<id>/<resolution>/<segment>/` | HLS `.ts` segment | JWT |

`<resolution>` is one of `480p`, `720p`, `1080p`.

---

## How the Video Pipeline Works

1. An admin uploads a video file via the Django admin (`/admin/video_app/video/add/`).
2. A `post_save` signal enqueues `process_video(video_id)` in the `default` RQ queue.
3. The RQ worker (started by `backend.entrypoint.sh`) runs `ffmpeg` three times to produce HLS playlists and segments at 480p / 720p / 1080p under `media/videos/<id>/<resolution>/`.
4. A single frame is extracted as the JPEG thumbnail at `media/thumbnails/<id>.jpg`.
5. The `Video.thumbnail` field is updated automatically.
6. The list endpoint then returns `thumbnail_url`, and the player can request the HLS manifests.

To watch the worker live:

```bash
docker compose logs -f web
```

---

## End-to-End Smoke Test (via Frontend)

1. **Register** a user via the frontend (or `curl -X POST /api/register/`).
2. **Find the activation link** in the container logs:
   ```bash
   docker compose logs web | grep -A1 'activate your account'
   ```
3. **Open the link** in the browser — account gets `is_active=True`.
4. **Log in** via the frontend — receive HttpOnly cookies + CSRF cookie.
5. **Upload a video** in the Django admin — wait until the RQ worker has finished (visible in logs).
6. **Open the dashboard** in the frontend — thumbnails load, HLS playback starts.

---

## Useful Commands

```bash
# View live logs (web + RQ worker output)
docker compose logs -f web

# Open a Django shell inside the container
docker compose exec web python manage.py shell

# Inspect the RQ queue
docker compose exec redis redis-cli -n 0 llen rq:queue:default

# Stop everything
docker compose down

# Stop and remove persistent volumes (full reset — DB + uploaded media gone!)
docker compose down -v
```

---

## Project Layout

```
videoflix-backend/
├── auth_app/                 # User registration, login, JWT cookie handling
│   ├── api/
│   │   ├── authentication.py  # CookieJWTAuthentication
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py           # Token, cookie, mail helpers
│   │   └── views.py
│   └── ...
├── video_app/                # Video model, HLS pipeline, streaming endpoints
│   ├── api/
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py           # serve_hls_file with path-traversal guard
│   │   └── views.py
│   ├── models.py
│   ├── signals.py             # post_save → enqueue HLS task
│   └── tasks.py               # ffmpeg HLS conversion + thumbnail
├── core/                     # Django project (settings, urls, wsgi)
├── tests/                    # All test modules (flat structure, run via `manage.py test tests`)
├── backend.Dockerfile
├── backend.entrypoint.sh
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## Code Conventions

- Functions are kept **≤ 14 lines**, each with a single responsibility.
- Helpers live in `utils.py` / `tasks.py`, never in `views.py`.
- `snake_case` everywhere; PEP-8 compliant.
- Error messages exposed to the API are **generic** (security) — clients never learn whether an email exists, whether a password was wrong, or whether a token was invalid.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `docker compose up` fails on Postgres column missing | Run `docker compose exec web python manage.py migrate` |
| Tests fail with `column "category" does not exist` | Missing migration — run `makemigrations video_app` + `migrate` |
| `401` on `/api/video/` from the frontend | Frontend not sending `credentials: 'include'` |
| CORS blocked in browser | Add the frontend origin to `CORS_ALLOWED_ORIGINS` in `.env`, then `docker compose up -d` |
| `404` on `index.m3u8` for an existing video | HLS conversion has not run yet — check the RQ worker logs |
| `Logout error, redirecting...` toast | Missing `csrftoken` cookie — log in first to receive it |

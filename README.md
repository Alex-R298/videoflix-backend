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

# 2. Copy the env template and adjust it
cp .env.template .env
#    edit .env with your own SECRET_KEY, DB credentials, and (optional)
#    SMTP credentials if you want real mail delivery

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

The `web` container is wired to a local `.env` file via `env_file: .env` in `docker-compose.yml`. `.env.template` ships with the project — copy it to `.env` and adjust as needed. The most important variables:

| Variable | Default | When to change |
|---|---|---|
| `SECRET_KEY` | dev key | Always set a real one |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | placeholders | Always set |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5500` | Add your frontend dev host |
| `CORS_ALLOWED_ORIGINS` | falls back to common ports (5500/5501/4200) | Override if your frontend runs elsewhere |
| `FRONTEND_URL` | `http://127.0.0.1:5500` | Set to your actual frontend origin |
| `FRONTEND_ACTIVATION_PATH` | `/pages/auth/activate.html` | Path of the activation page in the frontend |
| `FRONTEND_PASSWORD_RESET_PATH` | `/pages/auth/confirm_password.html` | Path of the password-confirm page |
| `EMAIL_BACKEND` | `...console.EmailBackend` | Set to `...smtp.EmailBackend` for real mails |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | empty | Fill in to send via SMTP (Mailtrap/Gmail/...) |

All variable names are referenced in `core/settings.py`.

---

## Email Setup

The backend renders **HTML + plaintext** activation and password-reset emails from templates in [`auth_app/templates/emails/`](auth_app/templates/emails/). The link inside the email points to the **frontend** (e.g. `http://127.0.0.1:5500/pages/auth/activate.html?uid=...&token=...`); the frontend then calls the backend API.

Three ways to deliver these mails:

| Backend | What happens | Use for |
|---|---|---|
| `console.EmailBackend` (default) | Mail is dumped into the Docker logs | Quick dev / submission default — no setup |
| `smtp.EmailBackend` with [Mailtrap](https://mailtrap.io) | Mail lands in a sandbox web inbox | Visual testing of templates |
| `smtp.EmailBackend` with Gmail / SendGrid / Mailgun | Real delivery to a real inbox | Production-style demo |

To switch from console to real SMTP, set in `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=sandbox.smtp.mailtrap.io     # or smtp.gmail.com, etc.
EMAIL_PORT=2525                          # or 587
EMAIL_HOST_USER=your_user
EMAIL_HOST_PASSWORD=your_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@videoflix.local
```

Then `docker compose up -d` to recreate the container with the new env.

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

Assumes the frontend is running on `http://127.0.0.1:5500` (or 5501 — adjust `FRONTEND_URL` in `.env`).

1. **Register** a user via the frontend form.
2. **Pick up the activation link.** With the default console backend, the mail is in the Docker log:
   ```bash
   docker compose logs web | grep -A1 'activate your account'
   ```
   Note: the URL in the raw log is quoted-printable-encoded (`=3D` → `=`, `&amp;` → `&`). For clickable mails, configure SMTP/Mailtrap (see *Email Setup*).
3. **Open the link** → the frontend's activation page runs, calls `GET /api/activate/<uid>/<token>/`, account becomes `is_active=True`.
4. **Log in** via the frontend — backend sets HttpOnly JWT cookies and a `csrftoken` cookie.
5. **Upload a video** in the Django admin (`/admin/video_app/video/add/`). The RQ worker picks up `process_video` automatically (`docker compose logs -f web` shows ffmpeg output).
6. **Open the dashboard** in the frontend — thumbnails appear once the worker finished, HLS playback works through the manifest/segment endpoints.

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
│   │   ├── authentication.py  # CookieJWTAuthentication (reads JWT from cookie)
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── utils.py           # Token, cookie, mail helpers
│   │   └── views.py
│   ├── templates/emails/      # HTML + plaintext activation / reset templates
│   ├── admin.py               # Custom UserAdmin (surfaces is_active)
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
| Email link in Docker log has `=3D` / `&amp;` artifacts | That's quoted-printable encoding of the multipart MIME message. Decoded URL is the same. Switch to Mailtrap or Gmail SMTP to see clean clickable links |
| 500 on `/api/register/` after changing `.env` | `EMAIL_BACKEND` is set to `smtp` but credentials are wrong — fix the SMTP values or remove the line to fall back to console backend |

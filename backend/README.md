# Backend (Django)

This folder holds the **Django project** (settings, URLs, WSGI).

- **`gistagum/`** — Main project package (settings, urls, wsgi, asgi, middleware).

**Django apps** live at the **project root** (one level up):

- `projeng/` — Projects & engineering
- `monitoring/` — Monitoring & dashboard
- `theme/` — Theming
- `onetagumvision/` — Tailwind / base app
- `accounts/` — Auth (login, password reset)

**Run commands from project root:**

```bash
# From repo root (recommended)
cd C:\xampp\htdocs\OneTagumVision-DP
python manage.py runserver
python manage.py migrate
python manage.py collectstatic
```

See **PROJECT_STRUCTURE.md** at the repo root for the full layout.

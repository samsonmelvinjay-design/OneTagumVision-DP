# Frontend (templates & static)

This folder is for **UI assets** when you use a separated layout.

- **`templates/`** — Django HTML templates (after you move them here from the repo root).
- **`static/`** — CSS, JavaScript, images, and static data (e.g. GeoJSON).

**If you haven’t moved them yet:**  
Templates and static files can stay at the project root (`templates/`, `static/`). The app will use them from there. When you’re ready for a cleaner structure, move those two folders into this `frontend/` folder; the Django settings will pick them up automatically.

**To work on frontend only:**  
Open this folder (and the root `templates/` and `static/` if they’re still at root) and edit HTML, CSS, JS, and assets. No need to run Django for static/template edits; run the server when you want to test in the browser.

See **PROJECT_STRUCTURE.md** at the repo root for the full layout.

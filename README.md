# A GIS-driven platform: A project monitoring and visualization for tagum city

A Django-based platform for monitoring and visualizing government projects using Leaflet and OpenStreetMap.

## Features

- Project listing and details
- Interactive map visualization
- Admin interface for project management

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd gistagum
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run migrations:
   ```
   python manage.py migrate
   ```

4. Create a superuser (optional):
   ```
   python manage.py createsuperuser
   ```

5. Run the development server:
   ```
   python manage.py runserver
   ```

6. Visit http://127.0.0.1:8000/ to view the project list and map.

## Data Migration (Restore Database and Media Files)

To fully restore the project with all data and uploaded files on a new machine:

1. **Clone the repository:**
   ```sh
   git clone https://github.com/kennethkeeen/GISONETAGUMVISION.git
   cd GISONETAGUMVISION
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Restore the database:**
   - If using SQLite, copy the `.sqlite3` file if present.
   - If using a SQL dump (e.g., `gistagumdb.sql`), import it into your database system:
     - For SQLite: You can use the file directly.
     - For PostgreSQL/MySQL: Use your DB tool to import the `.sql` file.

4. **Restore media files:**
   - The `media/` and `project_images/` folders are included in the repository. No extra steps needed.

5. **Run migrations (if needed):**
   ```sh
   python manage.py migrate
   ```

6. **Run the development server:**
   ```sh
   python manage.py runserver
   ```

7. **Access the app:**
   - Visit http://127.0.0.1:8000/ in your browser.

## Usage

- Admin: http://127.0.0.1:8000/admin/
- Project List: http://127.0.0.1:8000/
- Map View: http://127.0.0.1:8000/map/ 
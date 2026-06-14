# Spritai - Splitwise Clone MVP

A simplified Splitwise clone featuring Django REST Framework on the backend and React (Vite) on the frontend. 

Built overnight for a software engineering internship assignment.

---

## Local Setup

### 1. Backend Setup
Make sure you have Python 3.10+ installed.

```bash
# Initialize virtualenv
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations (creates SQLite locally by default)
python backend/manage.py migrate

# Seed default 6 users (Aisha, Rohan, Priya, Meera, Dev, Sam) and group "The Flat"
python backend/manage.py seed_data

# Run dev server
python backend/manage.py runserver
```
The backend will run on `http://127.0.0.1:8000/api/`.

### 3. Demo / Test Credentials
To test the local or deployed application, you can log in as any of the seeded roommates using the following credentials:
* **Password** (for all users): **`password123`**
* **Emails**:
  * `aisha@example.com`
  * `rohan@example.com`
  * `priya@example.com`
  * `meera@example.com`
  * `dev@example.com`
  * `sam@example.com`
  * `kabir@example.com` *(created automatically during CSV import)*

---

### 2. Frontend Setup
Make sure you have Node.js 18+ installed.

```bash
cd frontend

# Install packages
npm install

# Start local server
npm run dev
```
The frontend will open on `http://localhost:5173/`. It communicates with the backend local port by default.

---

## Production Deployment

### 1. Database Setup (Neon PostgreSQL)
1. Sign up for a free account on [Neon.tech](https://neon.tech/).
2. Create a new project and select PostgreSQL.
3. Copy the **connection string** (starts with `postgresql://...`).

### 2. Backend Deployment (Render)
1. Go to [Render](https://render.com/) and sign up.
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository: `https://github.com/animeshtripathii/splitwise-clone.git`.
4. Configure the settings:
   - **Name**: `splitwise-backend`
   - **Runtime**: `Python`
   - **Build Command**: `./build.sh` (This automatically runs requirements installation, DB migrations, seeds users, and collects static files)
   - **Start Command**: `gunicorn config.wsgi:application --chdir backend`
5. Add the following **Environment Variables** in the service settings:
   - `PYTHON_VERSION` = `3.11.5`
   - `DATABASE_URL` = `<your-neon-postgres-connection-string>`
   - `DEBUG` = `False`
   - `SECRET_KEY` = `<any-long-random-string>`
6. Deploy the service and copy your live backend URL (e.g. `https://splitwise-backend.onrender.com`).

### 3. Frontend Deployment (Vercel)
1. Go to [Vercel](https://vercel.com/) and sign up.
2. Click **Add New** -> **Project** and import your GitHub repository.
3. In the project setup panel:
   - **Root Directory**: Select `frontend`.
   - **Framework Preset**: `Vite`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand the **Environment Variables** section and add:
   - `VITE_API_URL` = `<your-live-render-backend-url>/api/` (e.g., `https://splitwise-backend.onrender.com/api/`)
5. Click **Deploy**. Vercel will build and serve your React app publicly.

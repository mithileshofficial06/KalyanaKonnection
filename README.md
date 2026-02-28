# KalyanaKonnection

KalyanaKonnection is a role-based food surplus redistribution platform that connects event food providers with NGOs for fast, verified, and transparent pickup.

## Key Highlights

- Role-based portals for **Provider**, **NGO**, and **Admin**
- Email OTP verification for **registration** and **forgot password**
- Location-aware nearby matching using geocoding + distance radius
- Receiver-generated pickup code verification at handover
- Real-time dashboard refresh using Socket.IO events
- Admin analytics, moderation tools, and system health diagnostics

## Modules

### Provider
- Add surplus with mahal details, quantity, location, and photo
- Mark surplus as ready for NGO requests
- Verify receiver pickup using 6-digit code
- Track allocations and view reviews/complaints

### NGO
- Find nearby surplus by location + radius
- View provider contact and mahal details
- Request pickup and receive unique pickup code
- Track allocations with clear status (On the way / Received)
- Submit reviews and complaints

### Admin
- View platform KPIs and operational insights
- Manage users, events, allocations, and complaints
- Update complaint lifecycle status
- Use analytics dashboard and health diagnostics endpoint

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-Migrate (Alembic)
- **Realtime:** Flask-SocketIO
- **Security:** Flask-WTF (CSRF), Flask-Limiter, password hashing
- **Database:** PostgreSQL (`psycopg2-binary`)
- **Maps/Geo:** OpenStreetMap Nominatim + haversine distance

## Project Structure

```text
app/
  models/      # SQLAlchemy models
  routes/      # Role-based route blueprints
  services/    # Geocoding, matching, realtime services
  templates/   # Jinja templates (shared + role dashboards)
  static/      # CSS, JS, uploads
migrations/    # Alembic migration history
api/index.py   # Deployment entrypoint
run.py         # Local runtime entrypoint
```

## Local Setup

### 1) Create and activate virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables (`.env`)

```env
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://username:password@host:5432/dbname

# SMTP for email OTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_smtp_password_or_app_password
SMTP_FROM_EMAIL=your_email@example.com
SMTP_USE_TLS=true

# Optional runtime controls
COOKIE_SECURE=false
PREFERRED_URL_SCHEME=http
RATELIMIT_STORAGE_URI=memory://
```

### 4) Apply migrations

```bash
flask --app run.py db upgrade
```

### 5) Run locally

```bash
python run.py
```

App starts on `http://localhost:5000`.

## Realtime Update Behavior

Dashboards subscribe to `platform_update` events. Important actions (new request, completion, review, complaint update, etc.) trigger auto-refresh so users see the latest state quickly.

## Pickup Verification Flow

1. Provider marks surplus as ready.
2. NGO requests pickup and receives a 6-digit code.
3. Provider enters receiver's code at handover.
4. If code is correct, allocation is completed and receiver status becomes received.

## Production Notes

- Ensure production has correct `DATABASE_URL` (no localhost unless intended).
- Run migrations in deployment environment before validating routes.
- SMTP credentials must be valid for OTP delivery.
- Use `COOKIE_SECURE=true` behind HTTPS.

## Current Documentation

- Detailed technical report: `PROJECT_REPORT.md`
- Submission-format report: `PROJECT_REPORT_SUBMISSION.md`

## Future Improvements

- Weather-aware pickup prioritization
- Trust scoring module
- Predictive surplus analytics
- Automated test suite expansion

## License

This project is currently for educational/project use.

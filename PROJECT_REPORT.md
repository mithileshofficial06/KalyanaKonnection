# KalyanaKonnection — Detailed Project Report

## 1) Project Overview

**Project Name:** KalyanaKonnection  
**Domain:** Food surplus recovery and redistribution  
**Primary Users:**
- **Providers** (wedding halls/caterers/event hosts)
- **NGOs/Receivers** (organizations that collect and distribute food)
- **Admins** (platform supervisors)

### Problem Statement
Large quantities of quality food go to waste after events, while many communities still face food insecurity. KalyanaKonnection addresses this gap by connecting surplus food providers with nearby receivers through a structured, secure, and trackable pickup workflow.

### Core Objective
Enable fast, trusted, location-aware surplus pickup with role-based dashboards, secure authentication, OTP-protected account and handover flows, and real-time operational updates.

---

## 2) Current Technology Stack

### Backend
- **Python + Flask** (application framework)
- **Flask SQLAlchemy** (ORM)
- **Alembic + Flask-Migrate** (database migrations)
- **Flask-SocketIO** (real-time updates)
- **Flask-WTF / CSRFProtect** (CSRF protection)
- **Flask-Limiter** (rate limiting)

### Database
- **PostgreSQL** in deployment
- `psycopg2-binary` database driver

### Supporting Libraries
- `requests` for geocoding API calls
- `python-dotenv` for environment configuration

### Runtime Entry Points
- Local run: `run.py`
- Deployment handler: `api/index.py`

---

## 3) Project Architecture

The application follows a modular Flask blueprint architecture:

- `app/routes/auth_routes.py` — Authentication, OTP verification, password reset
- `app/routes/provider_routes.py` — Provider dashboard and surplus lifecycle
- `app/routes/ngo_routes.py` — NGO matching, requests, pickup history, reviews
- `app/routes/admin_routes.py` — Admin analytics, moderation, user management
- `app/routes/common_routes.py` — Shared helper APIs (location suggest/geocode)

### Service Layer
- `app/services/maps_service.py` — geocoding + location suggestions (Nominatim)
- `app/services/matching_service.py` — radius filtering with haversine distance
- `app/services/realtime_service.py` — central socket event publisher

### Data Models
- `User`
- `Event`
- `Surplus`
- `Allocation`
- `Review`
- `Complaint`

---

## 4) Data Model Summary

## `User`
Stores identity and role information:
- `full_name`, `email` (unique), `password_hash`
- `role` (`provider`, `ngo`, `admin`)
- `phone_number` (unique), `phone_verified`

## `Event`
Provider-side event metadata:
- `event_name`, `event_date`, `guest_count`, `provider_id`

## `Surplus`
Primary donation batch entity:
- `event_name`, `mahal_name`, `provider_name`
- `food_type`, `quantity`, `quantity_kg`
- `estimated_expiry`, `distance_km`
- `provider_location`, `provider_latitude`, `provider_longitude`
- `photo_path`, `status`, timestamps

## `Allocation`
Handover transaction between provider and NGO:
- `surplus_id`, `provider_id`, `ngo_id`
- `status`, `pickup_time`, `otp_code`

## `Review`
NGO feedback for providers:
- `rating`, `comment`, foreign keys to NGO/provider

## `Complaint`
Issue reporting + admin moderation:
- `issue_type`, `description`, `status`

---

## 5) Authentication & Security Features

## Role-Based Access Control
All protected routes use role guards to prevent cross-role access.

## Account Security
- Passwords are hashed (`werkzeug.security`)
- Email format and password policy validation enforced
- Phone number format validation (10-digit)
- Unique email and phone constraints

## OTP Verification
Implemented via email OTP in `auth_routes` + `otp_generator`:
- **Register OTP flow**
  - OTP generated and hashed
  - Session-bound context
  - Expiry checks and max-attempt protection
  - Resend support
- **Forgot password OTP flow**
  - OTP verification before reset
  - Restricted reset session flags

## Anti-Abuse Controls
- Endpoint-level rate limits on register, login, OTP verify, forgot/reset
- CSRF protection enabled globally

## Session Hardening
- HTTPOnly cookies
- SameSite policy
- Configurable secure cookies (`COOKIE_SECURE`)

---

## 6) Provider Module (Features)

### Dashboard
- Total events
- Total donated quantity
- Active allocations
- Average rating
- Recent allocation activity

### Add Surplus Workflow
Provider submits:
- Event name
- Mahal name
- Food type
- Quantity (kg)
- Mahal location
- Optional distance/expiry
- Food photo upload

System behavior:
- Validates required fields
- Geocodes mahal location
- Stores lat/lon for matching
- Creates surplus in **pending** state

### Ready State Control
Provider must explicitly mark surplus as **Ready**:
- Status transitions to `available`
- NGOs can request only after this transition

### Pickup Verification
- Provider sees active allocations
- Provider enters **receiver-generated 6-digit code** manually
- Wrong code: handover remains in-progress
- Correct code:
  - Allocation -> `completed`
  - Surplus -> `completed`
  - Realtime event emitted

---

## 7) NGO Module (Features)

### Dashboard
- Available nearby surplus count
- Active pickups count
- Completed pickups count
- Trust score

### Nearby Surplus Discovery
- Receiver enters location and radius
- Backend geocodes receiver location
- Surplus filtered using haversine distance
- Results sorted by nearest distance
- Includes provider contact + mahal details for coordination

### Request Pickup Flow
- NGO can request only for `available` surplus
- Photo requirement enforced before request
- On request:
  - Allocation created
  - Unique 6-digit pickup OTP generated
  - Surplus marked requested/in-progress

### Allocation Tracking
Receiver page displays:
- Event/mahal/provider/contact details
- Pickup code to share at handover
- Status language:
  - **On the way** before successful verification
  - **Received** once provider verifies code

### Reviews & Complaints
- Submit provider reviews (rating + comment)
- Raise complaints with issue type + details

---

## 8) Admin Module (Features)

### Admin Dashboard
- Total providers, NGOs, events, surplus kg, allocations, active complaints
- Operational insights (completion rate, high-risk batches, unallocated surplus)
- Recent cross-module activity stream

### User Management
- Role filters and search
- User deletion with related data cleanup

### Events Monitoring
- Event list and event insights
- Tracking of events with associated surplus

### Allocation Monitoring
- Recent allocations and status distribution
- Insight counters for completed/requested/allocated/in-transit labels

### Complaint Moderation
- Complaint queue with status transitions:
  - Under Review
  - Escalated
  - Resolved
  - Rejected

### Analytics
- Monthly surplus trend
- Monthly completed allocations trend
- Complaint status distribution
- Top providers (donated kg)
- Top NGOs (completed pickups)
- Allocation efficiency and trust score metrics

### System Health Endpoint
`/admin/system/health` reports:
- Active DB host and DB name
- Existence of critical tables
- Column introspection for diagnostics

---

## 9) Realtime Update System

Realtime delivery is implemented via `Flask-SocketIO`:

- Backend emits `platform_update` events on important actions:
  - user creation/deletion
  - surplus creation/ready
  - allocation requested/completed
  - review/complaint updates
- Shared dashboard base listens to events and refreshes UI automatically
- Live indicator timestamp updates to show active refresh behavior

This ensures providers, NGOs, and admins see near-live state changes without manual polling.

---

## 10) Pickup Status Semantics (Current UX)

Internally, allocation status persists as DB values (`requested`, `completed`, etc.) to keep analytics compatible.

User-facing status language is mapped for clarity:
- Before verification: **On the way**
- After successful provider verification:
  - Provider view: **Completed**
  - NGO view: **Received**

This gives user-friendly tracking while preserving stable reporting logic.

---

## 11) Location & Mapping Features

### APIs
- `/location/suggest?q=...` — returns place suggestions
- `/location/geocode?q=...` — returns resolved coordinates/display name

### Matching Logic
- Geocode receiver query
- Compare receiver coordinates against surplus coordinates
- Calculate distance via haversine
- Filter by selected radius
- Sort by nearest

---

## 12) Migrations & Schema Evolution

Key migration history includes:
- Auth and role/flow upgrades
- Surplus location fields
- `quantity_kg` normalization
- `mahal_name` addition
- User phone normalization and unique index enforcement

Latest chain includes:
- `d4b5a7c9e1f2_add_surplus_quantity_kg_column.py`
- `e7c2f9a1b6d3_add_mahal_name_to_surplus.py`
- `f9a4c2d8b1e6_normalize_user_phone_numbers.py`

---

## 13) UI/UX Implementations

Platform-wide enhancements include:
- Modernized dashboard UI
- Better visual hierarchy and sectioning
- Search + sort tables
- Responsive sidebar and mobile interactions
- Flash alert normalization and dismiss actions
- Status badge normalization
- Form validation polish
- Accessibility improvements (`focus-visible`, keyboard sort triggers)

Branding is now **KalyanaKonnection** across shared templates.

---

## 14) Deployment Readiness & Operations

### Dependency Optimization
`requirements.txt` reduced to essential runtime dependencies for deployment size compatibility.

### Production Stability Work
- PostgreSQL driver compatibility adjusted (`psycopg2-binary`)
- Environment-based DB URL handling (`postgres://` compatibility conversion)
- Schema-drift fixes through corrective migrations
- Admin diagnostics endpoint to troubleshoot runtime DB mismatches

### Repo Hygiene
`.gitignore` includes:
- virtual environments
- secrets (`.env`)
- build artifacts
- caches/logs
- uploaded assets

---

## 15) Validation Summary

Recent functional validation confirms:
1. NGO request creates allocation and 6-digit code.
2. Wrong provider-entered code does **not** complete handover.
3. Correct code marks allocation and surplus as completed.
4. UI status mapping reflects required wording:
   - On the way -> Completed/Received
5. Realtime events are emitted at request and completion transitions.

---

## 16) Current Gaps / Improvement Opportunities

The following files exist but are currently placeholders (empty):
- `app/services/weather_service.py`
- `app/services/trust_service.py`
- `app/ml/predict.py`
- `app/ml/train_model.py`
- `app/static/js/main.js`
- `app/static/js/maps.js`
- `app/static/js/weather.js`

### Suggested Next Enhancements
- Add weather-risk assistance for pickup prioritization.
- Implement trust-scoring service at provider/NGO profile level.
- Add predictive surplus estimation (ML module).
- Add background task queue for non-blocking OTP/mail/retry workflows.
- Add automated unit + integration test suite for route and status transitions.
- Reconcile README to reflect current email OTP implementation and updated architecture.

---

## 17) Conclusion

KalyanaKonnection is now a robust multi-role food surplus coordination platform with:
- secure role-based access,
- OTP-verified onboarding and account recovery,
- geolocation-driven matching,
- controlled pickup verification using receiver code,
- realtime operational synchronization,
- and admin-level observability/analytics.

The system is production-oriented, schema-migrated, and functionally aligned with your latest workflow requirements for provider–receiver handover and status transparency.

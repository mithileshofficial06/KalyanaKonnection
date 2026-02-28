# KalyanaKonnection
## Academic Project Submission Report

## 1. Title
**KalyanaKonnection: A Real-Time Food Surplus Redistribution Platform for Event Providers and NGOs**

---

## 2. Abstract
Food waste after events is a major social and environmental issue, while many communities still face food insecurity. KalyanaKonnection is a web-based platform that connects food providers (wedding halls/caterers) with NGOs for quick and safe redistribution of surplus food. The system uses role-based access, location-based matching, OTP-secured handover verification, and real-time dashboard updates to ensure reliable coordination between stakeholders. The project aims to reduce edible food wastage, improve transparency in food handover, and provide an operational control panel for administrators.

---

## 3. Problem Statement
In many cities, large quantities of edible food are discarded after social events due to lack of coordination between food providers and organizations that can redistribute it. Existing manual processes are often slow, unstructured, and lack trust verification mechanisms.

### Existing Challenges
- No structured platform for provider–NGO coordination
- Delays in identifying nearby receivers
- Lack of pickup verification and accountability
- Poor visibility for administrators
- Data inconsistency and manual communication overhead

---

## 4. Objectives
The main objectives of KalyanaKonnection are:
1. Build a role-based food surplus management platform.
2. Enable providers to publish surplus food batches with location details.
3. Help NGOs discover and request nearby surplus quickly.
4. Secure pickup handover using receiver-generated OTP verification.
5. Provide real-time update visibility across all dashboards.
6. Offer admin-level monitoring, analytics, and complaint moderation.

---

## 5. Scope of the Project
### In Scope
- Authentication and role-based access for Provider, NGO, and Admin
- OTP-based registration verification and password reset (email)
- Surplus posting with mahal name/location and image
- Radius-based nearby surplus search
- Pickup request and verification flow
- Realtime dashboard auto-refresh on important events
- Admin dashboard, analytics, user controls, complaint handling

### Out of Scope (Current Version)
- Payment gateway integration
- Native mobile applications
- Multi-language UI
- Full automated test suite
- Predictive ML recommendations (modules reserved but not implemented)

---

## 6. Technology Stack
### Backend
- Python 3.11
- Flask
- Flask-SQLAlchemy
- Flask-Migrate + Alembic
- Flask-SocketIO
- Flask-WTF (CSRF)
- Flask-Limiter

### Database
- PostgreSQL (production)
- SQLite-compatible in isolated local tests

### APIs / Integrations
- OpenStreetMap Nominatim (geocoding + suggestions)

### Utilities
- `requests`
- `python-dotenv`
- `psycopg2-binary`

---

## 7. System Architecture
The project follows a modular Flask architecture with blueprints and separated service layers.

### Core Components
- **App Factory:** central initialization of extensions and blueprints
- **Routes Layer:** role-based modules for auth, provider, NGO, admin, common APIs
- **Service Layer:** geocoding, matching, realtime events
- **Data Layer:** SQLAlchemy models and Alembic migrations
- **Template Layer:** role dashboards and shared responsive UI shell

### Main Route Modules
- `auth_routes.py`
- `provider_routes.py`
- `ngo_routes.py`
- `admin_routes.py`
- `common_routes.py`

---

## 8. Database Design Overview
### Entities
1. **User** — identity, role, email, phone, password hash
2. **Event** — provider events and metadata
3. **Surplus** — food batches with location and status
4. **Allocation** — pickup transactions between provider and NGO
5. **Review** — trust/feedback records
6. **Complaint** — issue tracking and moderation

### Key Relationships
- One provider can have multiple events and surplus batches.
- One NGO can request multiple allocations.
- One surplus can map to allocation records.
- NGO/provider pair can generate review and complaint entries.

---

## 9. Module-Wise Feature Description

## 9.1 Authentication Module
- Register with role, email, phone, and password
- Email OTP verification for account creation
- Resend OTP and max attempt protections
- Secure login with role-based redirection
- Forgot password via OTP and reset flow

## 9.2 Provider Module
- Dashboard KPIs (events, donations, allocations, ratings)
- Add surplus batch with:
  - Event name
  - Mahal name
  - Mahal location (geocoded)
  - Food details and quantity
  - Optional expiry and distance
  - Food image upload
- Mark batch as ready to receive requests
- Verify pickup by entering receiver-provided code
- View allocation summaries and reviews/complaints

## 9.3 NGO Module
- Dashboard with available surplus and pickup metrics
- Nearby search by receiver location + radius
- Request food from ready surplus batches
- Generated 6-digit pickup code visible to NGO
- Allocation status tracking
- Submit review and complaint feedback

## 9.4 Admin Module
- Operational dashboard with KPIs and live activity
- User management with role filters and search
- Event and allocation tracking
- Complaint moderation with status transitions
- Analytics dashboard (trends and top contributors)
- System health endpoint for DB diagnostics

---

## 10. Workflow and Business Logic
### Step 1: Provider posts surplus
- Surplus starts in `pending` state.

### Step 2: Provider marks batch as ready
- Status becomes `available`.

### Step 3: NGO requests pickup
- Allocation is created in `requested` state.
- Unique receiver pickup OTP is generated.

### Step 4: Pickup handover verification
- Provider must manually enter receiver’s 6-digit code.
- If code is wrong: status remains in progress.
- If code is correct:
  - Allocation becomes `completed`
  - Surplus becomes `completed`

### User-facing status language
- Before verification: **On the way**
- After successful verification:
  - Provider side: **Completed**
  - NGO side: **Received**

---

## 11. Real-Time Update Mechanism
KalyanaKonnection uses SocketIO-based event notifications.

### Events emitted on:
- New user creation/deletion
- Surplus creation/ready transitions
- Allocation request/completion
- Review and complaint updates

### Client behavior
- Shared dashboard script listens for `platform_update`
- Dashboards auto-refresh after receiving event
- Live indicator timestamp is updated

This keeps all roles synchronized without manual refresh.

---

## 12. Security Measures
1. **Password hashing** for user credentials
2. **CSRF protection** on form submissions
3. **Rate limiting** for sensitive routes (login/OTP/reset)
4. **OTP expiry + attempt restrictions**
5. **Role-based route guards**
6. **Session controls** with secure cookie policies
7. **Input validation** for email, phone, and numeric fields

---

## 13. UI/UX Design Enhancements
- Responsive role dashboards
- Mobile-friendly sidebar interactions
- Improved card hierarchy and sectioning
- Searchable and sortable tables
- Status badges and normalized alert patterns
- Better form validation and field feedback
- Accessibility-friendly focus behavior

Branding has been standardized as **KalyanaKonnection**.

---

## 14. Deployment and Environment Notes
- Deployment-compatible entry available via `api/index.py`
- Environment-driven configuration via `.env`
- PostgreSQL-ready setup with migration tracking
- Optimized runtime dependencies for cloud build size constraints
- Added `.gitignore` for secrets, cache, and generated assets

---

## 15. Migration and Data Consistency Work
The project includes versioned schema evolution to support production stability.

### Important migration milestones
- Dynamic auth and flow upgrades
- Surplus location fields
- Quantity normalization (`quantity_kg`)
- Mahal name support in surplus
- Phone normalization and unique index handling

These changes ensure compatibility between evolving features and deployed databases.

---

## 16. Testing and Validation Summary
Validated outcomes include:
1. NGO request generates allocation + 6-digit code.
2. Wrong provider code does not complete pickup.
3. Correct provider code completes allocation and surplus.
4. Receiver/provider status wording appears correctly.
5. Realtime update triggers are active for request and completion transitions.

---

## 17. Limitations
Current version limitations:
- Weather-based spoilage intelligence not yet implemented
- Trust scoring service module exists but not active
- ML prediction pipeline files are placeholders
- No complete automated unit/integration test suite yet

---

## 18. Future Enhancements
1. Weather risk prediction and pickup prioritization
2. Dynamic trust index for providers and NGOs
3. ML-based surplus forecasting and smart recommendation engine
4. Notification expansion (email/SMS/push)
5. Full CI test coverage
6. Role-based audit trails and compliance logging
7. Native mobile application support

---

## 19. Social and Operational Impact
KalyanaKonnection can help:
- Reduce event-based food wastage
- Improve food access for vulnerable groups
- Increase trust through verified handovers
- Provide data-driven transparency for organizations and administrators

The platform creates measurable social value by combining logistics, accountability, and technology in a practical food redistribution workflow.

---

## 20. Conclusion
KalyanaKonnection demonstrates a complete, practical solution for event surplus food management. The platform integrates secure access control, location-aware matching, realtime operational visibility, and OTP-based handover verification to ensure trustworthy food redistribution from providers to NGOs. The current implementation is production-oriented, modular, and extensible for future smart features such as predictive analytics, advanced trust scoring, and automated prioritization.

---

## 21. References
1. Flask Documentation — https://flask.palletsprojects.com/
2. SQLAlchemy Documentation — https://docs.sqlalchemy.org/
3. Alembic Documentation — https://alembic.sqlalchemy.org/
4. Flask-SocketIO Documentation — https://flask-socketio.readthedocs.io/
5. OpenStreetMap Nominatim API — https://nominatim.org/

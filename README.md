# CorteX – Zero-Commission Food Redistribution Platform

## Table of Contents
1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [System Architecture & Technology Stack](#system-architecture--technology-stack)
4. [Technical Deep Dive](#technical-deep-dive)
5. [Installation & Setup Guide](#installation--setup-guide)
6. [Usage Guide](#usage-guide)
7. [Environment Variables / Configuration](#environment-variables--configuration)
8. [Project Screens / Pages](#project-screens--pages)
9. [Security & Privacy Notes](#security--privacy-notes)
10. [Performance & Optimization Notes](#performance--optimization-notes)
11. [Limitations & Known Issues](#limitations--known-issues)
12. [Future Enhancements](#future-enhancements)
13. [Real-World Value & Business Perspective](#real-world-value--business-perspective)
14. [Contribution Guidelines](#contribution-guidelines)
15. [License](#license)
16. [Conclusion](#conclusion)

## Project Overview
CorteX is a web platform that connects restaurants, donors, NGOs, beneficiaries, and delivery personnel to redistribute surplus food locally. It eliminates marketplace commissions, streamlines pickup and delivery through OTP-based verification, and supports optional paid listings with in-app payments and automated refunds. The goal is to reduce food waste, combat hunger, and offer a transparent, community-driven redistribution network.

- **What it does:** Manages multi-role interactions for posting food, requesting pickups, assigning deliveries, and completing handoffs with payment and OTP verification.
- **Platform type:** Web application (Flask backend with server-rendered HTML/Bootstrap UI).
- **Purpose & goal:** Cut food waste, speed last-mile redistribution, and keep costs at zero for core flows.
- **Target users:** Restaurants, donors, NGOs, beneficiaries, delivery partners, and admins.
- **Scope & vision:** Local-first logistics with geo-filtered matching, transparent payments, and donor/delivery payouts.

## Key Features
**Core**
- Multi-role accounts: restaurant, donor, NGO, beneficiary, delivery; admin console for user oversight.
- Food listings: create/edit/delete food posts with images, stock toggles, free/paid tagging, pricing, and geocoded location capture.
- Pickup requests: NGOs/beneficiaries request items; donors approve/decline; status lifecycle covers payment pending, accepted, delivery assigned, arrived, completed, rejected.
- Payments: Razorpay orders for requester charges (item price, platform fee, delivery fee, GST). Signature verification on success.
- Refunds: Donor-side rejection triggers Razorpay refund on paid requests.
- Delivery assignment: Auto-selection of nearest delivery partner (≤5 km to donor and requester) or manual acceptance by delivery users.
- OTP verification: Separate OTP for donor arrival and requester completion; registration OTP via email.

**Major**
- Dashboards per role with charts (Chart.js) and live counts: donations, deliveries, pickups, completion metrics, food saved.
- Search & discovery: keyword search across item name/description/city; geo-filtered listings by requester address and distance calculation.
- Notifications: Email alerts for registration OTP, login success, request acceptance, delivery assignment.
- Profile management: Editable contact and payout details (bank/UPI/PAN) for payouts.

**Minor/Hidden**
- Mobile-friendly navigation bar and footer shortcuts.
- Pagination on listings view.
- Copy/share listing link helper.
- Flash messaging for UX feedback.

**Admin**
- Admin login and user table with delete capability.

## System Architecture & Technology Stack
- **Architecture:** Flask application factory with Blueprints; SQLAlchemy ORM; server-rendered Bootstrap templates; Razorpay and OpenCage integrations; SMTP via Flask-Mail.
- **Frontend:** HTML templates (Bootstrap 5, Font Awesome, Chart.js) under `app/templates` with shared layout in `app/templates/base.html`.
- **Backend:** Flask, Flask-Login, Flask-WTF, Flask-Mail, Flask-Migrate, Flask-Bcrypt/Werkzeug hashing.
- **Database:** SQLAlchemy with default SQLite (`sqlite:///multimosaic.db`); models: User, FoodPost, PickupRequest, Message.
- **Payments:** Razorpay Orders + signature verification; payouts prepared via Razorpay Payout APIs (guarded with availability checks) for delivery and donor earnings; refunds on rejection.
- **Geocoding & Distance:** OpenCageGeocode API to resolve addresses and compute Haversine distance for matching and delivery selection.
- **File storage:** Uploaded food images stored in `app/static/uploads/`.
- **Session/Auth:** Flask-Login sessions with long-lived cookies; OTP-based registration; email login notifications.
- **Error handling:** Custom 404 template; basic flash-based error surfacing.

### Data Flow (Happy Path)
1. Donor/restaurant posts food → stored as `FoodPost` with optional price and image.
2. NGO/beneficiary searches/listings → requests pickup → Razorpay payment created if payable.
3. Payment success → `PickupRequest` marked "Payment Successful" → donor notified → donor accepts or rejects.
4. On acceptance → delivery partner auto-picked by proximity or delivery user self-accepts → OTPs generated for arrival and completion.
5. Delivery marks completion with requester OTP → optional payouts to delivery and donor processed.
6. Status transitions reflected in request/delivery dashboards.

## Technical Deep Dive
- **Languages:** Python 3, HTML/CSS/JS (templated).
- **Key modules:**
  - App bootstrap: [app/__init__.py](app/__init__.py#L1-L43)
  - Config & env: [config.py](config.py#L1-L39)
  - Models: [app/models.py](app/models.py#L1-L88) (`User`, `FoodPost`, `PickupRequest`, `Message`), status enum `RequestStatus`.
  - Forms: [app/forms.py](app/forms.py#L1-L83) (`RegistrationForm`, `LoginForm`, `FoodPostForm`, `OTPForm`, `ProfileEditForm`).
  - Routes & business logic: [app/routes.py](app/routes.py).
- **Business rules (selected):**
  - Registration requires email OTP; passwords hashed with Werkzeug.
  - Pickup request pricing: delivery fee ₹30/₹45 by distance; optional platform fee; GST 5% on subtotal; commission on donor payout (20% under ₹100, else 15%).
  - Refunds executed only when payment exists and donor rejects.
  - Delivery partner auto-selection requires both pickup and drop within 5 km; otherwise manual pool for delivery users.
  - OTPs generated for delivery arrival (`delivery_otp`) and requester completion (`requester_otp`).
- **Security practices:** hashed passwords; CSRF via Flask-WTF; signature verification on payments; long session lifetimes configurable.
- **Engineering quality:** Straightforward MVC with service logic in routes; database operations wrapped with commits/rollbacks; defensive checks for auth/role and payment config.

## Installation & Setup Guide
### Prerequisites
- Python 3.9+ recommended
- pip
- (Optional) Virtualenv/venv

### Steps
1. **Clone & enter project**
   ```bash
   git clone <repo-url>
   cd CorteX
   ```
2. **Create virtual environment (recommended)**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set environment variables** (see [Environment Variables](#environment-variables--configuration)). On Windows PowerShell example:
   ```powershell
   $env:SECRET_KEY="your-secret"
   $env:SQLALCHEMY_DATABASE_URI="sqlite:///multimosaic.db"
   $env:MAIL_USERNAME="you@example.com"
   $env:MAIL_PASSWORD="app-password"
   $env:OPENCAGE_API_KEY="your-key"
   $env:RAZORPAY_KEY_ID="your-key-id"
   $env:RAZORPAY_KEY_SECRET="your-key-secret"
   $env:RAZORPAY_ACCOUNT_NUMBER="your-razorpay-account"
   ```
5. **Initialize database** (auto-creates on first run via `db.create_all()`). For migrations you can add Flask-Migrate commands if desired.
6. **Run the server**
   ```bash
   python run.py
   ```
7. **Access the app**
   - Web: http://localhost:5000
   - Admin portal: http://localhost:5000/admin/login (default creds from env/defaults).

### Troubleshooting
- Missing Razorpay/OpenCage keys: payment or distance features gracefully warn/skip.
- SQLite locking on Windows: ensure single running process and no parallel writers.
- Email issues: verify SMTP/ports and allow less-secure/app passwords for Gmail if used.

## Usage Guide
- **Register & verify:** Sign up with role, confirm OTP sent via email, then log in.
- **Dashboards:** Role-specific stats and shortcuts.
- **Post food (restaurant/donor):** Add item details, price (optional), auto-fill address via geolocation, upload image, manage stock.
- **Browse & request (NGO/beneficiary):** View distance-aware listings, request pickup; complete payment if required.
- **Payments:** On payable items, complete Razorpay checkout; status becomes "Payment Successful".
- **Donor actions:** Accept/reject requests; auto-assign delivery partner or let pool pick up; mark arrival via OTP.
- **Delivery users:** See available deliveries in their city, accept tasks, collect/requester OTP to complete.
- **Completion:** Delivery partner enters requester OTP to mark complete; payouts attempted if Razorpay Payout APIs available.
- **Admin:** Login to view/delete users.

## Environment Variables / Configuration
| Variable | Purpose | Default |
| --- | --- | --- |
| SECRET_KEY | Flask session/CSRF secret | `change-me` |
| SQLALCHEMY_DATABASE_URI | DB connection string | `sqlite:///multimosaic.db` |
| MAIL_SERVER | SMTP host | `smtp.gmail.com` |
| MAIL_PORT | SMTP port | `587` |
| MAIL_USE_TLS | TLS for SMTP | `True` |
| MAIL_USE_SSL | SSL for SMTP | `False` |
| MAIL_USERNAME | SMTP user | None |
| MAIL_PASSWORD | SMTP password | None |
| MAIL_DEFAULT_SENDER | From address fallback | `MAIL_USERNAME` or `multimosaic.help@gmail.com` |
| ADMIN_USERNAME | Admin login | `cortex` |
| ADMIN_PASSWORD | Admin password | `cortex@6708` |
| REMEMBER_COOKIE_DURATION_DAYS | Session remember duration | `365` |
| PERMANENT_SESSION_LIFETIME_DAYS | Permanent session TTL | `365` |
| OPENCAGE_API_KEY | Geocoding key | None |
| RAZORPAY_KEY_ID | Razorpay public key | None |
| RAZORPAY_KEY_SECRET | Razorpay secret key | None |
| RAZORPAY_ACCOUNT_NUMBER | Razorpay payout account | None |

## Project Screens / Pages
- Public: home, search, about, terms, privacy, 404.
- Auth: register (with geolocation autofill), verify OTP, login, profile, edit profile.
- Listings: post/edit/delete, detail view, mark in/out of stock, search results, paginated listings view.
- Requests: view pickup requests, payments detail, payment checkout, request status for donors.
- Delivery: available deliveries, my deliveries, OTP completion.
- Dashboards: donor, restaurant, NGO, beneficiary, delivery (Chart.js analytics).
- Admin: admin login, user list/delete.

## Security & Privacy Notes
- Passwords hashed; CSRF enabled via Flask-WTF.
- OTP verification for registration and delivery flows; Razorpay signature verification on payments.
- Long session lifetimes—set stricter durations in production.
- Admin credentials default to weak values—override in production.
- File uploads stored locally without size/type throttling beyond extension checks (jpg/png/jpeg).
- Email transport relies on provided SMTP; avoid hardcoding secrets; use env vars.
- Payout APIs invoked only if Razorpay resources are present; errors fall back to marking complete with warning.

## Performance & Optimization Notes
- SQLite default is fine for small deployments; migrate to PostgreSQL for concurrency.
- Geocoding is per-request; consider caching coordinates per address to reduce API calls.
- Template rendering is server-side; suitable for current scope; add pagination already present for listings.
- Batch queries could replace per-item lookups in some routes to reduce DB calls.

## Limitations & Known Issues
- No automated tests included.
- File uploads lack size limits and content scanning.
- Payment page embeds test key in script tag; ensure it matches server-side env in production.
- Delivery partner auto-selection requires OpenCage key and accurate addresses; falls back quietly otherwise.
- Admin panel permits user deletion without soft-delete or audit trail.
- Session lifetime defaults are long; review for security compliance.

## Future Enhancements
1. Add unit/integration tests and CI pipeline.
2. Introduce role-based access middleware and audit logging.
3. Add rate limiting for OTP/email and payment endpoints.
4. Replace local uploads with object storage (S3/Blob) and CDN.
5. Add push/email templates and notification preferences.
6. Improve donor/delivery payout reconciliation and webhooks for payment/payout events.
7. Add internationalization and accessibility audits.
8. Implement soft deletes and activity logs for admin actions.

## Real-World Value & Business Perspective
- Enables zero-commission food redistribution, lowering waste-disposal costs for restaurants and creating social impact metrics for CSR reporting.
- NGOs and beneficiaries gain reliable, geo-aware access to surplus food with transparent status tracking.
- Delivery partners can earn per-trip charges; donors can monetize paid items with commission handling.
- Provides a foundation for city-level food rescue networks and CSR partnerships.

## Contribution Guidelines
- Fork and branch per feature; prefer PRs with clear descriptions.
- Run formatting/linting as applicable; keep commits scoped.
- Cover new logic with tests (to be added) and update README for config changes.
- Avoid committing secrets; use env vars and `.env` locally.

## License
No explicit license is provided. All rights reserved by the authors/owners of this repository.

## Conclusion
CorteX delivers a practical, multi-role platform to curb food waste and hunger through transparent logistics, payments, and OTP-verified deliveries. With clearer configuration, stronger security defaults, and added tests, it is ready to support real-world food rescue operations at scale.

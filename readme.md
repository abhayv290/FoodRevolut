# djFood API

djFood is a Django REST backend for a Swiggy/Zomato-style food delivery app.
It supports multiple user roles, full order flow, payments, reviews, search, and real-time order tracking over WebSockets.

## What is already built

- Role-based auth for Customer, Restaurant Owner, and Delivery Agent
- JWT login/refresh/logout with email verification and password reset flow
- Restaurant, category, menu item, and variant management
- Cart and checkout flow with order lifecycle state transitions
- Payment integration flow (Razorpay initiate + verify)
- Restaurant and delivery reviews
- Search + autocomplete for restaurants and menu items
- Real-time tracking channel for live order updates

## Tech stack

- Django 6 + Django REST Framework
- PostgreSQL
- Redis + Django Channels (WebSocket)
- SimpleJWT
- drf-spectacular (OpenAPI docs)
- django-filter
- django-cors-headers

## Apps overview

- apps.users: Handles authentication, role-based user accounts, profile management, addresses, email verification, and password flows.
- apps.restaurants: Manages restaurants, categories, menu items, variants, and restaurant-level operational details.
- apps.orders: Covers cart, cart items, checkout, order creation, order items, status transitions, and order history.
- apps.payments: Integrates payment lifecycle for orders (initiate, verify, status tracking) using Razorpay.
- apps.reviews: Lets customers review restaurants and delivery agents after completed orders.
- apps.search: Provides search and autocomplete endpoints for restaurants and menu items.
- apps.tracking: Powers real-time order tracking through WebSocket consumers and routing.
- core: Shared project utilities like permissions, pagination, and centralized exception handling.
- config: Project configuration for settings, URL wiring, ASGI/WSGI entry points, and environment-specific behavior.

## Quick start (local)

1. Clone the repo and move into it.
2. Start infra services:

```powershell
docker compose up -d
```

3. Create and activate virtual env:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

5. Create a .env file in project root (sample below).
6. Run migrations:

```powershell
python manage.py migrate
```

7. Start server:

```powershell
python manage.py runserver
```

API will be available at http://127.0.0.1:8000/

## Minimal .env example

```env
SECRET_KEY=change-this
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=djFoodDb
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0

CORS_ALLOWED_ORIGINS=http://localhost:5173

RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret

MAILGUN_API_KEY=your_mailgun_key
MAILGUN_DOMAIN=your_mailgun_domain
DEFAULT_FROM_EMAIL=noreply@example.com
```

## API entry points

Base API prefix: /api/v1/

- Auth + profiles: /api/v1/auth/* and role profile endpoints
- Restaurants and menus: /api/v1/restaurants/
- Cart + orders: /api/v1/cart/, /api/v1/orders/
- Payments: /api/v1/payments/
- Reviews: /api/v1/reviews/
- Search: /api/v1/search/

### Docs

- Swagger UI: /api/docs/
- ReDoc: /api/redoc/
- OpenAPI schema: /api/schema

## WebSocket tracking

Use this endpoint for live tracking updates:

ws://127.0.0.1:8000/ws/tracking/<order_id>/?token=<access_token>

## Development notes

- Default settings module is local (config.settings.local).
- Silk profiling middleware is enabled in local settings.
- In development, media files are served by Django when DEBUG=True.


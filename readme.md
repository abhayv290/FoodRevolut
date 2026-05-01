# FoodRevolut API

Backend for a real-time food delivery platform. Full order lifecycle, payments, delivery tracking, and multi-role auth.

## What this is

A complete food delivery backend (think Swiggy/Zomato API). Customers order food, restaurants accept/prepare orders, delivery agents pick up and track, everything happens in real-time with WebSocket updates. Handles payments via Razorpay, manages order states, auto-cancels unpaid orders, notifies everyone via email, and tracks deliveries live on a map.

## Why I built this

Started as a learning project to practice building a real-world system with multiple actors, async tasks, payments, and real-time features. Got deep into order state machines, how to handle background jobs at scale, and building systems that don't fall apart when timing matters (like auto-canceling unpaid orders). It's the kind of problem that's easy to oversimplify and surprisingly hard to get right.

## Features

- **Auth & multi-role users**: Customers, restaurant owners, and delivery agents with JWT tokens and email verification
- **Restaurant browsing**: Search and filter by cuisine, city, rating, etc. Uses PostgreSQL full-text search for fast results
- **Cart & checkout**: Add items with variants (sizes, etc.), manage cart, calculate totals with delivery fees
- **Orders with state machine**: PLACED → ACCEPTED → PREPARING → READY → PICKED_UP → DELIVERED. Auto-transitions, auto-cancellation, status history
- **Payment gateway**: Razorpay integration with signature verification. Handles multiple payment methods (UPI, card, net banking, cash on delivery)
- **Auto-cancel unpaid orders**: Celery beat runs every 5 mins, cancels orders that are PLACED but not paid after 15 mins
- **Real-time delivery tracking**: WebSocket endpoint for customers/restaurants to track order location and status live
- **Automatic delivery agent assignment**: When order is ready, system finds nearest available agent and assigns it
- **Reviews & ratings**: Customers rate restaurants and delivery agents after order completion. Rating aggregation for restaurants
- **Email notifications**: Async email notifications for order status changes (order placed, accepted, ready, picked up, delivered) + payment confirmations
- **Menu management**: Restaurants manage categories, items, variants, availability
- **Customer addresses**: Save multiple delivery addresses (home, work, other) with geo-coordinates

## Tech Stack

**Backend**
- Django 6, Django REST Framework
- SimpleJWT for auth (with token blacklist support)
- PostgreSQL (with full-text search indexes)
- drf-spectacular for auto-generated API docs

**Real-time & Async**
- Django Channels + Daphne for WebSocket support
- Redis + Celery for background tasks
- Celery Beat for scheduled tasks

**Infrastructure**
- Docker + Docker Compose (multi-stage builds, health checks)
- Nginx as reverse proxy
- Redis for caching and message broker

**Integrations**
- Razorpay for payments
- AnyMail for email (flexible backend: SendGrid, Mailgun, etc.)

## How it works

### Order Flow
1. Customer searches restaurants → builds cart with items/variants → enters delivery address and payment method
2. Checkout creates order with PLACED status and Payment record (if online payment)
3. If online payment: redirect to Razorpay, customer pays, webhook updates Payment status
4. Auto-cancel task checks every 5 mins: if PLACED + unpaid + 15 mins old → CANCELLED
5. Restaurant sees order, accepts it → status becomes ACCEPTED
6. Kitchen prepares → status becomes PREPARING, then READY
7. When READY, auto-assign task finds nearest available delivery agent and assigns
8. Delivery agent picks up order → status becomes PICKED_UP
9. Agent navigates to customer, pushes location updates via WebSocket to customer in real-time
10. Delivers order → status becomes DELIVERED
11. Customer rates both restaurant and delivery agent

### Real-time Tracking
- WebSocket endpoint: `ws://host/ws/tracking/<order_id>/?token=<jwt_token>`
- JWT validation happens at connection time (query param, since WebSocket doesn't support headers)
- Permission check: only customer, restaurant, and assigned delivery agent can access
- Server broadcasts location updates and status changes to all connected clients in the order's channel group
- If connection drops, client reconnects—no data loss, just latest state

### Background Jobs
- **notify_order_status_changed**: Runs async after every order status change. Sends targeted emails to customer, restaurant, or delivery agent depending on status
- **cancel_unpaid_orders**: Celery Beat task, runs every 5 mins. Finds orders that are PLACED + unpaid + older than 15 mins, cancels them
- **assign_delivery_agent_task**: Triggered when order becomes READY. Finds nearest available agent, assigns, retries up to 5 times if no agent found

### Search
- Uses PostgreSQL full-text search (FTS) with weighted vectors
- Restaurant name gets weight A (most important), cuisine_type gets B, description gets C
- Filters applied after FTS: city, cuisine_type, is_premium, is_open, rating
- Menu item search across all restaurants with price range and vegetarian filters

## Local Setup

Prerequisites: Docker and Docker Compose installed.

### Step 1: Environment setup

```powershell
Copy-Item .env.example .env
```

### Step 2: Update `.env` with your values

```env
# Database
DB_NAME=fooddb
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Payments (Razorpay)
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret

# Email (example: using console backend for local testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# For production, use AnyMail with your email service provider
ANYMAIL_MAILGUN_API_KEY=your_key
```

### Step 3: Start services

```powershell
docker compose -f docker-compose.yaml up --build
```

This starts:
- **web** (port 8000): Django + Daphne WebSocket server
- **worker**: Celery worker for async tasks
- **beat**: Celery Beat for scheduled tasks
- **db**: PostgreSQL
- **nginx** (port 80): Reverse proxy (routes to web)
- **redis**: Cache and message broker (not exposed)

### Step 4: Create superuser and test

```bash
docker compose exec web python manage.py createsuperuser
```

Then visit:
- Admin: `http://localhost/admin/`
- API Docs (Swagger): `http://localhost/api/docs/`
- ReDoc: `http://localhost/api/redoc/`
- Health check: `http://localhost/api/health/`

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection | `fooddb` / `postgres` / `password` / `db` / `5432` |
| `REDIS_URL` | Redis connection for Celery & cache | `redis://redis:6379/0` |
| `SECRET_KEY` | Django secret key | Random 50+ char string |
| `DEBUG` | Django debug mode | `True` (local) / `False` (prod) |
| `ALLOWED_HOSTS` | Allowed domain names | `localhost,127.0.0.1` |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay API credentials | Available in Razorpay dashboard |
| `EMAIL_BACKEND` | Email service | `django.core.mail.backends.console.EmailBackend` (local) |
| `ANYMAIL_*` | AnyMail config (prod) | Varies by provider (SendGrid, Mailgun, etc.) |
| `DJANGO_SETTINGS_MODULE` | Settings module | `config.settings.local` (dev) / `config.settings.prod` (prod) |

## API Endpoints

Base URL: `/api/v1/`

**Authentication**
- `POST /auth/register/` - Sign up
- `POST /auth/login/` - Get JWT tokens
- `POST /auth/refresh/` - Refresh access token
- `POST /auth/logout/` - Blacklist token

**Restaurants**
- `GET /restaurants/` - List restaurants (paginated)
- `GET /restaurants/{id}/` - Restaurant details with menu
- `GET /restaurants/{id}/reviews/` - Restaurant reviews

**Orders**
- `GET /cart/` - Get or create cart
- `POST /cart/item/` - Add item to cart
- `PATCH /cart/item/{id}/` - Update quantity
- `DELETE /cart/item/{id}/` - Remove from cart
- `POST /checkout/` - Create order from cart
- `GET /orders/` - List customer's orders
- `GET /orders/{id}/` - Order details with items and status history
- `PATCH /orders/{id}/status/` - Update order status (restaurant/admin only)

**Payments**
- `POST /payments/initiate/` - Create Razorpay order
- `POST /payments/verify/` - Verify payment (called by mobile app after Razorpay callback)

**Reviews**
- `POST /reviews/restaurant/` - Leave restaurant review
- `POST /reviews/delivery/` - Leave delivery agent review

**Search**
- `GET /search/restaurants/?q=pizza&city=kanpur&cuisine_type=PIZZA&ordering=-average_rating` - Full-text search restaurants
- `GET /search/menu-item/?q=pizza&is_veg=true&max_price=300` - Search menu items

**WebSocket**
- `ws://host/ws/tracking/{order_id}/?token=<jwt_token>` - Real-time order tracking

Full docs: `/api/docs/`

## Interesting Implementation Details

### Order State Machine
Order status is a choice field with specific allowed transitions:
- PLACED → ACCEPTED (restaurant accepts)
- ACCEPTED → PREPARING (kitchen starts)
- PREPARING → READY (food ready, trigger delivery agent assignment)
- READY → PICKED_UP (agent picks up)
- PICKED_UP → DELIVERED (agent delivers)
- Any state → CANCELLED (customer/restaurant/system can cancel)

Each transition is tracked in `OrderStatusHistory` with timestamp and optional notes.

### JWT Auth on WebSocket
WebSockets don't support custom headers like HTTP. JWT token is passed as query parameter: `?token=<access_token>`. The consumer extracts it, validates it using SimpleJWT's `AccessToken` class, and rejects connection if invalid or user doesn't have access.

### Pricing Snapshots
When order is placed, `subtotal`, `delivery_fee`, and `total_amount` are captured in the Order model. This prevents issues when restaurant later changes menu item prices—the customer gets charged what was shown at checkout.

### Celery Task Retries
Payment and order assignment tasks use Celery's retry mechanism. Example: `assign_delivery_agent_task` retries up to 5 times with 2-minute delays if no agent found. Uses exponential backoff to avoid hammering the system.

### Search Weighted Vectors
Restaurant search uses PostgreSQL FTS with weight-based ranking:
- Restaurant name (weight A = 1.0): highest priority
- Cuisine type (weight B = 0.4)
- Description (weight C = 0.2)

Results ranked by relevance score, then paginated.

### Email Notifications Async
Order status change views call `.delay()` on notify tasks instead of executing synchronously. View responds immediately to client, Celery worker sends emails in background. If email fails, Celery retries 3 times with exponential backoff.

## Known Limitations & TODOs

- **No geo-distance filtering yet**: Restaurant search filters by city (text) but doesn't sort by distance. Need to add PostGIS for proper geo queries
- **Delivery agent auto-assignment is naive**: Currently just finds first available agent, not nearest one. Should calculate distance using lat/long coordinates
- **No refunds**: Payment model has a REFUNDED status but no refund flow implemented
- **Cart can only hold one restaurant**: Design choice for simplicity. Real apps let you order from multiple restaurants
- **No order cancellation after PICKED_UP**: Currently you can cancel anytime, but realistically shouldn't cancel during delivery
- **Email templates are basic**: Using plain text, should move to HTML templates
- **No rate limiting on API**: Could abuse payment endpoint or search. Should add DRF throttling
- **WebSocket connection pooling**: For production with thousands of concurrent orders, consider separate WebSocket server (e.g., with Celery)

## Production Notes

- Use `docker-compose.prod.yaml` (loads from ECR)
- Settings: `config/settings/prod.py` (forces DEBUG=False, stricter allowed hosts, HTTPS, etc.)
- Database: Use AWS RDS PostgreSQL instead of containerized Postgres
- Redis: Use AWS ElastiCache or similar managed service
- Media uploads: Store in S3 bucket (configure with AnyMail/Pillow)
- Email service: Configure AnyMail with SendGrid/Mailgun/AWS SES
- Logging: Configure CloudWatch or similar centralized logging
- Monitoring: Add Sentry for error tracking

## Commands

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Shell
docker compose exec web python manage.py shell

# View Celery tasks (local only)
docker compose exec web celery -A config inspect active

# View scheduled tasks
docker compose exec web celery -A config inspect scheduled

# Rebuild image
docker compose build

# Stop services
docker compose down
```

## License

Not specified. Update this if you plan to publish.


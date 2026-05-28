# Bloom & Basket Flower Shop

Bloom & Basket is a small Django flower shop built for an undergraduate web applications course. Customers can browse flower products, register, log in, use a session cart, complete a simulated purchase, and view saved order history. Employees use Django admin to manage products and inspect orders.

Checkout is intentionally simulated for instruction. The app never asks for credit card data, never stores payment details, and automatically marks purchases as approved when inventory is available.

## Classroom Storage Warning

This repository uses SQLite locally and in the requested Google Cloud Run demo. On Cloud Run, the SQLite file is stored at `/tmp/db.sqlite3` through `SQLITE_DB_PATH`. Cloud Run container filesystems are disposable, so product changes and orders are not durable production storage. Data can be lost when the container is replaced, scaled down, or redeployed.

The workflow deploys with `--max-instances=1` to avoid multiple Cloud Run instances writing to the same SQLite file. This is appropriate for a classroom deployment pipeline demonstration, not a reliable production e-commerce database.

## Features

- Public home page, catalog, and product detail pages.
- Product stock visibility, including out-of-stock messaging.
- Customer registration, login, logout, and customer-only order history.
- Session-backed cart with add, update, remove, inventory caps, totals, and CSRF-protected POST actions.
- Transactional simulated checkout that snapshots product name and price, decrements inventory, saves orders, and clears the cart only after success.
- Authorization filters that prevent customers from viewing other customers' orders.
- Django admin registration for `Product`, `Order`, and `OrderItem`.
- Console logging for registrations, successful simulated orders, insufficient-stock checkout failures, and unexpected checkout errors.
- Docker, Gunicorn, WhiteNoise, and GitHub Actions deployment to Cloud Run.

## Local Setup

Use Python 3.12 if available.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_products
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Run the test suite:

```bash
python -m pytest
```

Run production-style checks with explicit environment variables:

```bash
DJANGO_DEBUG=False \
DJANGO_SECRET_KEY=replace-this-with-a-long-random-secret-for-real-deployments \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000 \
DJANGO_SECURE_SSL_REDIRECT=True \
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True \
DJANGO_SECURE_HSTS_PRELOAD=True \
python manage.py check --deploy
```

## Environment Variables

- `DJANGO_SECRET_KEY`: Required when `DJANGO_DEBUG=False`.
- `DJANGO_DEBUG`: Use `True` locally and `False` in deployment.
- `DJANGO_ALLOWED_HOSTS`: Comma-separated hostnames, for example `example.run.app,www.example.com`.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: Comma-separated trusted origins including scheme, for example `https://example.run.app`.
- `SQLITE_DB_PATH`: SQLite database path. Defaults to `db.sqlite3` locally and `/tmp/db.sqlite3` on Cloud Run.
- `DJANGO_SECURE_SSL_REDIRECT`: Set to `True` on Cloud Run.
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` and `DJANGO_SECURE_HSTS_PRELOAD`: Optional hardening settings for domains where you are certain HTTPS should apply.
- `DJANGO_LOG_LEVEL` and `STORE_LOG_LEVEL`: Optional logging levels.
- `PORT`: Provided by Cloud Run; defaults to `8080` in the container.

Do not commit `.env` files, service account keys, secrets, or runtime SQLite databases.

## Admin Use

Create a local admin account:

```bash
python manage.py createsuperuser
```

Then visit `/admin/`. Staff and superuser accounts can add and update products and inspect orders. Customer registrations always create ordinary non-staff users.

For a Cloud Run classroom demo, create a superuser through a controlled one-off shell or job after deployment, then remove that access path. Do not hardcode admin credentials in this repository.

## Docker

Build and run locally:

```bash
docker build -t flower-shop .
docker run --rm -p 8080:8080 \
  -e DJANGO_SECRET_KEY=local-container-secret \
  -e DJANGO_DEBUG=False \
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8080 \
  flower-shop
```

The container runs migrations and `collectstatic`, then starts Gunicorn on `PORT`.

## Google Cloud Run Deployment

The workflow in `.github/workflows/deploy.yml` runs tests, builds a Docker image, pushes it to Artifact Registry, and deploys to Cloud Run. It uses Workload Identity Federation through `google-github-actions/auth@v3`; no long-lived service account JSON key is required.

Before the first deployment:

1. Enable required APIs: Cloud Run, Artifact Registry, IAM Credentials, and Secret Manager.
2. Create an Artifact Registry Docker repository.
3. Create a Secret Manager secret containing the Django secret key.
4. Create or choose a deployment service account with permissions for Cloud Run deployment, Artifact Registry push, and Secret Manager access. Typical roles include Cloud Run Admin, Artifact Registry Writer, Secret Manager Secret Accessor, and Service Account User on the runtime service account.
5. Configure GitHub Workload Identity Federation for this repository and grant the GitHub principal permission to impersonate the deployment service account.
6. Add repository variables:
   - `GCP_PROJECT_ID`
   - `GCP_REGION`
   - `GCP_ARTIFACT_REPOSITORY`
   - `CLOUD_RUN_SERVICE`
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`
   - `GCP_SERVICE_ACCOUNT`
   - `DJANGO_SECRET_KEY_SECRET_NAME`
   - `DJANGO_ALLOWED_HOSTS`
   - `DJANGO_CSRF_TRUSTED_ORIGINS`

The deploy step sets `SQLITE_DB_PATH=/tmp/db.sqlite3`, `DJANGO_DEBUG=False`, `DJANGO_SECURE_SSL_REDIRECT=True`, port `8080`, and `--max-instances=1`.

## Path to Production

A real flower shop should move persistence to a durable database such as Cloud SQL for PostgreSQL. The customer-facing models, views, templates, cart, checkout, and admin concepts can stay largely the same; the main change is replacing the Django `DATABASES` configuration and adding a production database service, credentials, backups, and migrations strategy.

## Logging

Application logs go to standard output, where Cloud Run captures them. The app logs new customer registrations, successful simulated orders, insufficient inventory checkout failures, and unexpected checkout errors without logging passwords, sessions, payment data, or secrets.

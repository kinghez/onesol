# 🚀 OneSol AI Hub — Render Deployment Guide

## Files Created / Changed in Codebase

| File | Purpose |
|---|---|
| `onesolai/settings.py` | Full production config (env-vars driven) |
| `onesolai/email_backend.py` | Resend API email backend |
| `build.sh` | Render build script (install → collectstatic → migrate) |
| `runtime.txt` | Python 3.12.3 |
| `requirements.txt` | Lean production dependencies |
| `.gitignore` | Protects secrets, excludes DB/media |
| `.env.production.example` | Template of all env vars to set on Render |
| `vendors/sync.py` | Celery-free vendor product sync |

---

## Step 1 — Push to GitHub

Your code changes are committed. Push them to your GitHub repository:

```bash
git push origin main
```

---

## Step 2 — Create Render Web Service

1. Go to [render.com](https://render.com) → **New +** → **Web Service**
2. Connect your GitHub account → select **kinghez/onesol** repo
3. Fill in the deployment settings:

| Field | Value |
|---|---|
| **Name** | `onesolai` |
| **Root Directory** | `onesolai` |
| **Runtime** | `Python 3` |
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn onesolai.wsgi:application --workers 2 --timeout 120` |
| **Instance Type** | **Free** |

> [!IMPORTANT]
> **Root Directory must be `onesolai`** — that's the inner folder where `manage.py` lives.

---

## Step 3 — Set Environment Variables on Render

In your Web Service → **Environment** tab, add these key-value pairs:

| Key | Value |
|---|---|
| `SECRET_KEY` | Run `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` to generate one |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `onesolai.onrender.com,onesolai.com,www.onesolai.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://onesolai.onrender.com,https://onesolai.com,https://www.onesolai.com` |
| `DATABASE_URL` | `postgresql://postgres.qwrtyzzmrduybtfpfzmk:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres` |
| `CLOUDINARY_URL` | `cloudinary://127128733577438:v0mJx8v2FIPRwqsvTTjI_hcrxkM@obgie1pr` |
| `RESEND_API_KEY` | `re_xxxxxxxxxxxxxxxxxxxxxxxx` |
| `DEFAULT_FROM_EMAIL` | `OneSol AI Hub <noreply@onesolai.com>` |
| `PAYSTACK_PUBLIC_KEY` | Your live Paystack public key (`pk_live_...`) |
| `PAYSTACK_SECRET_KEY` | Your live Paystack secret key (`sk_live_...`) |
| `PAYSTACK_CALLBACK_URL` | `https://onesolai.com/orders/callback/` |
| `FLW_PUBLIC_KEY` | Your live Flutterwave public key (`FLWPUBK_LIVE-...`) |
| `FLW_SECRET_KEY` | Your live Flutterwave secret key (`FLWSECK_LIVE-...`) |
| `FLW_CALLBACK_URL` | `https://onesolai.com/orders/flutterwave/callback/` |

---

## Step 4 — Deploy & Create Superuser

1. Click **Create Web Service** → Render will build & deploy (takes ~3 minutes).
2. Once deployed, open the **Shell** tab on Render and run:
```bash
python manage.py createsuperuser
```

---

## Step 5 — Link Custom Domain (onesolai.com)

### On Render:
1. Go to Web Service → **Settings** → **Custom Domains**.
2. Click **Add Custom Domain** → enter `onesolai.com`.
3. Also add `www.onesolai.com`.

### On Cloudflare:
1. Go to your Cloudflare DNS dashboard for `onesolai.com`.
2. Add the records Render provides:
   - `CNAME  @  onesolai.onrender.com` (proxied ✅)
   - `CNAME  www  onesolai.onrender.com` (proxied ✅)

---

## Step 6 — Resend Email Domain Verification

For Resend to send emails from `@onesolai.com`:
1. Go to [resend.com](https://resend.com) → **Domains** → **Add Domain**.
2. Enter `onesolai.com`.
3. Copy the DNS records (DKIM, SPF, MX) provided by Resend and add them to Cloudflare DNS.
4. Click **Verify** on Resend.

---

## Step 7 — Paystack & Flutterwave Dashboard Webhook Setup

### Where to set this up:
Webhooks are configured inside your online Paystack and Flutterwave developer dashboards (not directly in code).

1. **Paystack Dashboard**:
   - Log in to [dashboard.paystack.com](https://dashboard.paystack.com)
   - Go to **Settings** → **API Keys & Webhooks**
   - Under **Live Webhook URL**, enter:
     `https://onesolai.com/orders/callback/`
   - Save changes.

2. **Flutterwave Dashboard**:
   - Log in to [dashboard.flutterwave.com](https://dashboard.flutterwave.com)
   - Go to **Settings** → **Webhooks**
   - Enter your **Live Webhook URL**:
     `https://onesolai.com/orders/flutterwave/callback/`
   - Save changes.

---

## Step 8 — Keep-Alive Cron (cron-job.org)

To keep Render (15-min sleep limit) and Supabase (7-day pause limit) alive on the free tier:

1. Sign up at [cron-job.org](https://cron-job.org).
2. Create 2 scheduled jobs:
   - **Render Keep-Alive**: `https://onesolai.com/` (every 10 minutes)
   - **Supabase Keep-Alive**: `https://onesolai.com/` (every 3 days)

---

## Step 9 — Database Content Migration (Optional)

To copy your local categories, tools, site settings, and FAQs into Supabase:

```bash
# 1. Export local content
python manage.py dumpdata products core.sitesettings analytics --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission -o content_backup.json

# 2. In your local terminal, temporarily set DATABASE_URL to your Supabase URL
export DATABASE_URL="postgresql://postgres.qwrtyzzmrduybtfpfzmk:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# 3. Run migrations and load data onto Supabase
python manage.py migrate
python manage.py loaddata content_backup.json
python manage.py createsuperuser
```

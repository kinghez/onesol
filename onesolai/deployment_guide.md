# 🚀 OneSol AI Hub — Complete Render Deployment Guide

> All credentials below are your real values. Copy them directly into Render.  
> **Never share this file publicly or commit it with real secrets to a public repo.**

---

## Step 1 — Create Render Web Service

1. Go to [render.com](https://render.com) → Sign in → **New +** → **Web Service**
2. Connect your GitHub account → Select repo: **kinghez/onesol**
3. Fill in these settings:

| Field | Value |
|---|---|
| **Name** | `onesolai` |
| **Root Directory** | `onesolai` |
| **Runtime** | `Python 3` |
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn onesolai.wsgi:application --workers 2 --timeout 120` |
| **Instance Type** | **Free** |

> ⚠️ **Root Directory MUST be `onesolai`** — that is the subfolder inside the repo where `manage.py` lives.

---

## Step 2 — Add All Environment Variables on Render

Go to your Web Service → **Environment tab** → Add each row below:

| Key | Value |
|---|---|
| `SECRET_KEY` | `d_6wps4naiy%3judj&peh#shpwb3+=w0^2ik46a3=iq%apbp^^` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `onesolai.onrender.com,onesolai.com,www.onesolai.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://onesolai.onrender.com,https://onesolai.com,https://www.onesolai.com` |
| `DATABASE_URL` | `postgresql://postgres.qwrtyzzmrduybtfpfzmk:191Kinghez***@aws-0-eu-central-1.pooler.supabase.com:6543/postgres` |
| `CLOUDINARY_URL` | `cloudinary://127128733577438:v0mJx8v2FIPRwqsvTTjI_hcrxkM@obgie1pr` |
| `RESEND_API_KEY` | `re_xxxxxxxxxxxxxxxxxxxxxxxx` |
| `DEFAULT_FROM_EMAIL` | `OneSol AI Hub <noreply@onesolai.com>` |
| `PAYSTACK_PUBLIC_KEY` | *(your live Paystack public key — pk_live_...)* |
| `PAYSTACK_SECRET_KEY` | *(your live Paystack secret key — sk_live_...)* |
| `PAYSTACK_CALLBACK_URL` | `https://onesolai.com/orders/callback/` |
| `FLW_PUBLIC_KEY` | *(your live Flutterwave public key — FLWPUBK_LIVE-...)* |
| `FLW_SECRET_KEY` | *(your live Flutterwave secret key — FLWSECK_LIVE-...)* |
| `FLW_CALLBACK_URL` | `https://onesolai.com/orders/flutterwave/callback/` |

> ⚠️ Replace `191Kinghez***` in DATABASE_URL with your real Supabase database password.

---

## Step 3 — Deploy & Create Admin Superuser

1. Click **Create Web Service** — Render will build & deploy (takes 3–5 minutes first time)
2. Watch the **Logs** tab for any errors
3. Once live, go to **Shell** tab on Render and run:

```bash
python manage.py createsuperuser
```

---

## Step 4 — Link Custom Domain (onesolai.com)

### On Render:
1. Web Service → **Settings** → **Custom Domains**
2. Click **Add Custom Domain** → enter `onesolai.com`
3. Also add `www.onesolai.com`
4. Render shows you a CNAME value to use on Cloudflare

### On Cloudflare (DNS tab for onesolai.com):
Add these two records:

| Type | Name | Target | Proxied |
|---|---|---|---|
| `CNAME` | `@` | `onesolai.onrender.com` | ✅ Yes |
| `CNAME` | `www` | `onesolai.onrender.com` | ✅ Yes |

Render auto-provisions free SSL (Let's Encrypt) within ~5 minutes.

---

## Step 5 — Resend Email Domain Verification

So Resend can send emails from `@onesolai.com`:

1. Go to [resend.com](https://resend.com) → **Domains** → **Add Domain**
2. Enter `onesolai.com`
3. Resend gives you DNS records (DKIM TXT records + SPF + MX)
4. Add ALL of them in Cloudflare DNS
5. Click **Verify** on Resend — wait for green checkmarks

---

## Step 6 — Paystack & Flutterwave Webhook Configuration

These are set inside your **payment provider dashboards** (not in code):

### Paystack:
1. Log in to [dashboard.paystack.com](https://dashboard.paystack.com)
2. Go to **Settings** → **API Keys & Webhooks**
3. Set **Live Webhook URL** to:
   ```
   https://onesolai.com/orders/callback/
   ```

### Flutterwave:
1. Log in to [dashboard.flutterwave.com](https://dashboard.flutterwave.com)
2. Go to **Settings** → **Webhooks**
3. Set **Live Webhook URL** to:
   ```
   https://onesolai.com/orders/flutterwave/callback/
   ```

---

## Step 7 — Keep-Alive Cron (Prevent Free Tier Sleeping)

Render sleeps after 15 min of inactivity. Supabase pauses after 7 days of no activity.

1. Sign up at [cron-job.org](https://cron-job.org) (free)
2. Create 2 cron jobs:

| Job | URL | Schedule |
|---|---|---|
| Render keep-alive | `https://onesolai.com/` | Every 10 minutes |
| Supabase keep-alive | `https://onesolai.com/` | Every 3 days |

---

## Step 8 — Migrate Local Content to Supabase (Optional)

If you want to move your local products, categories, FAQs, and site settings to the live database:

```bash
# 1. Export content from local SQLite
cd /home/kinghez/onesol/onesolai
/home/kinghez/myenv/bin/python manage.py dumpdata \
  products core.sitesettings analytics \
  --natural-foreign --natural-primary \
  --exclude contenttypes --exclude auth.permission \
  -o content_backup.json

# 2. Set DATABASE_URL temporarily in your local terminal session
export DATABASE_URL="postgresql://postgres.qwrtyzzmrduybtfpfzmk:191Kinghez***@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
# (replace 191Kinghez*** with your real Supabase password)

# 3. Run migrations on Supabase
/home/kinghez/myenv/bin/python manage.py migrate

# 4. Load content into Supabase
/home/kinghez/myenv/bin/python manage.py loaddata content_backup.json

# 5. Create your superuser on Supabase
/home/kinghez/myenv/bin/python manage.py createsuperuser
```

---

## Deployment Architecture

```
Browser
   │
   ▼
Cloudflare (onesolai.com)       ← DNS + Proxy + SSL
   │
   ▼
Render Free Tier (Frankfurt)    ← Django + Gunicorn
   │
   ├── Static files  → WhiteNoise (bundled in app, no extra service)
   ├── Media files   → Cloudinary (obgie1pr)
   ├── Database      → Supabase PostgreSQL (Frankfurt eu-central-1)
   └── Email         → Resend API
```

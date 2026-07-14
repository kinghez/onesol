# OneSol AI Hub – Development Plan

## Project Overview
OneSol AI Hub is a premium AI & SaaS tools marketplace designed specifically for African users. It provides affordable, localized access to 100+ premium AI tools with payments in local African currencies (NGN, GHS, KES, ZAR, etc.) via Paystack and Flutterwave.

---

## ⚠️ CORE DESIGN PRINCIPLE: MOBILE-FIRST

> **This application is MOBILE-FIRST by design.**
>
> Over 90% of the target users access the platform from mobile devices (Android and iPhone).
> All UI components, layouts, and interactions must be designed and built starting from the
> smallest screen (320px wide) and progressively enhanced for larger screens.

### Mobile-First CSS Rules
- Base styles always target mobile (no `@media` wrapper needed)
- Use `@media (min-width: Xpx)` breakpoints to scale UP for tablet/desktop
- Never use `@media (max-width: ...)` to override desktop styles downward
- Touch targets must be at least 44×44px
- Font sizes: minimum 15px for body text, 26px+ for headings on mobile
- All forms must have password reveal toggles for usability
- Tab bars and navigation must be horizontally scrollable on mobile

### Breakpoints (min-width, scale UP)
| Breakpoint | Target |
|---|---|
| base (320px) | Mobile phones (primary target) |
| 480px | Large phones / small tablets |
| 768px | Tablets |
| 1024px | Laptops |
| 1280px | Desktops |

---

## Technology Stack
- **Frontend:** Pure HTML5, Vanilla CSS3 (mobile-first), Vanilla JavaScript
- **Backend:** Django 5.2 (Python 3.12)
- **Auth:** Custom `accounts.User` model with email as `USERNAME_FIELD`
- **Payments:** Paystack (primary) + Flutterwave (secondary)
- **Database:** SQLite (development) → PostgreSQL (production)
- **Static Files:** served via Django `staticfiles`

---

## Phase Status

### ✅ Phase 1 – Project Setup & Architecture
- Django project structure (`onesolai/`)
- Custom User model (email-based auth)
- Apps: `accounts`, `products`, `orders`, `core`
- Template/static file structure

### ✅ Phase 2 – Frontend Design & Templates
- Base templates: `base_public.html`, `base_auth.html`, `base_dashboard.html`
- Home page with hero carousel, trust bar, tool cards
- Auth pages: login, signup with referral code support and password reveal
- Dashboard with sidebar navigation, stat cards, subscription list
- All tools listing page with sidebar filters

### ✅ Phase 3 – Database Models
- `accounts`: `User`, `Profile` (wallet, referral code), `Referral`
- `products`: `Category`, `Tool`, `SubscriptionPlan`
- `orders`: `Order`, `OrderItem`, `PaymentTransaction`

### ✅ Phase 4 – Django Admin
- Full admin setup with branding ("OneSol AI Hub – Admin")
- Accounts: UserAdmin with Profile inline, Referral admin with "Mark Rewarded" action
- Products: ToolAdmin with logo previews, inline plans, editable flags
- Orders: Color-coded status badges, delivery management actions

### ✅ Phase 5 – Seed Data & Initial Setup
- 8 product categories seeded
- 8 AI tools with subscription plans seeded
- Superuser created: `admin@onesolai.com`

### ✅ Phase 6 – Dynamic Views & API
- Dashboard pulls real DB data (orders, subscriptions, wallet balance)
- Products API endpoint (`/tools/api/`) serves tool data as JSON for frontend carousels
- Currency conversion utility (`core/currency.py`) with 17 African/global currencies
- Currency rates API endpoint (`/api/currencies/`)

### ✅ Phase 7 – Referral System
- Referral code auto-generated on user profile creation
- Signup page shows referrer name when valid `?ref=CODE` URL is used
- Referral code input on signup form (auto-filled from URL)
- Referral records created in DB on successful signup
- Admin shows referral counts on User and Profile lists

### 🔄 Phase 8 – Payment Integration (Next)
- Paystack: initialize payment, callback handler, webhook verification
- Flutterwave: initialize payment, callback handler, webhook verification
- Order creation flow: cart → checkout → payment → delivery
- Automatic access delivery after successful payment confirmation
- Payment keys managed via environment variables

### ✅ Phase 9 – Subscriptions & Order Management
- User-facing order history page
- Subscription expiry tracking
- Renewal reminders (email)
- Refund request flow

### ⬜ Phase 10 – User Profile & Wallet
- Profile settings page (name, email, avatar, currency preference)
- Wallet top-up and withdrawal
- Referral earnings display and withdrawal

### ⬜ Phase 11 – Production Deployment
- PostgreSQL database migration
- Environment variable management (`.env`)
- Gunicorn + Nginx setup
- SSL certificate
- Domain configuration

---

## Key Rules for Developers
1. **Mobile-first always** – design for phone screens first, scale up
2. Do not add functional backend features until the UI design for that component is approved
3. Use `{% static %}` and `{% url %}` tags in all templates
4. Use `accounts.User` for all authentication references
5. All payment keys must come from environment variables, never hardcoded
6. Every new form must include password reveal toggles where applicable
7. All user-facing text must be clear and accessible in the African context

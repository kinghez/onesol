# Vendor API Integration Plan

This document outlines the architecture and implementation steps to integrate the three subscription vendors (Akunding, Shop Bot, and Canboso). This ensures that when a user makes a payment on OneSol, the system automatically purchases the corresponding product from the vendor and delivers the activation code or link to the user.

## User Review Required

> [!IMPORTANT]
> **API Keys & Security**: The API keys will be stored securely in the database. You will need to input them via the Django Admin panel once this is deployed.
> **Synchronous vs Asynchronous**: For MVP, we will process the vendor API calls synchronously right after the payment is verified. This means the user might wait a few extra seconds on the success page while we fetch their code. If this is an issue, we can move it to a background Celery task. Is synchronous processing okay for now?

## Open Questions

> [!WARNING]
> 1. **Canboso Purchase Payload**: The exact JSON body for Canboso's `POST /api/telegram-buyer/purchase` is not fully documented in your message. We will assume a standard payload like `{"product_id": "ID", "quantity": 1}`. We can adjust this during testing if it fails.
> 2. **Shop Bot Webhooks**: The Shop Bot (Source 2) supports webhooks for manual orders. Should we build a webhook listener right now, or just poll the order status if it's manual? (I recommend just building the webhook listener).

## Proposed Changes

We will create a new dedicated Django app called `vendors` to handle all third-party API communication neatly.

---

### Database Models (`vendors/models.py`)

We will create two new models:
#### [NEW] `vendors/models.py`
- `Vendor`: Stores the vendor's name, API Type (Akunding, ShopBot, Canboso), Base URL, and API Key.
- `VendorProduct`: Stores the products pulled from the vendor (e.g., "Netflix 1 Month", `vendor_product_id="12"`).

#### [MODIFY] `products/models.py`
We will add a Foreign Key to `SubscriptionPlan` linking it to a `VendorProduct`. This allows the admin to explicitly map a OneSol plan to the exact vendor product.

---

### Service Layer (`vendors/services.py`)

We will create an API adapter for each vendor so the main application doesn't need to know the specifics of each API.

#### [NEW] `vendors/services.py`
- `BaseVendorService`: Defines standard methods `get_balance()`, `fetch_products()`, and `purchase()`.
- `AkundingService`: Implements logic for `akunding.shop/api` (`/v1/orders` etc.).
- `ShopBotService`: Implements logic for the Shop Bot (`/purchase`, decoding `connection_code` etc.).
- `CanbosoService`: Implements logic for `canboso.com` Telegram buyer API.

---

### Auto-Purchase Hook (`orders/checkout_views.py`)

When an order payment is successfully verified and marked as `paid` (via Paystack, Flutterwave, or Crypto), we will trigger the fulfillment process.

#### [MODIFY] `orders/checkout_views.py`
- Right after `order.status = 'paid'`, call `fulfill_order_via_vendors(order)`.
- This function will:
  1. Loop through all items in the order.
  2. Check if the purchased `SubscriptionPlan` is mapped to a `VendorProduct`.
  3. Instantiate the correct `VendorService` and call `purchase()`.
  4. Save the returned activation codes/links to `Order.access_details`.
  5. Update the `delivery_status` to `sent` and email the user.

---

### Admin Interface (`vendors/admin.py`)

#### [NEW] `vendors/admin.py`
- Build an admin interface to manage Vendors.
- Add an admin action: **"Sync Products from Vendor"**. When clicked, it will hit the vendor's `/products` endpoint and automatically populate the `VendorProduct` table, so you don't have to type them manually!
- Add an admin action: **"Check Balance"** to view your current crypto balance with each vendor.

---

## Verification Plan

### Automated Tests
- N/A - We will rely on manual sandbox testing to ensure real API calls function correctly.

### Manual Verification
1. I will configure the three Vendors in the Django Admin using the keys you provided.
2. I will run the "Sync Products" action to ensure we can successfully fetch products from all 3 APIs.
3. You can map a test product to a vendor product, make a manual/test purchase, and verify that the system correctly hits the vendor API and delivers the code.

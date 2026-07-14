# OneSol AI Hub – SaaS & AI Tools Website
## Development Plan & Project Specification

### 1. Project Overview
**OneSol AI Hub** is a modern, automated web platform designed for selling digital AI and SaaS subscription tools (e.g., AI chat tools, productivity software, and content creation tools). The platform aims to offer these tools at competitive prices while fully automating the sales, payment, and delivery pipeline.

**Core Objectives:**
* Automate the manual sales process.
* Support African users with localized currency payments (via Paystack and Flutterwave).
* Establish a premium, trustworthy brand presence.
* Enable instant order confirmation and lay the groundwork for automated product delivery.

### 2. Technology Stack
* **Frontend:** Pure HTML5, Vanilla CSS3, Vanilla JavaScript. (No React/Vue/Angular).
* **Backend:** Django (Python).
* **Design Pattern:** Mobile-first, sleek, premium, modern aesthetics (glassmorphism, micro-animations, high-quality typography).

### 3. Core System Requirements

#### 3.1 Country & Currency System (Critical)
* **Coverage:** All African countries supported by Paystack and Flutterwave (e.g., NGN, GHS, KES, ZAR, UGX, TZS, RWF, XOF, XAF, ZMW, MWK, MUR).
* **Functionality:** 
  * Automatic IP-based country detection or manual country selection.
  * Single centralized base price (NGN).
  * Real-time dynamic currency conversion displayed site-wide.
  
#### 3.2 Payment Integration
* **Gateways:** Paystack and Flutterwave.
* **Flow:** Users are charged in their local currency. Payment options adapt dynamically based on the selected/detected country.
* **Post-Payment:** Successful transaction triggers an immediate order confirmation.

#### 3.3 Product (AI & SaaS Tools) System
* **Catalog:** Display top and best-selling tools on the front page.
* **Tool Data Structure:**
  * Tool Name
  * Category
  * Description
  * Subscription Duration (monthly, yearly, bundles)
  * Base Price (NGN)
  * Auto-converted Local Price
  * Status Tags (e.g., New / Popular)
* **User Features:** Browse, search, and filter by category.

#### 3.4 Checkout Flow
1. User selects a tool and clicks "Buy Now".
2. Checkout page opens displaying: tool details, local currency price, and available payment options.
3. User completes payment securely.
4. **Post-Checkout Success:** Success confirmation page displaying "Access details will be sent to your email", with the order securely recorded in the backend.

#### 3.5 Automation-Ready Order Structure
* System logs orders automatically upon successful payment.
* Stores order status with placeholders built-in for future automated delivery hooks, email notifications, and admin alerts without requiring a system redesign.

#### 3.6 User Dashboard & Referral System
* **Dashboard:** Tracks active subscriptions, order history, referral earnings, and account settings.
* **Referrals:** 
  * Unique referral link per user.
  * Tracking of successful referrals with fixed rewards.
  * Referral dashboard showing total referrals and accumulated earnings.

### 4. Required Pages
1. Home page
2. Tools listing page
3. Tool detail page
4. Checkout page
5. Category pages
6. Search results page
7. User dashboard
8. Referral page
9. About / Support page

### 5. UI & UX Requirements
* Clean, professional, and premium design.
* **Strictly Mobile-First** layout.
* Fast loading times with smooth micro-interactions.
* Clear, trust-focused pricing displays.
* Integrated customer support / chat box widget.

### 6. Backend & Data Structure (Django)
* All tools must be stored in a single structured dataset.
* Base pricing stored in one primary currency.
* Dynamic currency conversion handled via backend or frontend integration.
* Seamless admin panel for easy updates to tool prices, descriptions, and categories.
* Connection to AI activation providers for provisioning different AI plans based on user purchases.

### 7. Phased Implementation Approach
We will approach the project phase by phase, starting purely with the frontend design:
* **Phase 1:** Global Styles, Design System, and Typography (HTML/CSS).
* **Phase 2:** Core Layouts & Navigation (Header, Footer, Mobile Menu).
* **Phase 3:** Home Page & Product Display (Sleek animations, premium feel).
* **Phase 4:** E-Commerce Flows (Checkout, Pricing localization mockup).
* **Phase 5:** User Dashboard & Referral UI.
* **Phase 6:** Backend Django Integration (Models, APIs, Payment Gateways).

---
*Note: Do not add any functional features until the design phase for that specific component is completed and approved.*

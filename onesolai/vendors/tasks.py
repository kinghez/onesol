# Celery tasks removed — replaced by manual admin triggers via vendors/sync.py
# The sync logic is now in vendors/sync.py and called directly from:
#   1. Admin Analytics Dashboard "Pull Products" button → analytics/views.py::pull_vendor_products
#   2. VendorAdmin action "Sync Products from Vendor API" → vendors/admin.py
#   3. VendorProductAdmin action "Pull Price/Stock Updates" → vendors/admin.py

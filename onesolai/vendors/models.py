from django.db import models

class Vendor(models.Model):
    API_TYPE_CHOICES = [
        ('akunding', 'Akunding'),
        ('shopbot', 'Shop Bot'),
        ('canboso', 'Canboso'),
    ]
    name = models.CharField(max_length=100)
    api_type = models.CharField(max_length=20, choices=API_TYPE_CHOICES)
    base_url = models.URLField(blank=True, help_text="Optional, depending on vendor")
    api_key = models.CharField(max_length=500, blank=True, help_text="Keep this secure")
    webhook_secret = models.CharField(max_length=200, blank=True, help_text="Secret for webhook verification")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_api_type_display()})"


class VendorProduct(models.Model):
    vendor = models.ForeignKey(Vendor, related_name='products', on_delete=models.CASCADE)
    vendor_product_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Vendor price in USD")
    stock = models.CharField(max_length=50, blank=True, help_text="e.g. 45 or unlimited")
    is_manual = models.BooleanField(default=False, help_text="Does this product require manual delivery by the vendor?")
    raw_data = models.JSONField(blank=True, null=True, help_text="Raw JSON product data from vendor API")
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vendor', 'vendor_product_id')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.vendor.name}"

from django.db import models
from vendors.models import Vendor

class VendorBalanceSnapshot(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='balance_snapshots')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.vendor.name} - ${self.balance} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

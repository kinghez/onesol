from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome class e.g. fa-robot")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order in sidebar/filters")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tool(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    vendor_product = models.OneToOneField('vendors.VendorProduct', null=True, blank=True, on_delete=models.SET_NULL, help_text="Link this tool directly to a Vendor Product")
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    category = models.ForeignKey(Category, related_name='tools', on_delete=models.CASCADE)
    
    # Pricing
    sell_price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Manual override for USD sell price")
    is_manual_price = models.BooleanField(default=False, help_text="If True, it will not auto-calculate the sell price based on markups")
    markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Per-tool percentage profit (overrides global)")
    markup_fixed_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Per-tool fixed USD profit (overrides per-tool percentage and global)")

    is_new = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show in Top Tools carousel on home page")
    is_active = models.BooleanField(default=True, help_text="Visible on the site")
    image_url = models.URLField(blank=True, null=True, help_text="Tool logo/icon URL (e.g. svgl)")
    developer = models.CharField(max_length=200, blank=True, help_text="Company/developer name e.g. OpenAI")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    review_count = models.PositiveIntegerField(default=0)
    users_count = models.CharField(max_length=50, blank=True, help_text="Display string e.g. '12,000+'")
    
    # Tab visibility controls
    show_overview_tab = models.BooleanField(default=True, help_text="Show the Overview tab on the product page")
    show_features_tab = models.BooleanField(default=True, help_text="Show the Features tab on the product page")
    show_reviews_tab = models.BooleanField(default=True, help_text="Show the Reviews tab on the product page")
    show_faqs_tab = models.BooleanField(default=True, help_text="Show the FAQs tab on the product page")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-is_popular', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.short_description and self.description:
            self.short_description = self.description[:297] + '...' if len(self.description) > 300 else self.description
        super().save(*args, **kwargs)

    def get_usd_price(self):
        from core.models import SiteSettings
        settings = SiteSettings.objects.first()
        global_markup_percent = float(settings.global_markup_percent) if settings else 20.00
        global_markup_fixed = float(settings.global_markup_fixed_usd) if settings else 0.00
        
        if self.is_manual_price and self.sell_price_usd is not None:
            return round(float(self.sell_price_usd), 2)
        elif self.vendor_product and self.vendor_product.price:
            vendor_price = float(self.vendor_product.price)
            if float(self.markup_fixed_usd) > 0:
                profit = float(self.markup_fixed_usd)
            elif float(self.markup_percent) > 0:
                profit = vendor_price * (float(self.markup_percent) / 100)
            elif global_markup_fixed > 0:
                profit = global_markup_fixed
            else:
                profit = vendor_price * (global_markup_percent / 100)
            return round(vendor_price + profit, 2)
        return round(float(self.sell_price_usd or 0), 2)

    def get_ngn_price(self):
        from core.models import SiteSettings
        from core.services import get_live_usd_rates
        
        usd_price = self.get_usd_price()
        
        # Try fetching live rates first
        live_rates = get_live_usd_rates()
        if live_rates and 'NGN' in live_rates:
            rate = float(live_rates['NGN'])
        else:
            # Fallback to manual settings
            settings = SiteSettings.objects.first()
            rate = settings.usd_to_ngn_rate if settings else 1500.00
            
        return round(usd_price * float(rate), 2)

    def get_stock_status(self):
        if self.vendor_product:
            stock_str = self.vendor_product.stock.lower().strip()
            if stock_str in ['0', 'none', 'out of stock', 'out_of_stock']:
                return "Out of Stock"
            return "In Stock"
        return "In Stock"

    @property
    def is_in_stock(self):
        return self.get_stock_status() == "In Stock"

# (SubscriptionPlan removed)


class ToolScreenshot(models.Model):
    tool = models.ForeignKey(Tool, related_name='screenshots', on_delete=models.CASCADE)
    image_url = models.URLField(help_text="URL to the screenshot image")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Screenshot for {self.tool.name}"


class ToolFeature(models.Model):
    tool = models.ForeignKey(Tool, related_name='features', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, help_text="e.g. Priority access to GPT-4")
    description = models.TextField(blank=True, help_text="Optional longer description")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class ToolFAQ(models.Model):
    tool = models.ForeignKey(Tool, related_name='faqs', on_delete=models.CASCADE)
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.question


class ToolReview(models.Model):
    tool = models.ForeignKey(Tool, related_name='reviews', on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100)
    rating = models.PositiveIntegerField(default=5, help_text="1 to 5 stars")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating} star review by {self.user_name} for {self.tool.name}"

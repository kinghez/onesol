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
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    category = models.ForeignKey(Category, related_name='tools', on_delete=models.CASCADE)
    base_price_ngn = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base monthly price in NGN")
    is_new = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show in Top Tools carousel on home page")
    is_active = models.BooleanField(default=True, help_text="Visible on the site")
    image_url = models.URLField(blank=True, null=True, help_text="Tool logo/icon URL (e.g. svgl)")
    developer = models.CharField(max_length=200, blank=True, help_text="Company/developer name e.g. OpenAI")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    review_count = models.PositiveIntegerField(default=0)
    users_count = models.CharField(max_length=50, blank=True, help_text="Display string e.g. '12,000+'")
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

    def get_monthly_plan(self):
        return self.plans.filter(name__icontains='month').first()


class SubscriptionPlan(models.Model):
    DURATION_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (3 months)'),
        ('biannual', 'Biannual (6 months)'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    tool = models.ForeignKey(Tool, related_name='plans', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="e.g. Monthly, Yearly, Lifetime")
    duration_type = models.CharField(max_length=20, choices=DURATION_CHOICES, default='monthly')
    duration_days = models.IntegerField(default=30)
    price_ngn = models.DecimalField(max_digits=10, decimal_places=2)
    is_best_value = models.BooleanField(default=False, help_text="Highlight as best value plan")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['duration_days']

    def __str__(self):
        return f"{self.tool.name} – {self.name} (NGN {self.price_ngn})"


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

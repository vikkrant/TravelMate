from django.db import models
from django.contrib.auth.models import User

class Trip(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=15, decimal_places=10)
    longitude = models.DecimalField(max_digits=15, decimal_places=10)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.destination} ({self.start_date} - {self.end_date})"

class PackingListItem(models.Model):
    id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='packing_items')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)  # e.g., 'Clothing', 'Electronics', 'Toiletries'
    is_packed = models.BooleanField(default=False)
    is_auto_generated = models.BooleanField(default=False)  # To distinguish between auto-generated and manual items
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.category}) - {'Packed' if self.is_packed else 'Not Packed'}"

    class Meta:
        ordering = ['category', 'name']

class OutfitRecommendation(models.Model):
    id = models.AutoField(primary_key=True)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='outfit_recommendations')
    day = models.DateField()
    weather_condition = models.CharField(max_length=100)  # e.g., 'Sunny', 'Rainy', 'Cold'
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    outfit_description = models.TextField()
    is_customized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Outfit for {self.day} - {self.weather_condition}"

    class Meta:
        ordering = ['day'] 
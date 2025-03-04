from django.db import models
from django.contrib.auth.models import User

class CurrencyRate(models.Model):
    pair = models.CharField(max_length=10)  # e.g., 'USD/EUR'
    rate = models.FloatField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pair

class CurrencyRateHistory(models.Model):
    currency_rate = models.ForeignKey(CurrencyRate, on_delete=models.CASCADE, related_name='history')
    rate = models.FloatField()
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.currency_rate.pair} - {self.rate} at {self.updated_at}"

class CurrencyAlert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pair = models.CharField(max_length=10)
    target_rate = models.FloatField()
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)  # New field to store when the alert was triggered
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert for {self.pair} at {self.target_rate}"
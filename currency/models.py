from django.db import models

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
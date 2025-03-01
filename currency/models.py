from django.db import models

class CurrencyRate(models.Model):
    pair = models.CharField(max_length=10)  # e.g., 'USD/EUR'
    rate = models.FloatField()
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pair
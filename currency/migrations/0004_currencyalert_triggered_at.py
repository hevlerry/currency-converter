# Generated by Django 5.1.6 on 2025-03-04 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0003_currencyalert'),
    ]

    operations = [
        migrations.AddField(
            model_name='currencyalert',
            name='triggered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

# Generated by Django 5.0.7 on 2025-03-01 06:07

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CurrencyRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pair', models.CharField(max_length=10)),
                ('rate', models.FloatField()),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

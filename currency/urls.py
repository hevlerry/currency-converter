from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView,
    LoginView,
    CurrencyRateViewSet,
    sync_currency_rate,
    BulkCurrencyRateView,
    check_currency_pair,
    supported_currencies,
    all_currency_rates_history,
    currency_pair_trend,
    get_min_max_currency_rate,
    get_latest_currency_rates,
    check_currency_rate_status,
    get_daily_summary,  # New endpoint
    get_currency_pair_details, manage_currency_alert,
    trigger_currency_alerts, list_currency_alerts_and_create  # New endpoint
)

# Create a router and register the CurrencyRateViewSet
router = DefaultRouter()
router.register(r'v1/currency/rates', CurrencyRateViewSet, basename='currencyrate')

urlpatterns = [
    path('v1/auth/register/', RegisterView.as_view(), name='register'),
    path('v1/auth/login/', LoginView.as_view(), name='login'),
    path('v1/currency/rates/<int:id>/sync/', sync_currency_rate, name='sync_currency_rate'),
    path('v1/currency/rates/bulk/', BulkCurrencyRateView.as_view(), name='bulk_currency_rate'),
    path('v1/currency/rates/check/', check_currency_pair, name='check_currency_pair'),
    path('v1/currency/rates/supported-currencies/', supported_currencies, name='supported_currencies'),
    path('v1/currency/rates/all-history/', all_currency_rates_history, name='all_currency_rates_history'),
    path('v1/currency/rates/<int:currency_pair_id>/trend/', currency_pair_trend, name='currency_pair_trend'),
    path('v1/currency/rates/<int:currency_pair_id>/min-max/', get_min_max_currency_rate, name='min_max_currency_rate'),
    path('v1/currency/rates/latest/', get_latest_currency_rates, name='latest_currency_rates'),
    path('v1/currency/rates/<int:currency_rate_id>/status/', check_currency_rate_status, name='currency_rate_status'),
    path('v1/currency/rates/daily-summary/', get_daily_summary, name='daily_summary'),
    path('v1/currency/rates/<int:currency_rate_id>/details/', get_currency_pair_details, name='currency_pair_details'),
    path('v1/currency/alerts/', list_currency_alerts_and_create, name='list_currency_alerts_and_create'),
    path('v1/currency/alerts/<int:alert_id>/', manage_currency_alert, name='manage_currency_alert'),  # GET, PUT, DELETE
    path('v1/currency/alerts/trigger/', trigger_currency_alerts, name='trigger_currency_alerts'),
    # POST to trigger alerts
]

# Include the router URLs
urlpatterns += router.urls

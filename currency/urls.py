from django.urls import path
from .views import RegisterView, LoginView, CurrencyRateViewSet, sync_currency_rate, BulkCurrencyRateView, check_currency_pair
from rest_framework.routers import DefaultRouter  # Ensure this import is present

# Create a router and register the CurrencyRateViewSet
router = DefaultRouter()
router.register(r'v1/currency/rates', CurrencyRateViewSet, basename='currencyrate')

urlpatterns = [
    path('v1/auth/register/', RegisterView.as_view(), name='register'),
    path('v1/auth/login/', LoginView.as_view(), name='login'),
    path('v1/currency/rates/<int:id>/sync/', sync_currency_rate, name='sync_currency_rate'),
    path('v1/currency/rates/bulk/', BulkCurrencyRateView.as_view(), name='bulk_currency_rate'),
    path('v1/currency/rates/check/', check_currency_pair, name='check_currency_pair'),  # New check endpoint
]

# Include the router URLs
urlpatterns += router.urls
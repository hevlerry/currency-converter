from django.urls import path
from .views import RegisterView, LoginView, CurrencyRateViewSet, sync_currency_rate
from rest_framework.routers import DefaultRouter

# Create a router and register the CurrencyRateViewSet
router = DefaultRouter()
router.register(r'v1/currency/rates', CurrencyRateViewSet, basename='currencyrate')

urlpatterns = [
    path('v1/auth/register/', RegisterView.as_view(), name='register'),
    path('v1/auth/login/', LoginView.as_view(), name='login'),
    path('v1/currency/rates/<int:id>/sync/', sync_currency_rate, name='sync_currency_rate'),  # New sync endpoint
]

# Include the router URLs
urlpatterns += router.urls
from django.urls import path
from .views import RegisterView, LoginView, CurrencyRateViewSet
from rest_framework.routers import DefaultRouter

# Create a router and register the CurrencyRateViewSet
router = DefaultRouter()
router.register(r'v1/currency/rates', CurrencyRateViewSet, basename='currencyrate')

urlpatterns = [
    path('v1/auth/register/', RegisterView.as_view(), name='register'),
    path('v1/auth/login/', LoginView.as_view(), name='login'),
]

# Include the router URLs
urlpatterns += router.urls
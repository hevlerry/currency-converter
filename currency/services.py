from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CurrencyRate
import requests
from django.conf import settings  # Import settings

def register_user(username, password):
    user = User.objects.create_user(username=username, password=password)
    return user

def login_user(username, password):
    user = authenticate(username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    return None

def create_currency_rate(data):
    currency_rate = CurrencyRate(**data)
    currency_rate.save()
    return currency_rate

def create_bulk_currency_rates(rates_data):
    currency_rates = []
    for data in rates_data:
        currency_rate = create_currency_rate(data)
        currency_rates.append({
            "id": currency_rate.id,  # Include the ID of the created currency rate
            "pair": currency_rate.pair,
            "rate": currency_rate.rate
        })
    return currency_rates

def delete_currency_rates_by_ids(ids):
    deleted_count, _ = CurrencyRate.objects.filter(id__in=ids).delete()
    return deleted_count, None  # Return the count of deleted records

def get_currency_rate_by_id(rate_id):
    return CurrencyRate.objects.get(id=rate_id)

def sync_currency_rate(currency_rate):
    # Example: Assuming the pair is stored in the format 'USD/EUR'
    currency_pair = currency_rate.pair
    base_currency, target_currency = currency_pair.split('/')

    # Fetch the latest exchange rate from an external API
    api_key = settings.CURRENCY_FREAKS_API_KEY  # Use the API key from settings
    api_url = f'https://api.currencyfreaks.com/v2.0/rates/latest?apikey={api_key}&from={base_currency}&to={target_currency}'

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Extract the exchange rate
        exchange_rate = data.get('rates', {}).get(target_currency)
        if exchange_rate is None:
            raise ValueError(f"Exchange rate for {target_currency} not found in response.")

        return exchange_rate

    except requests.exceptions.HTTPError as http_err:
        raise ValueError(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        raise ValueError(f"Request error occurred: {req_err}")

def currency_pair_exists(pair):
    return CurrencyRate.objects.filter(pair=pair).exists()

def get_currency_rate_by_pair(pair):
    try:
        return CurrencyRate.objects.get(pair=pair)
    except CurrencyRate.DoesNotExist:
        return None
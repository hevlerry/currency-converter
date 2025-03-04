from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CurrencyRate, CurrencyRateHistory, CurrencyAlert
import requests
from django.conf import settings
from django.db.models import Min, Max
from django.utils import timezone
from datetime import timedelta

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

def get_supported_currency_pairs_with_ids():
    return CurrencyRate.objects.values('id', 'pair').distinct()

def get_all_currency_rate_history():
    # Retrieve all historical records of currency rates, ordered by updated_at descending
    return CurrencyRateHistory.objects.select_related('currency_rate').order_by('-updated_at')

def get_currency_pair_trend(currency_pair_id):
    # Retrieve historical rates for a specific currency pair, ordered by updated_at descending
    return CurrencyRateHistory.objects.filter(currency_rate_id=currency_pair_id).order_by('-updated_at')


def get_min_max_currency_rate_service(currency_pair_id):
    # Retrieve historical rates for the specified currency pair
    rates = CurrencyRateHistory.objects.filter(currency_rate_id=currency_pair_id)

    if rates.exists():
        min_rate = rates.aggregate(Min('rate'))['rate__min']
        max_rate = rates.aggregate(Max('rate'))['rate__max']

        # Get the currency pair from the CurrencyRate model
        currency_rate = rates.first().currency_rate  # Get the first related CurrencyRate object
        currency_pair = currency_rate.pair if currency_rate else None

        return {
            'pair': currency_pair,
            'min_rate': min_rate,
            'max_rate': max_rate
        }
    return None

def get_latest_currency_rates_service():
    # Retrieve the 10 most recently updated currency rates
    return CurrencyRate.objects.order_by('-last_updated')[:10]

def check_currency_rate_status_service(currency_rate_id):
    # Check if the currency rate exists by ID
    try:
        currency_rate = CurrencyRate.objects.get(id=currency_rate_id)
    except CurrencyRate.DoesNotExist:
        return None

    # Check if the pair has been updated in the last 3 days
    is_active = (timezone.now() - currency_rate.last_updated) <= timedelta(days=3)

    return {
        'pair': currency_rate.pair,
        'active': is_active,
        'last_updated': currency_rate.last_updated
    }


def get_daily_summary_service():
    # Get today's date
    today = timezone.now().date()

    # Get all currency rates
    currency_rates = CurrencyRate.objects.all()
    daily_summaries = []

    for currency_rate in currency_rates:
        # Get the initial rate for today using updated_at
        initial_rate = CurrencyRateHistory.objects.filter(
            currency_rate=currency_rate,
            updated_at__date=today
        ).order_by('updated_at').first()

        # Get the current rate
        current_value = currency_rate.rate

        if initial_rate:
            initial_value = initial_rate.rate
            percentage_change = ((current_value - initial_value) / initial_value) * 100

            daily_summaries.append({
                'pair': currency_rate.pair,
                'initial_rate': initial_value,
                'current_rate': current_value,
                'percentage_change': percentage_change
            })

    return daily_summaries


def get_currency_pair_details_service(currency_rate_id):
    try:
        currency_rate = CurrencyRate.objects.get(id=currency_rate_id)
    except CurrencyRate.DoesNotExist:
        return None

    # Get today's date
    today = timezone.now().date()

    # Get the daily fluctuation using updated_at
    initial_rate = CurrencyRateHistory.objects.filter(
        currency_rate=currency_rate,
        updated_at__date=today
    ).order_by('updated_at').first()

    current_rate = currency_rate.rate

    if initial_rate:
        initial_value = initial_rate.rate
        daily_fluctuation = ((current_rate - initial_value) / initial_value) * 100
    else:
        daily_fluctuation = 0.0  # No fluctuation if no initial rate is found

    # Get the highest and lowest recorded rates
    highest_rate = CurrencyRateHistory.objects.filter(currency_rate=currency_rate).aggregate(Max('rate'))['rate__max']
    lowest_rate = CurrencyRateHistory.objects.filter(currency_rate=currency_rate).aggregate(Min('rate'))['rate__min']

    return {
        'pair': currency_rate.pair,
        'current_rate': current_rate,
        'daily_fluctuation': daily_fluctuation,
        'highest_rate': highest_rate,
        'lowest_rate': lowest_rate
    }

from .models import CurrencyAlert, CurrencyRate
from django.contrib.auth.models import User
from django.utils import timezone

def create_currency_alert_service(user: User, pair: str, target_rate: float):
    # Check if the currency pair exists
    if not CurrencyRate.objects.filter(pair=pair).exists():
        raise ValueError("Currency pair does not exist.")

    alert = CurrencyAlert.objects.create(user=user, pair=pair, target_rate=target_rate)
    return alert

def list_currency_alerts_service(user: User):
    return CurrencyAlert.objects.filter(user=user)

def get_currency_alert_service(alert_id: int, user: User):
    try:
        return CurrencyAlert.objects.get(id=alert_id, user=user)
    except CurrencyAlert.DoesNotExist:
        return None

def update_currency_alert_service(alert_id: int, user: User, pair: str, target_rate: float):
    alert = get_currency_alert_service(alert_id, user)
    if alert:
        alert.pair = pair
        alert.target_rate = target_rate
        alert.save()
        return alert
    return None

def delete_currency_alert_service(alert_id: int, user: User):
    try:
        alert = CurrencyAlert.objects.get(id=alert_id, user=user)
        alert.delete()
        return True
    except CurrencyAlert.DoesNotExist:
        return False

def check_and_trigger_alerts():
    # Get all alerts
    alerts = CurrencyAlert.objects.all()
    for alert in alerts:
        # Get the current rate for the alert's pair
        current_rate = CurrencyRate.objects.filter(pair=alert.pair).first()
        if current_rate and current_rate.rate > alert.target_rate and not alert.triggered:
            alert.triggered = True
            alert.triggered_at = timezone.now()  # Set the time when the alert was triggered
            alert.save()
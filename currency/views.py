from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from .services import (
    register_user,
    login_user,
    create_currency_rate,
    sync_currency_rate as sync_currency_rate_service,
    create_bulk_currency_rates,
    delete_currency_rates_by_ids,
    currency_pair_exists,
    get_currency_rate_by_pair,
    get_supported_currency_pairs_with_ids,
    get_currency_pair_trend,
    get_all_currency_rate_history, get_min_max_currency_rate_service, get_latest_currency_rates_service,
    check_currency_rate_status_service, get_daily_summary_service, get_currency_pair_details_service,
    create_currency_alert_service, list_currency_alerts_service, get_currency_alert_service,
    update_currency_alert_service, delete_currency_alert_service, check_and_trigger_alerts, convert_currency,
    bulk_convert_currency, get_conversion_history
)
from .serializers import (
    UserSerializer,
    LoginSerializer,
    CurrencyRateSerializer,
    BulkCurrencyRateSerializer,
    CurrencyPairCheckSerializer,
    CurrencyPairTrendSerializer,
    CurrencyRateHistorySerializer, MinMaxRateSerializer, LatestCurrencyRateSerializer, CurrencyRateStatusSerializer,
    DailySummarySerializer, CurrencyPairDetailsSerializer, CurrencyAlertCreateSerializer, CurrencyAlertSerializer,
    CurrencyConvertRequestSerializer, CurrencyConversionSerializer, BulkCurrencyConvertRequestSerializer,
    CurrencyConvertByIDRequestSerializer,
)
from django.shortcuts import get_object_or_404
import requests
from .models import CurrencyRate, CurrencyRateHistory
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import CurrencyAlertSerializer, CurrencyAlertCreateSerializer
from .services import (
    create_currency_alert_service,
    list_currency_alerts_service,
    get_currency_alert_service,
    update_currency_alert_service,
)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User  registered successfully',
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        tokens = login_user(username, password)
        if tokens:
            return Response(tokens, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from django.shortcuts import get_object_or_404
from .models import CurrencyRate, CurrencyRateHistory
from .serializers import CurrencyRateSerializer
from rest_framework.permissions import IsAuthenticated

class CurrencyRateViewSet(viewsets.ModelViewSet):
    queryset = CurrencyRate.objects.all()
    serializer_class = CurrencyRateSerializer
    permission_classes = [IsAuthenticated]

    def is_valid_currency_pair(self, pair: str) -> bool:
        from_currency, to_currency = pair.split('/')

        valid_currencies = [
            'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'NZD',
            'SEK', 'KRW', 'SGD', 'NOK', 'MXN', 'INR', 'RUB', 'ZAR', 'TRY', 'BRL',
            'TWD', 'DKK', 'PLN', 'THB', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP',
            'AED', 'COP', 'SAR', 'MYR', 'RON'
        ]

        if from_currency == to_currency:
            return False

        if from_currency not in valid_currencies or to_currency not in valid_currencies:
            return False

        return True

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            pair = serializer.validated_data['pair']

            if not self.is_valid_currency_pair(pair):
                return Response({'error': 'Invalid currency pair. The currencies must be different and valid.'}, status=status.HTTP_400_BAD_REQUEST)

            if CurrencyRate.objects.filter(pair=pair).exists():
                return Response({'error': 'Currency pair already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            currency_rate = CurrencyRate.objects.create(**serializer.validated_data)
            return Response(CurrencyRateSerializer(currency_rate).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        raise MethodNotAllowed("PUT method is not allowed on this endpoint.")

    def destroy(self, request, pk=None):
        raise MethodNotAllowed("DELETE method is not allowed on this endpoint.")

    @action(detail=True, methods=['put', 'delete'], url_path='manual')
    def manual_update(self, request, pk=None):
        currency_rate = get_object_or_404(self.queryset, pk=pk)

        if request.method == 'PUT':
            new_rate = request.data.get('rate')
            if new_rate is not None:
                currency_rate.rate = new_rate
                currency_rate.save()

                CurrencyRateHistory.objects.create(
                    currency_rate=currency_rate,
                    rate=new_rate
                )

                return Response({
                    'message': 'Currency rate updated successfully',
                    'rate': currency_rate.rate
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Rate not provided'}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            currency_rate.delete()
            return Response({'message': 'Currency rate deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_currency_pair(request):
    pair = request.data.get('pair')
    if not pair:
        return Response({'error': 'Currency pair not provided.'}, status=status.HTTP_400_BAD_REQUEST)

    from_currency, to_currency = pair.split('/')
    if from_currency == to_currency:
        return Response({'error': 'Invalid currency pair. The currencies must be different.'}, status=status.HTTP_400_BAD_REQUEST)

    currency_rate = get_currency_rate_by_pair(pair)
    response_data = {
        'exists': False
    }

    if currency_rate:
        response_data['exists'] = True
        response_data['id'] = currency_rate.id
        response_data['pair'] = currency_rate.pair
        response_data['rate'] = currency_rate.rate

    serializer = CurrencyPairCheckSerializer(data=response_data)
    serializer.is_valid(raise_exception=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_currency_rate(request, id):
    currency_rate = get_object_or_404(CurrencyRate, id=id)

    try:
        exchange_rate = sync_currency_rate_service(currency_rate)

        if exchange_rate is not None:
            currency_rate.rate = exchange_rate
            currency_rate.save()

            CurrencyRateHistory.objects.create(
                currency_rate=currency_rate,
                rate=exchange_rate
            )

            return Response({
                'message': 'Currency rate synced successfully',
                'rate': exchange_rate,
                'pair': currency_rate.pair
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Exchange rate not found'}, status=status.HTTP_404_NOT_FOUND)

    except requests.exceptions.RequestException as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkCurrencyRateView(APIView):
    def post(self, request):
        serializer = BulkCurrencyRateSerializer(data=request.data)
        if serializer.is_valid():
            rates = serializer.validated_data['rates']
            created_rates = []
            errors = []

            seen_pairs = set()

            for rate in rates:
                pair = rate['pair']
                if pair in seen_pairs:
                    errors.append({'error': f'Duplicate currency pair: {pair}'})
                    continue
                seen_pairs.add(pair)

                from_currency, to_currency = pair.split('/')
                if from_currency == to_currency:
                    errors.append({'error': f'Invalid currency pair: {pair}. The currencies must be different.'})
                    continue

                valid_currencies = [
                    'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'HKD', 'NZD',
                    'SEK', 'KRW', 'SGD', 'NOK', 'MXN', 'INR', 'RUB', 'ZAR', 'TRY', 'BRL',
                    'TWD', 'DKK', 'PLN', 'THB', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP', 'PHP',
                    'AED', 'COP', 'SAR', 'MYR', 'RON'
                ]
                if from_currency not in valid_currencies or to_currency not in valid_currencies:
                    errors.append({'error': f'Invalid currency pair: {pair}. One or both currencies are not valid.'})
                    continue

                if CurrencyRate.objects.filter(pair=pair).exists():
                    errors.append({'error': f'Currency pair already exists: {pair}'})
                    continue

                created_rate = create_currency_rate(rate)
                created_rates.append(created_rate)

            response_data = {
                "status": "success",
                "message": "Currency rates added successfully.",
                "data": {
                    "created_rates": CurrencyRateSerializer(created_rates, many=True).data
                }
            }

            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count = delete_currency_rates_by_ids(ids)
        return Response({
            "status": "success",
            "deleted_count": deleted_count,
            "message": "Currency rates deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def supported_currencies(request):
    currency_pairs = get_supported_currency_pairs_with_ids()

    response_data = [{'id': currency['id'], 'pair': currency['pair']} for currency in currency_pairs]

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
def all_currency_rates_history(request):
    history_records = get_all_currency_rate_history().order_by('-updated_at')

    serializer = CurrencyRateHistorySerializer(history_records, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def currency_pair_trend(request, currency_pair_id):
    trend_records = get_currency_pair_trend(currency_pair_id).order_by('-updated_at')
    serializer = CurrencyPairTrendSerializer(trend_records, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_min_max_currency_rate(request, currency_pair_id):
    min_max_rates = get_min_max_currency_rate_service(currency_pair_id)

    if min_max_rates:
        serializer = MinMaxRateSerializer(data=min_max_rates)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found or no historical data available.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_latest_currency_rates(request):
    latest_rates = get_latest_currency_rates_service()

    serializer = LatestCurrencyRateSerializer(latest_rates, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def check_currency_rate_status(request, currency_rate_id):
    status_data = check_currency_rate_status_service(currency_rate_id)

    if status_data:
        serializer = CurrencyRateStatusSerializer(data=status_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_daily_summary(request):
    summary_data = get_daily_summary_service()

    if summary_data:
        serializer = DailySummarySerializer(summary_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'No data available for today.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_currency_pair_details(request, currency_rate_id):
    details_data = get_currency_pair_details_service(currency_rate_id)

    if details_data:
        serializer = CurrencyPairDetailsSerializer(details_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def list_currency_alerts_and_create(request):
    if request.method == 'GET':
        alerts = list_currency_alerts_service(request.user)
        serializer = CurrencyAlertSerializer(alerts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = CurrencyAlertCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                alert = create_currency_alert_service(request.user, serializer.validated_data['pair'], serializer.validated_data['target_rate'])
                return Response(CurrencyAlertSerializer(alert).data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_currency_alert(request, alert_id):
    if request.method == 'GET':
        alert = get_currency_alert_service(alert_id, request.user)
        if alert:
            serializer = CurrencyAlertSerializer(alert)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND)

    elif request.method == 'PUT':
        alert = get_currency_alert_service(alert_id, request.user)
        if alert:
            serializer = CurrencyAlertCreateSerializer(alert, data=request.data)
            if serializer.is_valid():
                updated_alert = update_currency_alert_service(
                    alert_id,
                    request.user,
                    serializer.validated_data['pair'],
                    serializer.validated_data['target_rate']
                )
                return Response(CurrencyAlertSerializer(updated_alert).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND)

    elif request.method == 'DELETE':
        if delete_currency_alert_service(alert_id, request.user):
            return Response({'message': 'Alert successfully deleted.'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Alert not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_currency_alerts(request):
    try:
        check_and_trigger_alerts()
        return Response({'message': 'Alerts checked and triggered if necessary.'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_currency_view(request):
    serializer = CurrencyConvertRequestSerializer(data=request.data)

    if serializer.is_valid():
        amount = serializer.validated_data['amount']
        from_currency = serializer.validated_data['from_currency']
        to_currency = serializer.validated_data['to_currency']

        conversion_record = convert_currency(amount, from_currency, to_currency, request.user)
        if conversion_record:
            return Response(CurrencyConversionSerializer(conversion_record).data, status=status.HTTP_200_OK)
        return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_currency_by_id_view(request, currency_id):
    serializer = CurrencyConvertByIDRequestSerializer(data=request.data)

    if serializer.is_valid():
        amount = serializer.validated_data['amount']

        currency_pair = CurrencyRate.objects.filter(id=currency_id).first()
        if not currency_pair:
            return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)

        from_currency, to_currency = currency_pair.pair.split('/')

        conversion_record = convert_currency(amount, from_currency, to_currency, request.user)
        if conversion_record:
            return Response(CurrencyConversionSerializer(conversion_record).data, status=status.HTTP_200_OK)
        return Response({'error': 'Conversion failed.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_convert_currency_view(request):
    print("Incoming request data:", request.data)
    serializer = BulkCurrencyConvertRequestSerializer(data=request.data)

    if serializer.is_valid():
        conversions = serializer.validated_data['conversions']
        results = []
        errors = []

        results, errors = bulk_convert_currency(conversions, request.user)

        response_data = {
            'results': [CurrencyConversionSerializer(record).data for record in results],
            'errors': errors
        }

        return Response(response_data, status=status.HTTP_200_OK)

    print("Serializer errors:", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversion_history_view(request):
    conversions = get_conversion_history(request.user)
    serializer = CurrencyConversionSerializer(conversions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
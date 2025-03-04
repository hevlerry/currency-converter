from rest_framework import generics, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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
    check_currency_rate_status_service, get_daily_summary_service, get_currency_pair_details_service
)
from .serializers import (
    UserSerializer,
    LoginSerializer,
    CurrencyRateSerializer,
    BulkCurrencyRateSerializer,
    CurrencyPairCheckSerializer,
    CurrencyPairTrendSerializer,
    CurrencyRateHistorySerializer, MinMaxRateSerializer, LatestCurrencyRateSerializer, CurrencyRateStatusSerializer,
    DailySummarySerializer, CurrencyPairDetailsSerializer,
)
from django.shortcuts import get_object_or_404
import requests
from .models import CurrencyRate, CurrencyRateHistory
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

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

class CurrencyRateViewSet(viewsets.ModelViewSet):
    queryset = CurrencyRate.objects.all()
    serializer_class = CurrencyRateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check if the currency pair already exists
            if currency_pair_exists(serializer.validated_data['pair']):
                return Response({'error': 'Currency pair already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            currency_rate = create_currency_rate(serializer.validated_data)
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
                # Update the currency rate
                currency_rate.rate = new_rate
                currency_rate.save()

                # Create a historical record for the manual update
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
        # Call the service to get the latest exchange rate
        exchange_rate = sync_currency_rate_service(currency_rate)

        if exchange_rate is not None:
            # Update the currency rate
            currency_rate.rate = exchange_rate
            currency_rate.save()

            # Create a historical record
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
            created_rates = create_bulk_currency_rates(serializer.validated_data['rates'])
            return Response({
                "status": "success",
                "data": {
                    "rates": created_rates
                },
                "message": "Currency rates added successfully."
            }, status=status.HTTP_201_CREATED)
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
    # Use the service function to get the supported currency pairs with IDs
    currency_pairs = get_supported_currency_pairs_with_ids()

    # Prepare the response data
    response_data = [{'id': currency['id'], 'pair': currency['pair']} for currency in currency_pairs]

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
def all_currency_rates_history(request):
    # Use the service function to get all historical currency rates
    history_records = get_all_currency_rate_history().order_by('-updated_at')  # Sort by updated_at descending

    # Serialize the response data
    serializer = CurrencyRateHistorySerializer(history_records, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def currency_pair_trend(request, currency_pair_id):
    # Use the service function to get historical rates for a specific currency pair
    trend_records = get_currency_pair_trend(currency_pair_id).order_by('-updated_at')  # Sort by updated_at descending

    # Serialize the response data
    serializer = CurrencyPairTrendSerializer(trend_records, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_min_max_currency_rate(request, currency_pair_id):
    # Use the service function to get the min and max rates
    min_max_rates = get_min_max_currency_rate_service(currency_pair_id)

    if min_max_rates:
        # Serialize the response data
        serializer = MinMaxRateSerializer(data=min_max_rates)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found or no historical data available.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_latest_currency_rates(request):
    # Use the service function to get the latest currency rates
    latest_rates = get_latest_currency_rates_service()

    # Serialize the response data
    serializer = LatestCurrencyRateSerializer(latest_rates, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def check_currency_rate_status(request, currency_rate_id):
    # Use the service function to check the status of the currency rate by ID
    status_data = check_currency_rate_status_service(currency_rate_id)

    if status_data:
        # Serialize the response data
        serializer = CurrencyRateStatusSerializer(data=status_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_daily_summary(request):
    summary_data = get_daily_summary_service()

    if summary_data:
        return Response(summary_data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'No data available for today.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_currency_pair_details(request, currency_rate_id):
    details_data = get_currency_pair_details_service(currency_rate_id)

    if details_data:
        serializer = CurrencyPairDetailsSerializer(data=details_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Currency pair not found.'}, status=status.HTTP_404_NOT_FOUND)
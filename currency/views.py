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
    get_supported_currency_pairs_with_ids
)
from .serializers import (
    UserSerializer,
    LoginSerializer,
    CurrencyRateSerializer,
    BulkCurrencyRateSerializer,
    CurrencyPairCheckSerializer,
    CurrencyPairSerializer
)
from django.shortcuts import get_object_or_404
import requests
from .models import CurrencyRate
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

    def retrieve(self, request, pk=None):
        currency_rate = get_object_or_404(self.queryset, pk=pk)
        serializer = self.get_serializer(currency_rate)
        return Response(serializer.data)

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
        # Raise MethodNotAllowed for PUT requests
        raise MethodNotAllowed("PUT method is not allowed on this endpoint.")

    def destroy(self, request, pk=None):
        # Raise MethodNotAllowed for DELETE requests
        raise MethodNotAllowed("DELETE method is not allowed on this endpoint.")

    # Manual update endpoint
    @action(detail=True, methods=['put', 'delete'], url_path='manual')
    def manual_update(self, request, pk=None):
        currency_rate = get_object_or_404(self.queryset, pk=pk)

        if request.method == 'PUT':
            new_rate = request.data.get('rate')
            if new_rate is not None:
                currency_rate.rate = new_rate
                currency_rate.save()
                return Response({'message': 'Currency rate updated successfully', 'rate': currency_rate.rate},
                                status=status.HTTP_200_OK)
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

    # Use the serializer to validate and serialize the response
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
            return Response({
                'message': 'Currency rate synced successfully',
                'rate': exchange_rate,
                'pair': currency_rate.pair
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Exchange rate not found'}, status=status.HTTP_404_NOT_FOUND)

    except requests.exceptions.RequestException as e:
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
from rest_framework import generics, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed
from .services import register_user, login_user
from .serializers import UserSerializer, LoginSerializer, CurrencyRateSerializer
from .models import CurrencyRate
from django.shortcuts import get_object_or_404
import requests


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
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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


# New sync endpoint for currency rates
@api_view(['POST'])
def sync_currency_rate(request, id):
    # Retrieve the currency rate object by ID
    currency_rate = get_object_or_404(CurrencyRate, id=id)

    # Example: Assuming the pair is stored in the format 'USD/EUR'
    currency_pair = currency_rate.pair
    base_currency, target_currency = currency_pair.split('/')

    # Fetch the latest exchange rate from an external API
    api_url = f'https://api.currencyfreaks.com/v2.0/rates/latest?apikey=cb1d7f7c66c445719ca2597904b347bf&from={base_currency}&to={target_currency}'

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Extract the exchange rate
        exchange_rate = data.get('rates', {}).get(target_currency)

        if exchange_rate is not None:
            # Update the currency rate in the database
            currency_rate.rate = exchange_rate
            currency_rate.save()
            return Response({'message': 'Currency rate synced successfully', 'rate': exchange_rate},
                            status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Exchange rate not found'}, status=status.HTTP_404_NOT_FOUND)

    except requests.exceptions.RequestException as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
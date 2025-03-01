from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated  # Import IsAuthenticated
from .services import register_user, login_user
from .serializers import UserSerializer, LoginSerializer, CurrencyRateSerializer
from .models import CurrencyRate
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer

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
    permission_classes = [IsAuthenticated]  # Require authentication for all actions

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
        currency_rate = self.get_object()
        serializer = self.get_serializer(currency_rate, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        currency_rate = self.get_object()
        currency_rate.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Manual update endpoint
    @action(detail=True, methods=['put', 'delete'], url_path='manual')
    def manual_update(self, request, pk=None):
        currency_rate = get_object_or_404(self.queryset, pk=pk)

        if request.method == 'PUT':
            new_rate = request.data.get('rate')
            if new_rate is not None:
                currency_rate.rate = new_rate
                currency_rate.save()
                return Response({'message': 'Currency rate updated successfully', 'rate': currency_rate.rate}, status=status.HTTP_200_OK)
            return Response({'error': 'Rate not provided'}, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'DELETE':
            currency_rate.delete()
            return Response({'message': 'Currency rate deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
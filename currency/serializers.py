from .models import CurrencyRate
from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {
            'password': {'write_only': True}  # Ensure password is write-only
        }

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])  # Hash the password
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = '__all__'

class BulkCurrencyRateSerializer(serializers.Serializer):
    rates = CurrencyRateSerializer(many=True)

    def create(self, validated_data):
        rates_data = validated_data.get('rates')
        return [create_currency_rate(rate_data) for rate_data in rates_data]

class CurrencyPairCheckSerializer(serializers.ModelSerializer):
    exists = serializers.BooleanField()
    id = serializers.IntegerField(required=False)
    pair = serializers.CharField(required=False)
    rate = serializers.FloatField(required=False)

    class Meta:
        model = CurrencyRate
        fields = ['exists', 'id', 'pair', 'rate']
from .models import CurrencyRate, CurrencyRateHistory, CurrencyAlert
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

class CurrencyRateHistorySerializer(serializers.ModelSerializer):
    currency_pair = serializers.CharField(source='currency_rate.pair')

    class Meta:
        model = CurrencyRateHistory
        fields = ['currency_pair', 'rate', 'updated_at']

class CurrencyPairTrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRateHistory
        fields = ['rate', 'updated_at']

class MinMaxRateSerializer(serializers.Serializer):
    pair = serializers.CharField()
    min_rate = serializers.FloatField()
    max_rate = serializers.FloatField()

class LatestCurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ['id', 'pair', 'rate', 'last_updated']

class CurrencyRateStatusSerializer(serializers.Serializer):
    pair = serializers.CharField()
    active = serializers.BooleanField()
    last_updated = serializers.DateTimeField()

class DailySummarySerializer(serializers.Serializer):
    pair = serializers.CharField()
    initial_rate = serializers.FloatField()
    current_rate = serializers.FloatField()
    percentage_change = serializers.FloatField()

class CurrencyPairDetailsSerializer(serializers.Serializer):
    pair = serializers.CharField()
    current_rate = serializers.FloatField()
    daily_fluctuation = serializers.FloatField()
    highest_rate = serializers.FloatField()
    lowest_rate = serializers.FloatField()

class CurrencyAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyAlert
        fields = ['id', 'pair', 'target_rate', 'triggered', 'triggered_at', 'created_at']

class CurrencyAlertCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyAlert
        fields = ['pair', 'target_rate']
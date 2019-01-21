from rest_framework import serializers
from django.contrib.auth.models import User

from .models import IndyWallet, VcxConnection


class VcxConnectionSerializer(serializers.Serializer):
    wallet_name = serializers.CharField(max_length=30)
    partner_name = serializers.CharField(max_length=30)
    invitation = serializers.CharField()
    status = serializers.CharField()

    def create(self, validated_data):
        # TODO create a Connection with an invitation to "partner_name"
        return VcxConnection.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # TODO update status:
        # - accept connection if it is an invitation
        # - poll for updated status if "Sent"
        instance.save()
        return instance


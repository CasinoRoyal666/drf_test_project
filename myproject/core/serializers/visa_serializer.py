from rest_framework import serializers
from ..models import VisaOrder, Passport, VisaStorage, OrderApproval

class VisaOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaOrder
        fields = ['id', 'passport_number', 'status', 'created_at']

    def validate_passport_number(self, value):
        if not Passport.objects.filter(passport_number = value).exists():
            raise serializers.ValidationError("Passport not found!")
        return value

class VisaStorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaStorage
        fields = ['id', 'total_visas', 'remaining_visas']

class OrderApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderApproval
        fields = ['id', 'order', 'staff_member', 'approved_at']

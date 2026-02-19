from rest_framework import serializers
from ..models import Passport

class PassportSerializerV1(serializers.ModelSerializer):
    class Meta:
        model = Passport
        fields = ['id', 'full_name', 'address']

class PassportSerializerV2(serializers.ModelSerializer):
    # Non-model field

    checker_role = serializers.CharField(write_only=True, required=False)
    
    # Field whose output will change
    sensitive_info = serializers.SerializerMethodField()

    class Meta:
        model = Passport
        fields = ['id', 'full_name', 'address', 'checker_role', 'sensitive_info']

    def get_sensitive_info(self, obj):
        request = self.context.get('request')
        
        role = ''
        if request and hasattr(request, 'data'):
            role = request.data.get('checker_role')
        
        if not role and request:
             role = request.query_params.get('checker_role')

        if role == 'customs':
            return f"FULL ACCESS: {obj.passport_number}"
        elif role == 'passport_office':
            return f"INTERNAL DATA: {obj.passport_number} (verified)"
        else:
            return "ACCESS DENIED: ******"

    def create(self, validated_data):
        validated_data.pop('checker_role', None)
        return super().create(validated_data)
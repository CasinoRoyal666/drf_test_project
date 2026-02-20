from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Passport
from ..serializers import PassportSerializerV1, PassportSerializerV2

class PassportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Passport.objects.filter(owner=self.request.user)
    
    def get_serializer_class(self):
        if self.request.version == '2':
            return PassportSerializerV2
        return PassportSerializerV1
    
    def perform_create(self, serializer):
        if Passport.objects.filter(owner=self.request.user).exists():
            raise serializers.ValidationError("You already have registered passport")
        serializer.save(owner=self.request.user)
        
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Passport, VisaStorage
from ..serializers import PassportSerializerV2, VisaStorageSerializer

class StaffPassportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Passport.objects.all()
    serializer_class = PassportSerializerV2
    permission_classes = [IsAuthenticated, IsAdminUser]

class StaffVisaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        inventory = VisaStorage.objects.first()
        serializer = VisaStorageSerializer(inventory)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def initialize(self, request):
        inventory, created = VisaStorage.objects.get_or_create(id=1)
        total = request.data.get('total_visas', 50)
        inventory.total_visas = total
        inventory.remaining_visas = total
        inventory.save()
        serializer = VisaStorageSerializer(inventory)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from ..models import Passport
from ..serializers import PassportSerializerV2

class StaffPassportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Passport.objects.all()
    serializer_class = PassportSerializerV2
    permission_classes = [IsAuthenticated, IsAdminUser]
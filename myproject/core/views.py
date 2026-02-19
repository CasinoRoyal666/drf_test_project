from rest_framework import viewsets
from .models import UserProfile, Passport
from .serializers import PassportSerializerV1, PassportSerializerV2, UserProfileSerializer

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

class PassportViewSet(viewsets.ModelViewSet):
    queryset = Passport.objects.all()

    def get_serializer_class(self):
        if self.request.version == '2':
            return PassportSerializerV2
        return PassportSerializerV1
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import UserProfileViewSet, PassportViewSet

router = DefaultRouter()
router.register(r'users', UserProfileViewSet)
router.register(r'passports', PassportViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from core.views.passport_views import PassportViewSet
from core.views.auth_views import RegisterView, LogoutView
from core.views.staff_views import StaffPassportViewSet, StaffVisaViewSet
from core.views.visa_views import VisaOrderViewSetV1, VisaOrderViewSetV2

router = DefaultRouter()
router.register(r'passports', PassportViewSet, basename='passport')
router.register(r'staff/passports', StaffPassportViewSet, basename='staff-passport')
router.register(r'v1/orders', VisaOrderViewSetV1, basename='v1-visa-order')
router.register(r'v2/orders', VisaOrderViewSetV2, basename='v2-visa-order')
router.register(r'staff/visa', StaffVisaViewSet, basename='staff-visa')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # auth
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
]
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from core.models import Passport
from core.serializers import PassportSerializerV2
from django.test import RequestFactory
from rest_framework.request import Request 


@pytest.fixture
def api_client():
    #anon
    return APIClient()

@pytest.fixture
def user(db):
    #user
    return User.objects.create_user(username="testuser", email="test@test.com", password="password123")

@pytest.fixture
def admin_user(db):
    #admin
    return User.objects.create_superuser(username="admin", email="admin@test.com", password="password123")

@pytest.fixture
def user_client(api_client, user):
    #client jwt authorized as user
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client

@pytest.fixture
def admin_client(api_client, admin_user):
    #client jwt authorized as admin
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


#REGISTER & JWT TESTS
@pytest.mark.django_db
class TestAuth:
    def test_register_success(self, api_client):
        data = {
            "username": "newuser",
            "email": "new@test.com",
            "password": "password123",
            "password_confirm": "password123"
        }
        res = api_client.post('/api/auth/register/', data)
        assert res.status_code == 201
        assert 'access' in res.data
        assert 'refresh' in res.data

    def test_register_password_mismatch(self, api_client):
        data = {
            "username": "newuser",
            "password": "password123",
            "password_confirm": "wrongpassword"
        }
        res = api_client.post('/api/auth/register/', data)
        assert res.status_code == 400
        assert "password_confirm" in res.data

    def test_login_success(self, api_client, user):
        res = api_client.post('/api/auth/login/', {"username": "testuser", "password": "password123"})
        assert res.status_code == 200
        assert 'access' in res.data

    def test_logout_success(self, user_client, user):
        refresh = str(RefreshToken.for_user(user))
        res = user_client.post('/api/auth/logout/', {"refresh": refresh})
        assert res.status_code == 200

    def test_logout_no_refresh_token(self, user_client):
        res = user_client.post('/api/auth/logout/', {})
        assert res.status_code == 400

    def test_logout_invalid_token(self, user_client):
        res = user_client.post('/api/auth/logout/', {"refresh": "fake_token"})
        assert res.status_code == 400


#PAASPORTS TESTS (USER)
@pytest.mark.django_db
class TestPassports:
    def test_create_passport_success(self, user_client):
        data = {"full_name": "Ivan Ivanov", "passport_number": "1234 567890", "address": "Moscow"}
        res = user_client.post('/api/passports/', data)
        assert res.status_code == 201
        assert Passport.objects.count() == 1

    def test_create_passport_duplicate_fails(self, user_client, user):
        Passport.objects.create(owner=user, full_name="Ivan", passport_number="123", address="A")
        
        data = {"full_name": "Petr", "passport_number": "321", "address": "B"}
        res = user_client.post('/api/passports/', data)
        assert res.status_code == 400
        assert "already have registered" in str(res.data)

    def test_get_passport_list_v1(self, user_client, user):
        Passport.objects.create(owner=user, full_name="Ivan", passport_number="123", address="A")
        res = user_client.get('/api/passports/')
        assert res.status_code == 200
        # V1 has no 'sensitive_info' field
        assert 'sensitive_info' not in res.data


#V2 TESTS
@pytest.mark.django_db
class TestPassportSerializerV2:
    def test_sensitive_info_logic(self, user):
        passport = Passport.objects.create(owner=user, full_name="Ivan", passport_number="SECRET_123", address="A")
        factory = RequestFactory()
    
        # role = customs
        raw_req = factory.get('/?checker_role=customs')
        # DRF Request to get .query_params
        req = Request(raw_req) 
        serializer = PassportSerializerV2(passport, context={'request': req})
        assert "FULL ACCESS: SECRET_123" == serializer.data['sensitive_info']

        raw_req = factory.post('/', data={'checker_role': 'passport_office'})
        req = Request(raw_req)
        req._full_data = {'checker_role': 'passport_office'} 
        serializer = PassportSerializerV2(passport, context={'request': req})
        assert "INTERNAL DATA: SECRET_123 (verified)" == serializer.data['sensitive_info']

        raw_req = factory.get('/')
        req = Request(raw_req)
        serializer = PassportSerializerV2(passport, context={'request': req})
        assert "ACCESS DENIED: ******" == serializer.data['sensitive_info']

@pytest.mark.django_db
class TestStaffPassports:
    def test_admin_can_access_all_passports(self, admin_client, user, admin_user):
        Passport.objects.create(owner=user, full_name="Ivan", passport_number="123", address="A")
        res = admin_client.get('/api/staff/passports/')
        
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_normal_user_cannot_access_staff_endpoints(self, user_client):
        res = user_client.get('/api/staff/passports/')
        assert res.status_code == 403
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from core.models import Passport
from core.serializers import PassportSerializerV2
from django.test import RequestFactory
from rest_framework.request import Request 

from core.models import Passport, VisaOrder, VisaStorage, OrderApproval

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

@pytest.fixture
def staff_user(db):
    #user with 'staff' status
    return User.objects.create_user(
        username="staff",
        email="staff@test.com",
        password="password123",
        is_staff=True
    )

@pytest.fixture
def staff_client(api_client, staff_user):
    #authorized client with 'staff' status
    refresh=RefreshToken.for_user(staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client

@pytest.fixture
def passport_with_owner(db, user):
    #passport linked to the user
    return Passport.objects.create(
        owner=user,
        full_name="Test User",
        passport_number="1234 567890",
        address="Test Address"
    )

@pytest.fixture
def visa_storage(db):
    #initialized visa storage
    return VisaStorage.objects.create(
        total_visas=50,
        remaining_visas=50
    )

@pytest.fixture
def visa_order(db, user, passport_with_owner):
    #order wiz status 'pending'
    return VisaOrder.objects.create(
        user=user,
        passport_number="1234 567890",
        status=VisaOrder.Status.PENDING
    )

@pytest.fixture
def visa_order_for_staff(db, staff_user, passport_with_owner):
    return VisaOrder.objects.create(
        user=staff_user,
        passport_number="1234 567890",
        status=VisaOrder.Status.PENDING
    )

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

@pytest.mark.django_db
class TestVisaOrderCreation:
    #Visa order creation tests
    def test_create_order_success(self, user_client, passport_with_owner):
        #succesful order creation with corrrect passport_number
        data = {"passport_number": "1234 567890"}
        res = user_client.post('/api/v2/orders/', data)
        
        assert res.status_code == 201
        assert res.data['passport_number'] == "1234 567890"
        assert res.data['status'] == 'pending'
        assert VisaOrder.objects.count() == 1
        assert VisaOrder.objects.first().user.username == "testuser"
    
    def test_create_order_invalid_passport(self, user_client):
        #Error in order creation wiz not existed passport number
        data = {"passport_number": "NONEXISTENT_PASSPORT"}
        res = user_client.post('/api/v2/orders/', data)
        
        assert res.status_code == 400
        assert "Passport not found" in str(res.data)
        assert VisaOrder.objects.count() == 0
    
    def test_create_order_unauthorized(self, api_client, passport_with_owner):
        #Unauthorized user can't create an order
        data = {"passport_number": "1234 567890"}
        res = api_client.post('/api/v2/orders/', data)
        
        assert res.status_code == 401

# @pytest.mark.django_db
# class TestVisaApprovalV1:
#     #Visa approval tests (v1 variand - logic without any checks)
    
#     def test_approve_v1_success(self, user_client, visa_storage, visa_order):
#         #succesful approve - reduces the amount of visas without checks
#         res = user_client.post(f'/api/v1/orders/{visa_order.id}/approve/', {})
        
#         assert res.status_code == 200
#         assert res.data['status'] == 'approved'
#         assert res.data['remaining_visas'] == 49
        
#         # db check
#         visa_storage.refresh_from_db()
#         assert visa_storage.remaining_visas == 49
        
#         visa_order.refresh_from_db()
#         assert visa_order.status == 'approved'
        
#         assert OrderApproval.objects.count() == 1
    
#     def test_approve_v1_can_go_negative(self, user_client, passport_with_owner):
#         #Approval (V1) allows the quantity to go into the - (race condition)
#         # 0 visas
#         visa_storage = VisaStorage.objects.create(
#             total_visas=0,
#             remaining_visas=0
#         )
        
#         visa_order = VisaOrder.objects.create(
#             user=User.objects.get(username="testuser"),
#             passport_number="1234 567890",
#             status=VisaOrder.Status.PENDING
#         )
        
#         res = user_client.post(f'/api/v1/orders/{visa_order.id}/approve/', {})
        
#         assert res.status_code == 200
#         assert res.data['remaining_visas'] == -1
        
#         visa_storage.refresh_from_db()
#         assert visa_storage.remaining_visas == -1

# @pytest.mark.django_db
# class TestVisaApprovalV2:
#     #Visa approval tests (v2 variand - correct logic with checks)
    
#     def test_approve_v2_success(self, user_client, visa_storage, visa_order):
#         #V2 approval successful with correct quantity check
#         res = user_client.post(f'/api/v2/orders/{visa_order.id}/approve/', {})
        
#         assert res.status_code == 200
#         assert res.data['status'] == 'approved'
#         assert res.data['remaining_visas'] == 49
#         assert res.data['low_visas'] == False 
        
#         visa_storage.refresh_from_db()
#         assert visa_storage.remaining_visas == 49
        
#         visa_order.refresh_from_db()
#         assert visa_order.status == 'approved'
        
#         assert OrderApproval.objects.count() == 1
    
#     def test_approve_v2_no_visas_available(self, user_client, passport_with_owner):
#         #Approval v2 test with no visas condition
#         # 0 visas storage
#         visa_storage = VisaStorage.objects.create(
#             total_visas=0,
#             remaining_visas=0
#         )
        
#         visa_order = VisaOrder.objects.create(
#             user=User.objects.get(username="testuser"),
#             passport_number="1234 567890",
#             status=VisaOrder.Status.PENDING
#         )
        
#         res = user_client.post(f'/api/v2/orders/{visa_order.id}/approve/', {})
        
#         assert res.status_code == 400
#         assert "No visas available" in res.data['error']
        
#         # quantity not changed
#         visa_storage.refresh_from_db()
#         assert visa_storage.remaining_visas == 0
        
#         # and order with 'pending' status
#         visa_order.refresh_from_db()
#         assert visa_order.status == 'pending'
        
#         # OrderApproval was not created
#         assert OrderApproval.objects.count() == 0
    
#     def test_approve_v2_low_visas_warning(self, user_client, passport_with_owner):
#         #test for low visa count warning (<=1)
#         # 1 visa storage
#         visa_storage = VisaStorage.objects.create(
#             total_visas=1,
#             remaining_visas=1
#         )
        
#         visa_order = VisaOrder.objects.create(
#             user=User.objects.get(username="testuser"),
#             passport_number="1234 567890",
#             status=VisaOrder.Status.PENDING
#         )
        
#         res = user_client.post(f'/api/v2/orders/{visa_order.id}/approve/', {})
        
#         assert res.status_code == 200
#         assert res.data['remaining_visas'] == 0
#         assert res.data['low_visas'] == True 

# @pytest.mark.django_db(transaction=True)
# class TestVisaConcurrency:
#     def test_v1_race_condition_fails(self, staff_user, visa_storage):
#         #FAILING TEST. it demonstrates that v1 logic allows issuing more visas than available
#         visa_storage.remaining_visas=2
#         visa_storage.save()

#         orders = [
#             VisaOrder.objects.create(
#                 user=staff_user,
#                 passport_number=f"PASS_{i}",
#                 status=VisaOrder.Status.PENDING
#             ) for i in range(3)
#         ]

#         def call_approve(order_id):
#             #creates a fresh client for each thread to avoid session coonflicts
#             client = APIClient()
#             client.force_authenticate(user=staff_user)
#             return client.post(f'/api/v1/orders/{order_id}/approve/')
        
#         #conext manager for threadPoolExecutor with 10 workers and map that apply call_approve to all orders;
#         #When 10 threads try to approve orders simultaneously
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             list(executor.map(call_approve, [o.id for o in orders]))

#         #then check integrity
#         visa_storage.refresh_from_db()

#         # This assert will fail!. 
#         # This is because of the race condition, remaining_visas will likely be 1 
#         # bc each thread read '2', and saved '1',
#         # But i expect it to NEVER be negative if logic was right.
#         # Here the check if we issued more than we had
#         assert VisaOrder.objects.filter(status='approved').count()<=2, \
#         f"example of race condition, because issued {VisaOrder.objects.filter(status='approved').count()} visas, but only 2 were available"
#         assert visa_storage.remaining_visas >= 0
    
#     def test_v2_race_condition_passes(self, staff_user, visa_storage):
#         #v2 correctly serializes access using select for update
#         #condition - given 2 visas and 10 orders
#         visa_storage.remaining_visas=2
#         visa_storage.save()

#         orders = [
#             VisaOrder.objects.create(
#                 user=staff_user, 
#                 passport_number=f"PASS_V2_{i}", 
#                 status=VisaOrder.Status.PENDING
#             ) for i in range(3)
#         ]

#         def call_approve(order_id):
#             client = APIClient()
#             client.force_authenticate(user=staff_user)
#             return client.post(f'/api/v2/orders/{order_id}/approve/')
        
#         with ThreadPoolExecutor(max_workers=3) as executor:
#             results = list(executor.map(call_approve, [o.id for o in orders]))

#         visa_storage.refresh_from_db()

#         approved_count = VisaOrder.objects.filter(status='approved', passport_number__contains='PASS_V2_').count()

#         #only 2 approved - others 400 error
#         assert approved_count == 2
#         assert visa_storage.remaining_visas == 0
#         #8 requests shld failed wiz 400
#         error_responses = [r for r in results if r.status_code == 400]
#         assert len(error_responses) == 8
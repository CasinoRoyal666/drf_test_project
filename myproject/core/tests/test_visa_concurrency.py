import requests
from concurrent.futures import ThreadPoolExecutor
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import VisaOrder, VisaStorage, Passport
class TestVisaConcurrencyLive(StaticLiveServerTestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create user once for all tests
        cls.staff_user = User.objects.create_user(
            username="staff_concurrent",
            email="staff_concurrent@test.com",
            password="password123",
            is_staff=True
        )
        # Get JWT token
        refresh = RefreshToken.for_user(cls.staff_user)
        cls.token = str(refresh.access_token)
    
    def setUp(self):
        # Create fresh storage and passport for each test
        self.visa_storage = VisaStorage.objects.create(
            total_visas=50,
            remaining_visas=2
        )
        Passport.objects.create(
            owner=self.staff_user,
            full_name="Staff User",
            passport_number="CONCURRENT_PASS",
            address="Test"
        )
    
    def test_v1_race_condition_fails(self):
        """V1: Race condition allows issuing more visas than available"""
        # Create 3 orders
        orders = [
            VisaOrder.objects.create(
                user=self.staff_user,
                passport_number=f"PASS_V1_{i}",
                status=VisaOrder.Status.PENDING
            ) for i in range(3)
        ]
        
        def call_approve(order_id):
            return requests.post(
                f'{self.live_server_url}/api/v1/orders/{order_id}/approve/',
                headers={'Authorization': f'Bearer {self.token}'},
                json={}
            )
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(call_approve, [o.id for o in orders]))
        
        self.visa_storage.refresh_from_db()
        approved_count = VisaOrder.objects.filter(status='approved').count()
        
        # This should FAIL - race condition issued more than 2
        self.assertLessEqual(approved_count, 2, 
            f"RACE CONDITION: Issued {approved_count} visas, only 2 available!")
    
    def test_v2_race_condition_passes(self):
        """V2: select_for_update prevents race condition"""
        orders = [
            VisaOrder.objects.create(
                user=self.staff_user,
                passport_number=f"PASS_V2_{i}",
                status=VisaOrder.Status.PENDING
            ) for i in range(3)
        ]
        
        def call_approve(order_id):
            return requests.post(
                f'{self.live_server_url}/api/v2/orders/{order_id}/approve/',
                headers={'Authorization': f'Bearer {self.token}'},
                json={}
            )
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(call_approve, [o.id for o in orders]))
        
        self.visa_storage.refresh_from_db()
        approved_count = VisaOrder.objects.filter(
            status='approved', 
            passport_number__startswith='PASS_V2_'
        ).count()
        
        # Exactly 2 approved
        self.assertEqual(approved_count, 2)
        self.assertEqual(self.visa_storage.remaining_visas, 0)
        
        # 1 request should fail with 400
        error_responses = [r for r in results if r.status_code == 400]
        self.assertEqual(len(error_responses), 1)
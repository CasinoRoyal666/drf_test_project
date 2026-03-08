import requests
from concurrent.futures import ThreadPoolExecutor
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import VisaOrder, VisaStorage, Passport
import pytest
import uuid

@pytest.mark.concurrency
class TestVisaConcurrencyLive(StaticLiveServerTestCase):

    def setUp(self):
        # Create fresh user for each test to avoid FK violations
        self.staff_user = User.objects.create_user(
            username=f"staff_{uuid.uuid4().hex[:8]}",
            email="staff@test.com",
            password="password123",
            is_staff=True
        )
        # Get JWT token
        refresh = RefreshToken.for_user(self.staff_user)
        self.token = str(refresh.access_token)

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

        # this test should fail
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

    def test_v1_visas_go_negative(self):
        """V1: Race condition causes visas to go negative"""
        orders = [
            VisaOrder.objects.create(
                user=self.staff_user,
                passport_number=f"NEG_V1_{i}",
                status=VisaOrder.Status.PENDING
            ) for i in range(5)
        ]

        def call_approve(order_id):
            return requests.post(
                f'{self.live_server_url}/api/v1/orders/{order_id}/approve/',
                headers={'Authorization': f'Bearer {self.token}'},
                json={}
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(call_approve, [o.id for o in orders]))

        self.visa_storage.refresh_from_db()
        approved_count = VisaOrder.objects.filter(
            status='approved',
            passport_number__startswith='NEG_V1_'
        ).count()

        #this test should fail
        self.assertLessEqual(approved_count, 2,
            f"RACE CONDITION: Approved {approved_count} visas, only 2 available!")

    def test_v2_visas_never_negative(self):
        """V2: Locking prevents visas from going negative"""
        orders = [
            VisaOrder.objects.create(
                user=self.staff_user,
                passport_number=f"NEG_V2_{i}",
                status=VisaOrder.Status.PENDING
            ) for i in range(5)
        ]

        def call_approve(order_id):
            return requests.post(
                f'{self.live_server_url}/api/v2/orders/{order_id}/approve/',
                headers={'Authorization': f'Bearer {self.token}'},
                json={}
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(call_approve, [o.id for o in orders]))

        self.visa_storage.refresh_from_db()
        approved_count = VisaOrder.objects.filter(
            status='approved',
            passport_number__startswith='NEG_V2_'
        ).count()

        self.assertGreaterEqual(self.visa_storage.remaining_visas, 0,
            f"Visas went negative: {self.visa_storage.remaining_visas}")
        self.assertEqual(self.visa_storage.remaining_visas, 0)
        self.assertEqual(approved_count, 2)

        # 3 requests should receive a 400 error
        error_responses = [r for r in results if r.status_code == 400]
        self.assertEqual(len(error_responses), 3)

from concurrent.futures import ThreadPoolExecutor
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import requests
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import VisaOrder, VisaStorage, Passport, PassportCore, PassportDetails
import pytest
import uuid

@pytest.mark.concurrency
class TestTaskNew(StaticLiveServerTestCase):

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

    def test_v3_read_commited_isolation(self):
        """no select_for_update -> race condition"""
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
                f'{self.live_server_url}/api/v3/orders/{order_id}/approve/',
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
    
    def test_v4_serializable_isolation(self):
        """"""
        self.visa_storage.remaining_visas = 2
        self.visa_storage.save()

        orders = [
            VisaOrder.objects.create(
                user=self.staff_user,
                passport_number=f"SERIAL_V4_{i}",
                status=VisaOrder.Status.PENDING
            ) for i in range(5)
        ]

        def call_approve(order_id):
            return requests.post(
                f'{self.live_server_url}/api/v4/orders/{order_id}/approve/',
                headers={'Authorization': f'Bearer {self.token}'},
                json={}
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(call_approve, [o.id for o in orders]))
        
        self.visa_storage.refresh_from_db()

        self.assertEqual(self.visa_storage.remaining_visas, 0)

        #count types of answers
        success_responses = [r for r in results if r.status_code == 200]
        conflict_responses = [r for r in results if r.status_code == 409] #ser. conflict
        out_of_visas_responses = [r for r in results if r.status_code == 400] #out of visas

        self.assertEqual(len(success_responses), 2, f"Expected 2 success cases, but {len(success_responses)} returned")

        approved_in_db = VisaOrder.objects.filter(
            status = VisaOrder.Status.APPROVED,
            passport_number__startswith='SERIAL_V4_'
        ).count()
        self.assertEqual(approved_in_db, 2)

        #rest of requests get 409 or 400
        total_errors = len(conflict_responses) + len(out_of_visas_responses)
        self.assertEqual(total_errors, 3, "rest 3 requests must return an error")

        print(f"Success cases -> {len(success_responses)}, 409 conflicts -> {len(conflict_responses)}, 400 no visas -> {len(out_of_visas_responses)}")

    def test_passport_split_unique(self):
        url = f"{self.live_server_url}/api/split-passport/get_or_create_unique/"
        data = {"passport_number": "UNIQUE_123", "full_name": "Test Split"}

        def call_create():
            return requests.post(
                url,
                headers={'Authorization': f'Bearer {self.token}'},
                json=data
            )
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(lambda _: call_create(), range(5)))

            self.assertEqual(PassportCore.objects.count(), 1)
            self.assertEqual(PassportDetails.objects.count(), 1)

            ids = [r.json()['id'] for r in results if r.status_code in [200, 201]]
            self.assertEqual(len(set(ids)), 1)

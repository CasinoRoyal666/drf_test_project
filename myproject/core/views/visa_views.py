from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, connection, IntegrityError
from django.db.models import F
import time

from ..serializers import VisaOrderSerializer
from ..models import VisaStorage, VisaOrder, OrderApproval, PassportCore, PassportDetails

class VisaOrderViewSetV1(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated]
	serializer_class = VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@action(detail=True, methods=['post'])
	#incorrect logic: no locking, has artificial delay to trigger race condition
	def approve(self, request, pk=None):
		order = self.get_object()

		storage = VisaStorage.objects.first()

		#read current value
		current_visas = storage.remaining_visas
		#art delay
		time.sleep(0.2)
		#write back
		storage.remaining_visas = current_visas - 1
		storage.save()

		order.status = VisaOrder.Status.APPROVED
		order.save()

		OrderApproval.objects.create(order=order, staff_member=request.user)

		return Response({
			"status":"approved",
			"remaining_visas": storage.remaining_visas
		}, status=status.HTTP_200_OK)
	
	
class VisaOrderViewSetV2(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated]
	serializer_class = VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@action(detail=True, methods=['post'])
	# correct logic: uses SELECT FOR UPDATE to lock the row
	def approve(self, request, pk=None):
		order = self.get_object()

		with transaction.atomic():
			#locks the row until tran. is commited
			storage = VisaStorage.objects.select_for_update().first()

			if storage.remaining_visas <= 0:
				return Response(
					{"error": "No visas available right now"},
					status=status.HTTP_400_BAD_REQUEST
				)

			storage.remaining_visas -= 1
			storage.save()

			order.status = VisaOrder.Status.APPROVED
			order.save()

			OrderApproval.objects.create(
				order = order,
				staff_member = request.user
			)

			response_data = {
				"status": "approved",
				"remaining_visas": storage.remaining_visas,
				"low_visas": storage.remaining_visas <= 1
			}
			return Response(response_data, status=status.HTTP_200_OK)

class VisaOrderViewSetV3(viewsets.ModelViewSet):
	"""READ COMMITED (postgres on default isolation mode),
	without select_for_update we can see race_condition"""
	permission_classes=[IsAuthenticated]
	serializer_class=VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	@action(detail=True, methods=['post'])
	def approve(self, request, pk=None):
		order = self.get_object()
		with transaction.atomic():
			#READ COMMITED
			with connection.cursor() as cursor:
				cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
			
			storage = VisaStorage.objects.first()
			time.sleep(0.2)

			if storage.remaining_visas <= 0:
				return Response({"error": "No visas"}, status=400)
			
			storage.remaining_visas -= 1
			storage.save()
			order.status = VisaOrder.Status.APPROVED
			order.save()
			return Response({"status": "approved", "remaining_visas": storage.remaining_visas})

class VisaOrderViewSetV4(viewsets.ModelViewSet):
	"""SERIALIZABLE. 
	db will throw error when detects a conflict between parallel edits."""
	permission_classes = [IsAuthenticated]
	serializer_class = VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	@action(detail=True, methods=['post'])
	def approve(self, request, pk=None):
		order = self.get_object()
		try:
			with transaction.atomic():
				with connection.cursor() as cursor:
					cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
				
				storage = VisaStorage.objects.first()
				if storage.remaining_visas <= 0:
					return Response({"error": "No visas"}, status=400)
				
				storage.remaining_visas -= 1
				storage.save()
				order.status = VisaOrder.Status.APPROVED
				order.save()
				return Response({"status": "approved", "remaining_visas": storage.remaining_visas})
		except Exception as e:
			return Response({"error": "Concurrency conflict", "detail": str(e)}, status=409)

#unique pairs between tables
class PassportSplitView(viewsets.ViewSet):
	permission_classes = [IsAuthenticated]

	@action(detail=False, methods=['post'])
	def get_or_create_unique(self, request):
		passport_number = request.data.get('passport_number')
		full_name = request.data.get('full_name')
		user = request.user

		try:
			with transaction.atomic():
				core, created = PassportCore.objects.get_or_create(owner=user)
				details, d_created = PassportDetails.objects.get_or_create(
					core=core,
					passport_number=passport_number,
					defaults={'full_name': full_name, 'adress': "Test Address"}
				)

				return Response({"id": core.id, "created": d_created}, 
					status=status.HTTP_201_CREATED if d_created else status.HTTP_200_OK)
			
				
		except IntegrityError:
			core = PassportCore.objects.get(owner=user)
			return Response({"id": core.id, "created": False}, status=status.HTTP_200_OK)
		

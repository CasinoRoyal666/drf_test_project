from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F

from ..serializers import VisaOrderSerializer
from ..models import VisaStorage, VisaOrder, OrderApproval

class VisaOrderViewSetV1(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated]
	serializer_class = VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@action(detail=True, methods=['post'])
	#incorrect logic
	def approve(self, request, pk=None):
		order = self.get_object()

		storage = VisaStorage.objects.first()
		storage.remaining_visas -= 1
		storage.save()

		order.status = VisaOrder.Status.APPROVED
		order.save()

		OrderApproval.objects.create(
			order=order,
			staff_member = request.user
		)
		
		return Response(
			{
				"status": "approved",
				"remaining_visas": storage.remaining_visas
			},
			status=status.HTTP_200_OK
		)
		
class VisaOrderViewSetV2(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticated]
	serializer_class = VisaOrderSerializer

	def get_queryset(self):
		return VisaOrder.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)

	@action(detail=True, methods=['post'])
	# correct logic
	def approve(self, request, pk=None):
		order = self.get_object()

		with transaction.atomic():
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
		

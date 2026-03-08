from django.db import models
from django.contrib.auth.models import User


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# context logic
class Passport(TimestampMixin):
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='passport'
    )

    full_name = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=20)
    address = models.CharField(max_length=200)

    def __str__(self):
        return f"Passport: {self.full_name}"

# two new models: PassportCore and PassportDetails - needed to test different levels of tran. isolation
class PassportCore(TimestampMixin):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='passport_cores')

    def __str__(self):
        return f"Core for {self.owner.username}"

class PassportDetails(TimestampMixin):
    core = models.ForeignKey(PassportCore, on_delete=models.CASCADE, related_name='details')
    passport_number = models.CharField(max_length=20)
    full_name = models.CharField(max_length=50)
    adress = models.CharField(max_length=100)

    class Meta:
        #garant unique passaport number x core (linked to user) pair
        unique_together = ('core', 'passport_number')

    def __str__(self):
        return f"Details: {self.passport_number}"
    


class VisaStorage(TimestampMixin):
    total_visas = models.IntegerField(default=50)
    remaining_visas = models.IntegerField(default=50)

    def __str__(self):
        return f"Visa inventory: {self.remaining_visas}/{self.total_visas}"

class VisaOrder(TimestampMixin):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        DENIED = 'denied', 'Denied'
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='visa_orders'
    )
    passport_number = models.CharField(max_length=20)
    status  = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    def __str__ (self):
        return f"Order {self.id}: {self.passport_number} - {self.status}"

class OrderApproval(TimestampMixin):
    order = models.ForeignKey(
        VisaOrder, 
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    staff_member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_approvals'
    )
    approved_at = models.DateTimeField(auto_now_add=True)

    def __str__ (self):
        return f"Approval for Order {self.order.id} by {self.staff_member.username}"
    



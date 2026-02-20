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
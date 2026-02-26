from django.contrib import admin
from .models import Passport, VisaOrder, VisaStorage

@admin.register(Passport)
class PassportAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'passport_number', 'address')
    search_fields = ('full_name', 'passport_number')
    list_editable = ('passport_number',) 

@admin.register(VisaOrder)
class VisaOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'passport_number', 'status')
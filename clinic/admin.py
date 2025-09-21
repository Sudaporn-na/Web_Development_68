from django.contrib import admin
from .models import User, Patient, Dentist, Service, Appointment

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'role', 'email', 'is_active', 'date_joined')
    list_filter  = ('role', 'is_active', 'is_staff')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'gender', 'date_of_birth', 'phone', 'created_at')
    search_fields = ('name', 'phone')

@admin.register(Dentist)
class DentistAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'phone', 'license_number', 'is_active')
    search_fields = ('name', 'license_number')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_minutes', 'is_active')
    search_fields = ('name',)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_date', 'start_time', 'end_time', 'patient', 'dentist', 'service', 'status')
    list_filter = ('appointment_date', 'status', 'dentist', 'service')
    search_fields = ('patient__name', 'dentist__name')

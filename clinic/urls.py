from django.urls import path
from . import views


urlpatterns = [
    path('', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),

    path('dashboard/', views.dashboard_page, name='dashboard'),

    path('patients/', views.patients_page, name='patients'),
    path('patients/add/', views.patient_add, name='patient_add'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'),

    path('appointments/', views.appointments_page, name='appointments'),
    path('appointments/add/', views.appointment_add, name='appointment_add'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),

    path('dentists/', views.dentists_page, name='dentists'),
    path('dentists/add/', views.dentist_add, name='dentist_add'),
    path('dentists/<int:pk>/edit/', views.dentist_edit, name='dentist_edit'),
    path('dentists/<int:pk>/delete/', views.dentist_delete, name='dentist_delete'),

    path('services/', views.services_page, name='services'),
    path('services/add/', views.service_add, name='service_add'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),

    path('logout/', views.logout_view, name='logout'),

    path("password/otp/request/", views.request_otp_view, name="request_otp"),
    path("password/otp/verify/", views.verify_otp_view, name="verify_otp"),
    path("password/otp/reset/", views.reset_password_custom, name="reset_password_custom"),



    path("patient/dashboard/", views.patient_dashboard, name="patient_dashboard"),
    path("patient/profile/", views.patient_profile, name="patient_profile"),
    path("patient/appointments/", views.patient_appointments, name="appointments_patient"),
    
]


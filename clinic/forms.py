from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Patient, Dentist, Service, Appointment

class BaseTWForm(forms.ModelForm):
    """ฐานสำหรับใส่ class Tailwind ให้ทุก field"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({
                "class": "w-full border px-3 py-2 rounded focus:ring-indigo-500 focus:border-indigo-500"
            })

class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "password1", "password2"]

   
class PatientForm(BaseTWForm):
    class Meta:
        model = Patient
        fields = "__all__"

class DentistForm(BaseTWForm):
    class Meta:
        model = Dentist
        fields = "__all__"

class ServiceForm(BaseTWForm):
    class Meta:
        model = Service
        fields = "__all__"

class AppointmentForm(BaseTWForm):
    class Meta:
        model = Appointment
        fields = "__all__"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # จำกัดตัวเลือกเฉพาะ active และเรียงสวย ๆ
        self.fields["dentist"].queryset = Dentist.objects.filter(is_active=True).order_by("name")
        self.fields["service"].queryset = Service.objects.filter(is_active=True).order_by("name")

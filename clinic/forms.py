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

class PatientProfileForm(BaseTWForm):
    class Meta:
        model = Patient
        fields = ["name", "gender", "phone", "email", "address", "photo", "date_of_birth"]

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
        widgets = {
            "appointment_date": forms.DateInput(
                attrs={
                    "type": "date",   # ✅ HTML5 date picker
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                }
            ),
            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",   # ✅ HTML5 time picker
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                }
            ),
            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",   # ✅ HTML5 time picker
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                    "placeholder": "หมายเหตุเพิ่มเติม (ถ้ามี)...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dentist"].queryset = Dentist.objects.filter(is_active=True).order_by("name")
        self.fields["service"].queryset = Service.objects.filter(is_active=True).order_by("name")




from django import forms
from django.core.exceptions import ValidationError
from .models import Appointment, Dentist, Service

class PatientAppointmentForm(BaseTWForm):
    class Meta:
        model = Appointment
        exclude = ["patient", "created_by", "status", "created_at", "updated_at"] 
        widgets = {
            "appointment_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                }
            ),
            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500",
                    "placeholder": "หมายเหตุเพิ่มเติม (ถ้ามี)...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)  # 👈 ดึง patient จาก view
        super().__init__(*args, **kwargs)
        self.fields["dentist"].queryset = Dentist.objects.filter(is_active=True).order_by("name")
        self.fields["service"].queryset = Service.objects.filter(is_active=True).order_by("name")

    def clean(self):    
        cleaned_data = super().clean()
        dentist = cleaned_data.get("dentist")
        appointment_date = cleaned_data.get("appointment_date")
        start_time = cleaned_data.get("start_time")

        # 1. หมอว่างมั้ย
        if dentist and appointment_date and start_time:
            if Appointment.objects.filter(
                dentist=dentist,
                appointment_date=appointment_date,
                start_time=start_time
            ).exists():
                raise ValidationError("ทันตแพทย์ท่านนี้มีนัดในเวลานี้แล้ว กรุณาเลือกเวลาอื่น")

        # 2. คนไข้ซ้ำมั้ย
        if self.patient and appointment_date and start_time:
            if Appointment.objects.filter(
                patient=self.patient,
                appointment_date=appointment_date,
                start_time=start_time
            ).exists():
                raise ValidationError("คุณมีนัดในเวลานี้อยู่แล้ว กรุณาเลือกเวลาอื่น")

        return cleaned_data







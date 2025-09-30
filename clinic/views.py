# clinic/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.db.models import Sum

import calendar
from datetime import date

from .decorators import role_required
from .models import Patient, Dentist, Service, Appointment, EmailOTP
from .forms import PatientProfileForm, UserRegisterForm, PatientForm, DentistForm, ServiceForm, AppointmentForm
from clinic import models

User = get_user_model()

# ---------------------------
# 🔐 Authentication
# ---------------------------
def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # ✅ Redirect ตาม role หลังล็อกอิน
            if user.role == "admin":
                return redirect("dashboard")
            elif user.role == "patient":
                return redirect("patient_dashboard")
            else:
                return redirect("login")  # fallback
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return render(request, "login.html")




def register_page(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "patient"   # ทุกคนที่สมัครผ่านเว็บเป็น patient
            user.save()
            messages.success(request, "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
            return redirect("login")
    else:
        form = UserRegisterForm()
    return render(request, "register.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------
# 📊 Dashboard
# ---------------------------
# views.py
from django.db.models import Count, Sum
from .models import Patient, Appointment, Dentist

@login_required
@role_required(["admin"])
def dashboard_page(request):
    today = date.today()
    current_year = today.year
    selected_month = int(request.GET.get("month") or today.month)
    selected_month_label = calendar.month_name[selected_month]

    # Summary cards
    patients_count = Patient.objects.count()
    appointments_count = Appointment.objects.count()
    dentists_count = Dentist.objects.count()

    # จำนวนผู้ป่วยรายวันในเดือน
    days_in_month = calendar.monthrange(current_year, selected_month)[1]
    days = list(range(1, days_in_month + 1))
    patients_daily = [
        Patient.objects.filter(
            created_at__year=current_year,
            created_at__month=selected_month,
            created_at__day=d
        ).count()
        for d in days
    ]

    # เพศ
    male_count = Patient.objects.filter(gender="M").count()
    female_count = Patient.objects.filter(gender="F").count()
    patients_gender = [male_count, female_count]

    # นัดหมายตามสถานะในเดือน ✅ ใช้ appointment_date
    status_stats = (
        Appointment.objects
        .filter(appointment_date__year=current_year, appointment_date__month=selected_month)
        .values("status")
        .annotate(count=Count("id"))
    )
    status_data = {item["status"]: item["count"] for item in status_stats}
    status_labels = ["scheduled", "confirmed", "completed", "cancelled", "no_show"]
    status_counts = [status_data.get(s, 0) for s in status_labels]

    # dropdown เดือน
    all_months = [{"value": i, "label": calendar.month_name[i]} for i in range(1, 13)]

    context = {
        "patients_count": patients_count,
        "appointments_count": appointments_count,
        "dentists_count": dentists_count,
        "patients_daily": patients_daily,
        "days": days,
        "patients_gender": patients_gender,
        "all_months": all_months,
        "selected_month": selected_month,
        "selected_month_label": selected_month_label,
        "status_labels": status_labels,
        "status_counts": status_counts,
    }
    return render(request, "dental_clinic/dashboard.html", context)



# ---------------------------
# 📄 Pages
# ---------------------------
@login_required
@role_required(["admin", "patient"])
def patients_page(request):
    patients = Patient.objects.all().order_by("-created_at")
    return render(request, "dental_clinic/patients.html", {"patients": patients})

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Appointment

@login_required
@role_required(["admin", "patient"])
def appointments_page(request):
    status = request.GET.get("status")
    appointments = Appointment.objects.select_related("patient", "dentist", "service").order_by(
        "-appointment_date", "-start_time"
    )

    if status:
        appointments = appointments.filter(status=status)
    return render(request, "dental_clinic/appointments.html", {
        "appointments": appointments,
        "status": status,    
        })

@login_required
@role_required(["admin"])
def dentists_page(request):
    dentists = Dentist.objects.all().order_by("name")
    return render(request, "dental_clinic/dentists.html", {"dentists": dentists})


@login_required
@role_required(["admin"])
def services_page(request):
    services = Service.objects.all().order_by("name")
    return render(request, "dental_clinic/services.html", {"services": services})


# ---------------------------
# ✍️ CRUD: Patient
# ---------------------------
@login_required
def patient_add(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "เพิ่มข้อมูลคนไข้สำเร็จ")
            return redirect("patients")
    else:
        form = PatientForm()
    return render(request, "dental_clinic/patient_form.html", {"form": form})


@login_required
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขข้อมูลคนไข้สำเร็จ")
            return redirect("patients")
    else:
        form = PatientForm(instance=patient)
    return render(request, "dental_clinic/patient_form.html", {"form": form})


@login_required
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        patient.delete()
        messages.success(request, "ลบข้อมูลคนไข้สำเร็จ")
        return redirect("patients")
    return render(request, "dental_clinic/confirm_delete.html", {"object": patient, "type": "คนไข้"})


# ---------------------------
# ✍️ CRUD: Dentist
# ---------------------------
@login_required
def dentist_add(request):
    if request.method == "POST":
        form = DentistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "เพิ่มข้อมูลทันตแพทย์สำเร็จ")
            return redirect("dentists")
    else:
        form = DentistForm()
    return render(request, "dental_clinic/dentist_form.html", {"form": form})


@login_required
def dentist_edit(request, pk):
    dentist = get_object_or_404(Dentist, pk=pk)
    if request.method == "POST":
        form = DentistForm(request.POST, instance=dentist)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขข้อมูลทันตแพทย์สำเร็จ")
            return redirect("dentists")
    else:
        form = DentistForm(instance=dentist)
    return render(request, "dental_clinic/dentist_form.html", {"form": form})


@login_required
def dentist_delete(request, pk):
    dentist = get_object_or_404(Dentist, pk=pk)
    if request.method == "POST":
        dentist.delete()
        messages.success(request, "ลบข้อมูลทันตแพทย์สำเร็จ")
        return redirect("dentists")
    return render(request, "dental_clinic/confirm_delete.html", {"object": dentist, "type": "ทันตแพทย์"})


# ---------------------------
# ✍️ CRUD: Service
# ---------------------------
@login_required
def service_add(request):
    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "เพิ่มบริการสำเร็จ")
            return redirect("services")
    else:
        form = ServiceForm()
    return render(request, "dental_clinic/service_form.html", {"form": form})


@login_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขบริการสำเร็จ")
            return redirect("services")
    else:
        form = ServiceForm(instance=service)
    return render(request, "dental_clinic/service_form.html", {"form": form})


@login_required
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        service.delete()
        messages.success(request, "ลบบริการสำเร็จ")
        return redirect("services")
    return render(request, "dental_clinic/confirm_delete.html", {"object": service, "type": "บริการ"})


# ---------------------------
# ✍️ CRUD: Appointment
# ---------------------------
@login_required
def appointment_add(request):
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            messages.success(request, "เพิ่มนัดหมายสำเร็จ")
            return redirect("appointments")
    else:
        form = AppointmentForm()
    return render(request, "dental_clinic/appointment_form.html", {"form": form})


@login_required
def appointment_edit(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขนัดหมายสำเร็จ")
            return redirect("appointments")
    else:
        form = AppointmentForm(instance=appointment)
    return render(request, "dental_clinic/appointment_form.html", {"form": form})


@login_required
def appointment_delete(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        appointment.delete()
        messages.success(request, "ลบนัดหมายสำเร็จ")
        return redirect("appointments")
    return render(request, "dental_clinic/confirm_delete.html", {"object": appointment, "type": "นัดหมาย"})


# ---------------------------
# 🔑 OTP Reset Password
# ---------------------------
def _send_otp_email(to_email: str, first_name: str, code: str):
    subject = "รหัส OTP สำหรับรีเซ็ตรหัสผ่าน (หมดอายุภายใน 5 นาที)"
    body = (
        f"สวัสดี {first_name or ''}\n\n"
        f"รหัส OTP ของคุณคือ: {code}\n"
        f"**รหัสจะหมดอายุภายใน 5 นาที**\n\n"
        f"หากคุณไม่ได้ร้องขอ กรุณาเพิกเฉยอีเมลฉบับนี้"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER)
    send_mail(subject, body, from_email, [to_email], fail_silently=False)


@csrf_protect
@never_cache
def request_otp_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if not email:
            messages.error(request, "กรุณากรอกอีเมล")
            return redirect("request_otp")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "ไม่พบอีเมลนี้ในระบบ")
            return redirect("request_otp")

        otp_obj = EmailOTP.generate_otp(user=user, minutes=5)
        _send_otp_email(user.email, user.first_name, otp_obj.otp_code)

        request.session["otp_user_id"] = user.id
        request.session["otp_requested_at"] = timezone.now().isoformat()
        messages.success(request, "เราได้ส่งรหัส OTP ไปที่อีเมลของคุณแล้ว")
        return redirect("verify_otp")

    return render(request, "otp/request_otp.html")


@csrf_protect
@never_cache
def verify_otp_view(request):
    user_id = request.session.get("otp_user_id")
    if not user_id:
        messages.error(request, "เซสชันหมดอายุ กรุณาขอรหัสใหม่")
        return redirect("request_otp")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "ไม่พบผู้ใช้")
        return redirect("request_otp")

    if request.method == "POST":
        code = (request.POST.get("otp") or "").strip()
        if not code:
            messages.error(request, "กรุณากรอกรหัส OTP")
            return redirect("verify_otp")

        try:
            otp_obj = EmailOTP.objects.filter(user=user).latest("created_at")
        except EmailOTP.DoesNotExist:
            messages.error(request, "ไม่พบรหัส OTP กรุณาขอรหัสใหม่")
            return redirect("request_otp")

        if otp_obj.is_valid(code):
            request.session["otp_verified"] = True
            messages.success(request, "ยืนยัน OTP สำเร็จ โปรดตั้งรหัสผ่านใหม่")
            return redirect("reset_password_custom")
        else:
            messages.error(request, "รหัส OTP ไม่ถูกต้องหรือหมดอายุแล้ว")
            return redirect("verify_otp")

    return render(request, "otp/verify_otp.html")


@csrf_protect
@never_cache
def reset_password_custom(request):
    if not request.session.get("otp_verified"):
        messages.error(request, "ยังไม่ได้ยืนยัน OTP")
        return redirect("request_otp")

    user_id = request.session.get("otp_user_id")
    if not user_id:
        messages.error(request, "เซสชันหมดอายุ กรุณาขอรหัสใหม่")
        return redirect("request_otp")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "ไม่พบผู้ใช้")
        return redirect("request_otp")

    if request.method == "POST":
        new_password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if len(new_password) < 8:
            messages.error(request, "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร")
            return redirect("reset_password_custom")

        if new_password != confirm_password:
            messages.error(request, "รหัสผ่านไม่ตรงกัน")
            return redirect("reset_password_custom")

        user.set_password(new_password)
        user.save()

        for key in ["otp_user_id", "otp_verified", "otp_requested_at"]:
            request.session.pop(key, None)

        messages.success(request, "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว สามารถเข้าสู่ระบบได้")
        return redirect("login")

    return render(request, "otp/reset_password_custom.html")




from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Patient, Appointment


@login_required
@role_required(["patient"])
def patient_dashboard(request):
    user = request.user  
    patient = Patient.objects.filter(email=user.email).first()
    appointments = Appointment.objects.filter(patient=patient) if patient else []
    context = {
        "user": user,
        "patient": patient,
        "appointments": appointments,
    }
    return render(request, "patient/patient_dashboard.html", context)



# clinic/views.py
# views.py
from django.apps import apps
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

@login_required
def object_detail(request, model_name, pk):
    model = apps.get_model("clinic", model_name.capitalize())
    obj = get_object_or_404(model, pk=pk)

    # 🔹 เก็บคู่ (verbose_name, value) เป็น list
    field_values = []
    for field in model._meta.fields:
        value = getattr(obj, field.name)
        field_values.append({
            "label": field.verbose_name,
            "value": value,
        })

    return render(request, "dental_clinic/object_detail.html", {
        "object": obj,
        "type": model._meta.verbose_name,
        "field_values": field_values,
    })




from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Appointment

@login_required
@csrf_exempt
def complete_appointment(request, pk):
    """เปลี่ยนสถานะนัดหมายเป็น completed"""
    if request.method == "POST":
        try:
            appt = Appointment.objects.get(pk=pk)
            appt.status = "completed"
            appt.save()
            return JsonResponse({"success": True})
        except Appointment.DoesNotExist:
            return JsonResponse({"success": False, "error": "Not found"}, status=404)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)








from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Appointment, Dentist, Service




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Appointment, Patient, Dentist, Service
from .forms import PatientAppointmentForm

@login_required
def patient_appointments(request):
    patient = Patient.objects.filter(email=request.user.email).first()
    if not patient:
        messages.error(request, "ไม่พบข้อมูลผู้ป่วยของคุณ กรุณาติดต่อคลินิก")
        return redirect("patient_dashboard")

    if request.method == "POST":
        form = PatientAppointmentForm(request.POST, patient=patient)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.patient = patient
            appt.status = "scheduled"
            appt.created_by = request.user
            appt.save()
            messages.success(request, "เพิ่มนัดหมายเรียบร้อย")
            return redirect("appointments_patient")
        else:
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = PatientAppointmentForm(patient=patient)

    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related("dentist", "service").order_by("-appointment_date", "-start_time")

    return render(request, "patient/appointments_patient.html", {
        "appointments": appointments,
        "form": form,
        "patient": patient,
    })



@login_required
def appointment_update_status(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status")
        if new_status in dict(Appointment.STATUS_CHOICES):
            appt.status = new_status
            appt.save()
            messages.success(request, "อัปเดตสถานะสำเร็จ")
        else:
            messages.error(request, "สถานะไม่ถูกต้อง")
    return redirect("appointments_patient")


@login_required
def confirm_appointment(request, pk):
    # หา patient จาก email user ที่ login
    patient = Patient.objects.filter(email=request.user.email).first()
    if not patient:
        messages.error(request, "ไม่พบข้อมูลผู้ป่วยของคุณ")
        return redirect("appointments_patient")

    # หา appointment ของ patient
    appt = get_object_or_404(Appointment, pk=pk, patient=patient)

    # ถ้าคนที่สร้างนัดนี้เป็น user คนเดียวกับผู้ที่ล็อกอิน
    if appt.created_by == request.user:
        messages.error(
            request,
            "คุณไม่สามารถยืนยันการจองที่คุณสร้างเองได้ ต้องรอแอดมินคลินิกยืนยันการจองแทน"
        )
        return redirect("appointments_patient")

    # ✅ ยืนยันได้ ก็ต่อเมื่อสร้างโดย Admin
    appt.status = "confirmed"
    appt.save()

    messages.success(request, "คุณได้ยืนยันการนัดหมายแล้ว")
    return redirect("appointments_patient")




from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Appointment

@login_required
def confirm_appointment_admin(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)

    # ❌ ถ้าแอดมินเป็นคนสร้างเอง ห้ามยืนยัน
    if appt.created_by == request.user:
        messages.error(request, "ไม่สามารถยืนยันการจองที่คุณสร้างเองได้")
        return redirect("appointments")

    # ✅ เปลี่ยนสถานะเป็น confirmed
    appt.status = "confirmed"
    appt.save()
    messages.success(request, f"ยืนยันการจองของ {appt.patient.name} เรียบร้อยแล้ว")

    return redirect("appointments")

@login_required
def cancel_appointment(request, pk):
    patient = Patient.objects.filter(email=request.user.email).first()
    appt = get_object_or_404(Appointment, pk=pk, patient=patient)

    appt.status = "cancelled"
    appt.save()
    messages.success(request, "คุณได้ยกเลิกการนัดหมายแล้ว")
    return redirect("appointments_patient")


@login_required
def edit_appointment(request, pk):
    patient = Patient.objects.filter(email=request.user.email).first()
    appt = get_object_or_404(Appointment, pk=pk, patient=patient, created_by=request.user)

    if request.method == "POST":
        form = PatientAppointmentForm(request.POST, patient=patient, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขนัดหมายเรียบร้อย")
            return redirect("appointments_patient")   
    else:
        form = PatientAppointmentForm(patient=patient, instance=appt)

    return render(request, "patient/appointment_edit.html", {"form": form, "appt": appt})


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patient
from .forms import PatientForm

@login_required
def patient_profile(request):
    patient = Patient.objects.filter(email=request.user.email).first()
    if not patient:
        messages.error(request, "ไม่พบข้อมูลผู้ป่วย")
        return redirect("patient_dashboard")

    form = PatientProfileForm(instance=patient)
    return render(request, "patient/patient_profile.html", {
        "patient": patient,
        "form": form,   # 👈 ส่งฟอร์มไปด้วย
    })



@login_required
def patient_edit_profile(request):
    patient = Patient.objects.filter(email=request.user.email).first()
    if not patient:
        messages.error(request, "ไม่พบข้อมูลผู้ป่วย")
        return redirect("patient_dashboard")

    if request.method == "POST":
        form = PatientProfileForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขโปรไฟล์เรียบร้อย")
        else:
            messages.error(request, "ข้อมูลไม่ถูกต้อง กรุณาลองอีกครั้ง")

    return redirect("patient_profile")


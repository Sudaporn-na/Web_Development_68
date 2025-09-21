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
from .forms import UserRegisterForm, PatientForm, DentistForm, ServiceForm, AppointmentForm

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
    total_revenue = Appointment.objects.filter(
        status="completed"
    ).aggregate(total=Sum("service__price"))["total"] or 0

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

    # dropdown เดือน
    all_months = [{"value": i, "label": calendar.month_name[i]} for i in range(1, 13)]

    context = {
        "patients_count": patients_count,
        "appointments_count": appointments_count,
        "dentists_count": dentists_count,
        "total_revenue": total_revenue,
        "patients_daily": patients_daily,
        "days": days,
        "patients_gender": patients_gender,
        "all_months": all_months,
        "selected_month": selected_month,
        "selected_month_label": selected_month_label,
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


@login_required
@role_required(["admin", "patient"])
def appointments_page(request):
    appointments = Appointment.objects.select_related("patient", "dentist", "service").order_by(
        "-appointment_date", "-start_time"
    )
    return render(request, "dental_clinic/appointments.html", {"appointments": appointments})


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

@login_required
def patient_profile(request):
    users = get_object_or_404(User, email=request.user.email)
    return render(request, "patient/patient_profile.html", {"patient": users})

@login_required
def patient_appointments(request):
    patient = Patient.objects.filter(email=request.user.email).first()
    if not patient:
        appointments = []
    else:
        appointments = Appointment.objects.filter(
            patient=patient
        ).select_related("dentist", "service").order_by("-appointment_date", "-start_time")

    return render(request, "patient/appointments_patient.html", {
        "appointments": appointments,
        "patient": patient,
    })

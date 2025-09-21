# clinic/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def role_required(roles=[]):
    """
    ใช้ตรวจสอบว่า user มี role ตามที่กำหนด
    เช่น @role_required(["admin", "patient"])
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role not in roles:
                messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

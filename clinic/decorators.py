# clinic/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def role_required(roles=[]):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.role not in roles:
                messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
                # redirect ตาม role
                if request.user.role == "admin":
                    return redirect("dashboard")
                elif request.user.role == "patient":
                    return redirect("patient_dashboard")
                else:
                    return redirect("login")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

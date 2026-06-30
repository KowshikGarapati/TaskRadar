from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import models
from django.db.models.functions import Cast

from .models import Task, User, PushSubscription
from .forms import TaskForm

import json
import random
import requests
import os

# Web Push
from pywebpush import webpush, WebPushException

# =========================
# TASK VIEWS
# =========================

def task_list(request):
    """Show all tasks for logged-in user"""
    tasks = Task.objects.filter(user_id=request.session.get("id")).values(
        "id", "title", "lat", "lon", "description", "date", "time",
        "is_completed", "location_notified", "time_notified", "is_expired"
    )
    return render(request, 'tasks.html', {
        "tasks_json": json.dumps(list(tasks), default=str), 
        "tasks": tasks,
    })


def newtask(request):
    """Create new task"""
    user = User.objects.get(id=request.session.get("id"))
    default_lat = user.default_latitude or 17.3850
    default_lon = user.default_longitude or 78.4867

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = user
            task.save()
            return redirect("task_list")
    else:
        form = TaskForm(initial={"lat": default_lat, "lon": default_lon})

    return render(request, 'newtask.html', {
        'form': form,
        'default_latitude': default_lat,
        'default_longitude': default_lon,
    })


def edit_task(request, task_id):
    """Edit existing task"""
    task = get_object_or_404(Task, id=task_id)
    user = User.objects.get(id=request.session.get("id"))
    default_lat = user.default_latitude or 17.3850
    default_lon = user.default_longitude or 78.4867

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task, initial={"lat": task.lat or default_lat, "lon": task.lon or default_lon})

    return render(request, 'edit_task.html', {
        'form': form,
        'default_latitude': default_lat,
        'default_longitude': default_lon,
    })


def delete_task(request, task_id):
    """Delete a task"""
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('task_list')


# =========================
# AUTH (BASIC - NOT SECURE)
# =========================

def signup(request):
    return render(request, "register.html")

def register(request):
    global newusername, newpassword, newemail
    newusername = request.GET.get("username")
    newpassword = request.GET.get("password")
    newconfirmpwd = request.GET.get("confirm password")
    newemail = request.GET.get("mail")
    if newpassword == newconfirmpwd:
        if newemail in User.objects.values_list('email', flat=True):
            return HttpResponse(b'email already exists')
        else:
            return redirect('send_verification_email', recipient=newemail)
        return redirect('/verify-email')
    signup_url = reverse('signup')
    return redirect(signup_url)

def login(request):
    return render(request, 'login.html')


def verify(request):
    """Simple login check (⚠ NOT secure, plain password)"""
    username = request.POST.get("username")
    password = request.POST.get("password")

    try:
        user = User.objects.get(name=username, password=password)
        request.session["id"] = user.id
        return redirect('/')
    except User.DoesNotExist:
        return redirect("login")


def logout(request):
    request.session.flush()
    return redirect("checkifuserloggedin")


def check_if_there_is_any_user_already_logged_in(request):
    """Redirect user based on login state"""
    if request.session.get("id"):
        return redirect("task_list")
    return redirect("login")


# =========================
# EMAIL VERIFICATION
# =========================

otpToBeChecked = None
newusername = None
newpassword = None
newemail = None


def send_verification_email(request, recipient):
    """Send OTP via email"""
    global otpToBeChecked
    otpToBeChecked = random.randint(10000, 99999)

    response = requests.post(
        "https://api.elasticemail.com/v2/email/send",
        data={
            'apikey': "YOUR_API_KEY",
            'subject': 'Verification Code',
            'from': 'your@email.com',
            'to': recipient,
            'bodyHtml': f'<h1>{otpToBeChecked}</h1>'
        }
    )

    print("Email sent" + str(otpToBeChecked) if response.status_code == 200 else "Email failed")
    return redirect('verify_otp')


def verifyotp(request):
    return render(request, "otpverification.html")


def emailverify(request):
    """Verify OTP and create user"""
    if request.GET.get("otp") == str(otpToBeChecked):
        user = User.objects.create(
            name=newusername,
            password=newpassword,
            email=newemail
        )
        request.session['id'] = user.id
        return redirect('task_list')

    return redirect('signup')


# =========================
# PUSH NOTIFICATION CONFIG
# =========================

VAPID_PRIVATE_KEY = "5UMfwX2ybkCYjwZxlVLvLhURiYPNwyeAIkI0BtwmYKU"
VAPID_PUBLIC_KEY = "BMov4lzyLO5ZFKs5uuCXHtmE0yo6Z7-cTpth3oQVrgWroh07h0lQM6neggYlc8AGd5vj0cunf_QwmB0Gqhgb44Q"


def gpstesting(request):
    """Page that initializes service worker & subscription"""
    return render(request, "GPSTest.html", {
        "vapid_public_key": VAPID_PUBLIC_KEY
    })


# =========================
# SAVE SUBSCRIPTION
# =========================

@csrf_exempt
def save_subscription(request):
    """
    Save subscription linked to logged-in user
    Flow:
    Browser → sends endpoint → stored with user
    """
    if request.method == "POST":
        data = json.loads(request.body)

        endpoint = data.get("endpoint")
        keys = data.get("keys", {})
        user_id = request.session.get("id")

        if not user_id:
            return JsonResponse({"error": "User not logged in"}, status=403)

        if endpoint and "auth" in keys and "p256dh" in keys:
            PushSubscription.objects.update_or_create(
                endpoint=endpoint,
                defaults={
                    "user_id": user_id,
                    "auth": keys["auth"],
                    "p256dh": keys["p256dh"]
                }
            )
            return JsonResponse({"status": "saved"})

        return JsonResponse({"error": "Invalid data"}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)


# =========================
# SEND NOTIFICATION
# =========================

def send_location_triggered_notification(request, task_id):
    user_id = request.session.get("id")

    if not user_id:
        return JsonResponse({"error": "Not logged in"}, status=403)

    task = get_object_or_404(Task, id=task_id)

    if task.user_id != user_id:
        return JsonResponse({"error": "Forbidden"}, status=403)

    subscriptions = PushSubscription.objects.filter(user_id=user_id)

    if not subscriptions.exists():
        return JsonResponse({"error": "No subscriptions"}, status=404)

    payload = {
        "title": task.title,
        "body": task.description,
        "icon": "/static/icons/notification.png"
    }

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": "mailto:your@email.com"
                }
            )
        except WebPushException as e:
            print(f"Push failed: {e}")

    task.location_notified = True
    task.save(update_fields=["location_notified"])

    return JsonResponse({"status": "Notification sent"})


def send_time_triggered_notification(request, task_id):
    user_id = request.session.get("id")

    if not user_id:
        return JsonResponse({"error": "Not logged in"}, status=403)

    task = get_object_or_404(Task, id=task_id)

    if task.user_id != user_id:
        return JsonResponse({"error": "Forbidden"}, status=403)

    payload = {
        "title": "⏰ Upcoming Task",
        "body": f"{task.title} starts soon!"
    }

    subscriptions = PushSubscription.objects.filter(user=task.user)

    for sub in subscriptions:

        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth
                }
            },

            data=json.dumps(payload),

            vapid_private_key=VAPID_PRIVATE_KEY,

            vapid_claims={
                "sub": "mailto:your@email.com"
            }
        )

    task.time_notified = True
    task.save(update_fields=["time_notified"])

    return JsonResponse({"status": "time notification sent"})

# =========================
# SERVICE WORKER
# =========================

def service_worker(request):
    """
    Serve service worker JS file
    IMPORTANT: Must be at root (/service-worker.js)
    """
    sw_path = os.path.join(settings.BASE_DIR, "routes/static/service-worker.js")
    return FileResponse(open(sw_path, "rb"), content_type="application/javascript")

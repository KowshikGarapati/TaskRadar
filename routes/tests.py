from unittest.mock import patch

from django.test import RequestFactory, TestCase

from .models import PushSubscription, Task, User
from .views import send_location_triggered_notification


class NotificationBehaviorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(name="owner", password="pwd", email="owner@example.com")
        self.other_user = User.objects.create(name="other", password="pwd", email="other@example.com")
        self.task = Task.objects.create(
            user=self.user,
            date="2030-01-01",
            time="10:00:00",
            title="Buy groceries",
            description="Near the task location",
            lat=17.3850,
            lon=78.4867,
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://example.test/endpoint",
            auth="auth-secret",
            p256dh="p256dh-secret",
        )

    def test_location_notification_marks_task_as_notified_for_owner(self):
        request = self.factory.post(f"/send_location_triggered_notification/{self.task.id}/")
        request.session = {"id": self.user.id}

        with patch("routes.views.webpush") as mock_webpush:
            response = send_location_triggered_notification(request, self.task.id)

        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.location_notified)
        mock_webpush.assert_called_once()

    def test_location_notification_rejects_task_owned_by_another_user(self):
        request = self.factory.post(f"/send_location_triggered_notification/{self.task.id}/")
        request.session = {"id": self.other_user.id}

        response = send_location_triggered_notification(request, self.task.id)

        self.assertEqual(response.status_code, 403)
        self.task.refresh_from_db()
        self.assertFalse(self.task.location_notified)

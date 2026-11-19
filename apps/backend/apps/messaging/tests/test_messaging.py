from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from PIL import Image

from apps.accounts.models import User
from apps.accounts.services import create_device_session
from apps.consultations.models import Appointment, ConsultationCase, ConsultationService
from apps.messaging.models import Message, RealtimeTicket
from apps.messaging.services import create_message, ensure_consultation_conversation, issue_ticket
from apps.private_media.models import StoredFile


class MessagingFixture:
    def build(self):
        self.user = User.objects.create_user("client@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.other = User.objects.create_user("other@example.com", "HairDoc!2026Strong", is_email_verified=True)
        self.tk = User.objects.create_user("tk@example.com", "HairDoc!2026Strong", is_email_verified=True, is_staff=True)
        service = ConsultationService.objects.create(
            name="Messaging consultation", slug=f"messaging-{uuid4()}", short_description="Talk to TK.",
            description="Talk to TK.", duration_minutes=30, price_amount="60", currency="GBP",
            status=ConsultationService.Status.PUBLISHED, published_at=timezone.now(), expert=self.tk,
        )
        case = ConsultationCase.objects.create(
            client=self.user, service=service, status=ConsultationCase.Status.PHOTOS_COMPLETE,
            timezone_snapshot="Europe/London", service_name=service.name, duration_minutes=30,
            price_amount="60", currency="GBP", intake_completed_at=timezone.now(), photos_completed_at=timezone.now(),
        )
        self.appointment = Appointment.objects.create(
            case=case, client=self.user, expert=self.tk, starts_at=timezone.now() + timedelta(days=2),
            ends_at=timezone.now() + timedelta(days=2, minutes=30), status=Appointment.Status.CONFIRMED,
            client_timezone="Europe/London", expert_timezone="Europe/London",
        )
        self.conversation = ensure_consultation_conversation(self.appointment)


class MessagingApiTests(MessagingFixture, APITestCase):
    def setUp(self):
        self.build(); self.authorize(self.user)

    def authorize(self, user):
        access, _, _ = create_device_session(user, "Messaging test")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_members_only_list_send_read_and_idempotency(self):
        listing = self.client.get(reverse("messaging:conversation-list"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["other_member_name"], "tk@example.com")
        message_id = uuid4()
        url = reverse("messaging:conversation-messages", kwargs={"public_id": self.conversation.public_id})
        first = self.client.post(url, {"body": "  Hello TK  ", "client_message_id": str(message_id)}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["body"], "Hello TK")
        self.assertEqual(self.client.post(url, {"body": "Hello TK", "client_message_id": str(message_id)}, format="json").status_code, 200)
        self.assertEqual(Message.objects.count(), 1)
        listing_with_message = self.client.get(reverse("messaging:conversation-list"))
        self.assertEqual(listing_with_message.status_code, 200)
        self.assertEqual(listing_with_message.json()[0]["last_message"]["body"], "Hello TK")
        self.assertEqual(self.client.post(reverse("messaging:conversation-read", kwargs={"public_id": self.conversation.public_id}), {"message_public_id": first.json()["public_id"]}, format="json").status_code, 200)

        self.authorize(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse("messaging:conversation-list")).json(), [])

    def test_new_empty_conversation_is_broadcast_to_both_cached_inboxes(self):
        self.conversation.delete()
        with patch("apps.messaging.services._broadcast_conversation_ready") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                conversation = ensure_consultation_conversation(self.appointment)
        broadcast.assert_called_once_with(conversation.pk)
        self.assertEqual(conversation.members.count(), 2)

    def test_history_is_cursor_paginated_and_ticket_is_hashed(self):
        for index in range(35):
            Message.objects.create(
                conversation=self.conversation, sender=self.tk, client_message_id=uuid4(), body=f"Message {index}",
            )
        history = self.client.get(reverse("messaging:conversation-messages", kwargs={"public_id": self.conversation.public_id}))
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["results"]), 30)
        self.assertIsNotNone(history.json()["next"])
        ticket = self.client.post(reverse("messaging:realtime-ticket"), {"conversation_public_id": str(self.conversation.public_id)}, format="json")
        self.assertEqual(ticket.status_code, 201)
        self.assertNotEqual(RealtimeTicket.objects.get().token_hash, ticket.json()["ticket"])
        inbox_ticket = self.client.post(reverse("messaging:realtime-ticket"), {}, format="json")
        self.assertEqual(inbox_ticket.status_code, 201)
        self.assertEqual(inbox_ticket.json()["websocket_path"], "/ws/v1/inbox/")
        self.assertTrue(RealtimeTicket.objects.filter(conversation__isnull=True).exists())

    def test_private_image_message_and_sent_read_states(self):
        content = BytesIO()
        Image.new("RGB", (640, 480), "purple").save(content, "PNG")
        upload = SimpleUploadedFile("private.png", content.getvalue(), content_type="image/png")
        url = reverse("messaging:conversation-messages", kwargs={"public_id": self.conversation.public_id})
        with TemporaryDirectory() as private_root, override_settings(PRIVATE_MEDIA_ROOT=private_root):
            sent = self.client.post(url, {
                "body": "", "client_message_id": str(uuid4()), "file": upload,
            }, format="multipart")
            self.assertEqual(sent.status_code, 201)
            self.assertEqual(sent.json()["status"], "SENT")
            self.assertEqual(sent.json()["attachment"]["content_type"], "image/jpeg")
            image = self.client.get(sent.json()["attachment"]["content_path"])
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image["Cache-Control"], "private, no-store, max-age=0")
            self.assertGreater(len(b"".join(image.streaming_content)), 0)

            self.authorize(self.tk)
            received = self.client.get(url).json()["results"][0]
            self.assertIsNotNone(received["attachment"])
            self.client.post(
                reverse("messaging:conversation-read", kwargs={"public_id": self.conversation.public_id}),
                {"message_public_id": sent.json()["public_id"]}, format="json",
            )
            self.authorize(self.user)
            self.assertEqual(self.client.get(url).json()["results"][0]["status"], "READ")
            delete_url = reverse("messaging:message-delete", kwargs={
                "public_id": self.conversation.public_id, "message_id": sent.json()["public_id"],
            })
            self.assertEqual(self.client.post(delete_url, {"mode": "everyone"}, format="json").status_code, 200)
            self.assertEqual(StoredFile.objects.count(), 0)
            self.assertEqual(self.client.get(sent.json()["attachment"]["content_path"]).status_code, 400)

    def test_reply_and_per_person_or_shared_deletion(self):
        url = reverse("messaging:conversation-messages", kwargs={"public_id": self.conversation.public_id})
        original = self.client.post(url, {"body": "Original context", "client_message_id": str(uuid4())}, format="json").json()
        self.authorize(self.tk)
        invalid = self.client.post(url, {"body": "No", "client_message_id": str(uuid4()), "reply_to_public_id": str(uuid4())}, format="json")
        self.assertEqual(invalid.status_code, 400)
        reply = self.client.post(url, {
            "body": "Reply to you", "client_message_id": str(uuid4()), "reply_to_public_id": original["public_id"],
        }, format="json")
        self.assertEqual(reply.status_code, 201)
        self.assertEqual(reply.json()["reply_to"]["body"], "Original context")
        delete_url = reverse("messaging:message-delete", kwargs={
            "public_id": self.conversation.public_id, "message_id": original["public_id"],
        })
        self.assertEqual(self.client.post(delete_url, {"mode": "everyone"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(delete_url, {"mode": "self"}, format="json").status_code, 200)
        self.assertEqual([item["body"] for item in self.client.get(url).json()["results"]], ["Reply to you"])
        self.authorize(self.user)
        self.assertEqual(len(self.client.get(url).json()["results"]), 2)
        self.assertEqual(self.client.post(delete_url, {"mode": "everyone"}, format="json").status_code, 200)
        tombstone = self.client.get(url).json()["results"][-1]
        self.assertTrue(tombstone["deleted_for_everyone"])
        self.assertEqual(tombstone["body"], "")
        self.assertTrue(self.client.get(url).json()["results"][0]["reply_to"]["deleted_for_everyone"])
        self.authorize(self.tk)
        self.assertTrue(self.client.get(url).json()["results"][0]["reply_to"]["deleted_for_everyone"])


class MessagingSocketTests(MessagingFixture, TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.build()

    def test_ticket_is_conversation_scoped_single_use_and_broadcasts_persisted_message(self):
        async_to_sync(self._exercise_socket)()

    def test_inbox_socket_receives_new_messages_without_polling(self):
        async_to_sync(self._exercise_inbox_socket)()

    def test_native_socket_without_origin_still_requires_a_ticket(self):
        async_to_sync(self._exercise_native_socket)()

    async def _exercise_native_socket(self):
        from channels.db import database_sync_to_async
        from config.asgi import application

        _, raw = await database_sync_to_async(issue_ticket)(self.user, None)
        socket = WebsocketCommunicator(application, f"/ws/v1/inbox/?ticket={raw}", headers=[])
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        self.assertEqual((await socket.receive_json_from())["type"], "realtime.ready")
        await socket.disconnect()
        reused = WebsocketCommunicator(application, f"/ws/v1/inbox/?ticket={raw}", headers=[])
        connected, code = await reused.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def _exercise_inbox_socket(self):
        from channels.db import database_sync_to_async
        from config.asgi import application

        _, raw = await database_sync_to_async(issue_ticket)(self.tk, None)
        headers = [(b"origin", b"http://testserver"), (b"host", b"testserver")]
        socket = WebsocketCommunicator(application, f"/ws/v1/inbox/?ticket={raw}", headers=headers)
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        self.assertEqual((await socket.receive_json_from())["type"], "realtime.ready")
        await database_sync_to_async(create_message)(self.conversation, self.user, "Hello TK", uuid4())
        notice = await socket.receive_json_from()
        self.assertEqual(notice["type"], "notification.created")
        self.assertEqual(notice["notification"]["route"], f"/messages/{self.conversation.public_id}")
        changed = await socket.receive_json_from()
        self.assertEqual(changed["type"], "inbox.changed")
        self.assertEqual(changed["conversation"]["public_id"], str(self.conversation.public_id))
        self.assertEqual(changed["conversation"]["last_message"]["body"], "Hello TK")
        self.assertEqual(changed["conversation"]["unread_count"], 1)
        def mark_notice_read():
            from apps.notifications.models import Notification
            from apps.notifications.services import broadcast_notifications_read

            item = Notification.objects.get(public_id=notice["notification"]["public_id"])
            item.read_at = timezone.now()
            item.save(update_fields=("read_at", "updated_at"))
            broadcast_notifications_read(self.tk, [item.public_id], item.read_at)
        await database_sync_to_async(mark_notice_read)()
        read_event = await socket.receive_json_from()
        self.assertEqual(read_event["type"], "notifications.read")
        self.assertEqual(read_event["notification_ids"], [notice["notification"]["public_id"]])
        self.assertEqual(read_event["unread_count"], 0)
        await socket.disconnect()

    async def _exercise_socket(self):
        from config.asgi import application
        from channels.db import database_sync_to_async

        ticket, raw = await database_sync_to_async(issue_ticket)(self.user, self.conversation)
        path = f"/ws/v1/conversations/{self.conversation.public_id}/?ticket={raw}"
        wrong = WebsocketCommunicator(application, f"/ws/v1/conversations/{uuid4()}/?ticket={raw}", headers=[(b"origin", b"http://testserver"), (b"host", b"testserver")])
        wrong_connected, wrong_code = await wrong.connect()
        self.assertFalse(wrong_connected)
        self.assertEqual(wrong_code, 4403)
        socket = WebsocketCommunicator(application, path, headers=[(b"origin", b"http://testserver"), (b"host", b"testserver")])
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        self.assertEqual((await socket.receive_json_from())["type"], "realtime.ready")
        _, tk_raw = await database_sync_to_async(issue_ticket)(self.tk, self.conversation)
        tk_socket = WebsocketCommunicator(
            application,
            f"/ws/v1/conversations/{self.conversation.public_id}/?ticket={tk_raw}",
            headers=[(b"origin", b"http://testserver"), (b"host", b"testserver")],
        )
        tk_connected, _ = await tk_socket.connect()
        self.assertTrue(tk_connected)
        self.assertEqual((await tk_socket.receive_json_from())["type"], "realtime.ready")
        tk_presence = await socket.receive_json_from()
        client_presence = await tk_socket.receive_json_from()
        self.assertEqual(tk_presence["type"], "conversation.presence")
        self.assertEqual(tk_presence["user_public_id"], str(self.tk.public_id))
        self.assertTrue(tk_presence["online"])
        self.assertEqual(client_presence["user_public_id"], str(self.user.public_id))
        self.assertTrue(client_presence["online"])
        await tk_socket.send_json_to({"type": "presence.inactive"})
        self.assertFalse((await socket.receive_json_from())["online"])
        await tk_socket.send_json_to({"type": "presence.active"})
        self.assertTrue((await socket.receive_json_from())["online"])
        await socket.send_json_to({"type": "typing.started"})
        typing = await socket.receive_json_from()
        peer_typing = await tk_socket.receive_json_from()
        self.assertEqual(typing["type"], "conversation.typing")
        self.assertEqual(typing["user_public_id"], str(self.user.public_id))
        self.assertTrue(typing["is_typing"])
        self.assertEqual(peer_typing["type"], "conversation.typing")
        self.assertTrue(peer_typing["is_typing"])
        socket_message_id = uuid4()
        await socket.send_json_to({
            "type": "message.send",
            "body": "Immediate over the socket",
            "client_message_id": str(socket_message_id),
        })
        socket_event = await socket.receive_json_from()
        peer_event = await tk_socket.receive_json_from()
        self.assertEqual(socket_event["type"], "message.created")
        self.assertEqual(socket_event["message"]["body"], "Immediate over the socket")
        self.assertEqual(socket_event["message"]["status"], "SENT")
        self.assertIsNone(socket_event["message"]["attachment"])
        self.assertTrue(
            await database_sync_to_async(Message.objects.filter(client_message_id=socket_message_id).exists)()
        )
        self.assertEqual(peer_event["message"]["client_message_id"], str(socket_message_id))
        await tk_socket.send_json_to({
            "type": "message.send", "body": "Socket reply", "client_message_id": str(uuid4()),
            "reply_to_public_id": str(socket_event["message"]["public_id"]),
        })
        self.assertEqual((await socket.receive_json_from())["message"]["reply_to"]["body"], "Immediate over the socket")
        self.assertEqual((await tk_socket.receive_json_from())["message"]["reply_to"]["body"], "Immediate over the socket")
        message, _ = await database_sync_to_async(create_message)(self.conversation, self.tk, "Persisted first", uuid4())
        event = await socket.receive_json_from()
        await tk_socket.receive_json_from()
        self.assertEqual(event["type"], "message.created")
        self.assertEqual(event["message"]["public_id"], str(message.public_id))
        await socket.disconnect()
        await tk_socket.disconnect()

        reused = WebsocketCommunicator(application, path, headers=[(b"origin", b"http://testserver"), (b"host", b"testserver")])
        connected_again, code = await reused.connect()
        self.assertFalse(connected_again)
        self.assertEqual(code, 4403)

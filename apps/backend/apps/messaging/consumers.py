from collections import deque
from urllib.parse import parse_qs
from time import monotonic
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .services import (
    MessagingError,
    consume_ticket,
    conversation_group,
    inbox_group,
    create_message,
    message_payload,
)


class ConversationConsumer(JsonWebsocketConsumer):
    def connect(self):
        conversation_id = self.scope["url_route"]["kwargs"]["public_id"]
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        ticket = consume_ticket(query.get("ticket", [""])[0], conversation_id)
        if not ticket:
            self.close(code=4403)
            return
        self.scope["user"] = ticket.user
        self.conversation = ticket.conversation
        self.group_name = conversation_group(self.conversation.public_id)
        self.last_typing_event_at = 0.0
        self.last_typing_state = False
        self.message_times = deque()
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self.send_json({"type": "realtime.ready", "conversation_public_id": str(self.conversation.public_id)})

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_send)(self.group_name, {
                "type": "conversation.typing",
                "user_public_id": str(self.scope["user"].public_id),
                "user_name": "",
                "is_typing": False,
            })
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            self.send_json({"type": "pong"})
        elif content.get("type") == "message.send":
            self._create_text_message(content)
        elif content.get("type") in {"typing.started", "typing.stopped"}:
            now = monotonic()
            is_typing = content["type"] == "typing.started"
            if is_typing == self.last_typing_state and now - self.last_typing_event_at < 0.25:
                return
            self.last_typing_event_at = now
            self.last_typing_state = is_typing
            async_to_sync(self.channel_layer.group_send)(self.group_name, {
                "type": "conversation.typing",
                "user_public_id": str(self.scope["user"].public_id),
                "user_name": (
                    f'{self.scope["user"].first_name} {self.scope["user"].last_name}'.strip()
                    or self.scope["user"].email
                ),
                "is_typing": is_typing,
            })
        else:
            self.send_json({"type": "error", "code": "UNSUPPORTED_EVENT"})

    def _create_text_message(self, content):
        client_message_id = str(content.get("client_message_id", ""))
        body = content.get("body")
        now = monotonic()
        while self.message_times and now - self.message_times[0] >= 60:
            self.message_times.popleft()
        if len(self.message_times) >= 30:
            self.send_json({
                "type": "message.rejected",
                "client_message_id": client_message_id,
                "code": "RATE_LIMITED",
            })
            return
        try:
            parsed_id = UUID(client_message_id)
            reply_to_id = UUID(content["reply_to_public_id"]) if content.get("reply_to_public_id") else None
            if not isinstance(body, str) or not body.strip() or len(body.strip()) > 4000:
                raise ValueError
        except (TypeError, ValueError, AttributeError):
            self.send_json({
                "type": "message.rejected",
                "client_message_id": client_message_id,
                "code": "INVALID_MESSAGE",
            })
            return
        self.message_times.append(now)
        try:
            message, created = create_message(
                self.conversation, self.scope["user"], body.strip(), parsed_id, reply_to_id=reply_to_id,
            )
        except MessagingError:
            self.send_json({
                "type": "message.rejected",
                "client_message_id": client_message_id,
                "code": "MESSAGE_NOT_ACCEPTED",
            })
            return
        # New messages are broadcast after commit. An idempotent retry has no
        # new commit, so acknowledge it directly to this socket.
        if not created:
            self.send_json({"type": "message.created", "message": message_payload(message)})

    def message_created(self, event):
        self.send_json({"type": "message.created", "message": event["message"]})

    def message_deleted(self, event):
        self.send_json({"type": "message.deleted", "message_public_id": event["message_public_id"]})

    def conversation_read(self, event):
        self.send_json({
            "type": "conversation.read", "user_public_id": event["user_public_id"],
            "message_public_id": event["message_public_id"],
        })

    def conversation_typing(self, event):
        self.send_json({
            "type": "conversation.typing",
            "user_public_id": event["user_public_id"],
            "user_name": event["user_name"],
            "is_typing": event["is_typing"],
        })


class InboxConsumer(JsonWebsocketConsumer):
    def connect(self):
        query = parse_qs(self.scope.get("query_string", b"").decode("utf-8"))
        ticket = consume_ticket(query.get("ticket", [""])[0])
        if not ticket:
            self.close(code=4403)
            return
        self.group_name = inbox_group(ticket.user.public_id)
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self.send_json({"type": "realtime.ready"})

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            self.send_json({"type": "pong"})

    def inbox_changed(self, event):
        self.send_json({"type": "inbox.changed", "conversation": event["conversation"]})

    def notification_created(self, event):
        self.send_json({"type": "notification.created", "notification": event["notification"]})

    def notifications_read(self, event):
        self.send_json({
            "type": "notifications.read",
            "notification_ids": event["notification_ids"],
            "read_at": event["read_at"],
            "unread_count": event["unread_count"],
        })

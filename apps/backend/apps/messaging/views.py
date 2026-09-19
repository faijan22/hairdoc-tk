from django.db.models import Prefetch
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.private_media.storage import get_storage_provider
from apps.notifications.services import broadcast_notifications_read

from .models import Conversation, ConversationMember, Message, MessageAttachmentAccess
from .pagination import MessageCursorPagination
from .serializers import (
    ConversationSerializer, MessageCreateSerializer, MessageSerializer, ReadSerializer, TicketSerializer,
)
from .services import (
    MessagingError, broadcast_read, create_message, delete_message_for_everyone,
    hide_message_for_user, issue_ticket, resolve_attachment_access,
)


def _conversation(request, public_id):
    return get_object_or_404(
        Conversation.objects.select_related("consultation").prefetch_related("members__user"),
        public_id=public_id, members__user=request.user,
    )


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(members__user=request.user).select_related(
            "consultation",
        ).prefetch_related(
            "members__user", "members__last_read_message",
            Prefetch(
                "messages",
                queryset=Message.objects.exclude(hidden_by__user=request.user).select_related(
                    "sender", "reply_to__sender", "reply_to__attachment",
                ).order_by("-created_at", "-id")[:1],
                to_attr="latest_messages",
            ),
        ).distinct()[:50]
        return Response(ConversationSerializer(conversations, many=True, context={"request": request}).data)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, public_id):
        return Response(ConversationSerializer(_conversation(request, public_id), context={"request": request}).data)


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "message_send"
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request, public_id):
        conversation = _conversation(request, public_id)
        paginator = MessageCursorPagination()
        page = paginator.paginate_queryset(
            conversation.messages.exclude(hidden_by__user=request.user).select_related(
                "sender", "reply_to__sender", "reply_to__attachment",
            ), request, view=self,
        )
        return paginator.get_paginated_response(MessageSerializer(page, many=True, context={"viewer": request.user}).data)

    def post(self, request, public_id):
        conversation = _conversation(request, public_id)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message, created = create_message(conversation, request.user, **serializer.validated_data)
        except MessagingError as exc:
            raise ValidationError(exc.details) from None
        message = Message.objects.select_related("sender", "conversation", "attachment__stored_file", "reply_to__sender", "reply_to__attachment").prefetch_related(
            "conversation__members__last_read_message",
        ).get(pk=message.pk)
        return Response(MessageSerializer(message, context={"viewer": request.user}).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id, message_id):
        conversation = _conversation(request, public_id)
        message = get_object_or_404(Message.objects.select_related("sender", "conversation"), conversation=conversation, public_id=message_id)
        mode = request.data.get("mode")
        try:
            if mode == "self":
                hide_message_for_user(conversation, request.user, message)
                return Response({"mode": "self", "message_public_id": str(message.public_id)})
            if mode == "everyone":
                delete_message_for_everyone(conversation, request.user, message)
                return Response({"mode": "everyone", "message_public_id": str(message.public_id)})
        except MessagingError as exc:
            raise ValidationError(exc.details) from None
        raise ValidationError({"mode": ["Choose self or everyone."]})


class PrivateMessageImageView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, attachment_id):
        try:
            attachment, viewer = resolve_attachment_access(request.query_params.get("token", ""))
        except MessagingError as exc:
            raise ValidationError(exc.details) from None
        if attachment.public_id != attachment_id:
            raise ValidationError({"token": ["This private image link does not match the requested image."]})
        MessageAttachmentAccess.objects.create(
            attachment=attachment, actor=viewer, request_id=getattr(request, "request_id", ""),
        )
        try:
            content = get_storage_provider().open(attachment.stored_file.storage_key)
        except FileNotFoundError:
            raise ValidationError({"attachment": ["This private image is unavailable."]}) from None
        response = FileResponse(content, content_type=attachment.stored_file.content_type)
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Content-Disposition"] = f'inline; filename="{attachment.public_id}.jpg"'
        response["X-Content-Type-Options"] = "nosniff"
        return response


class ConversationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, public_id):
        conversation = _conversation(request, public_id)
        serializer = ReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message_id = serializer.validated_data.get("message_public_id")
        message = get_object_or_404(
            Message, conversation=conversation,
            **({"public_id": message_id} if message_id else {}),
        ) if message_id else conversation.messages.first()
        membership = ConversationMember.objects.get(conversation=conversation, user=request.user)
        if message and (not membership.last_read_message or message.created_at > membership.last_read_message.created_at):
            membership.last_read_message = message
            membership.save(update_fields=("last_read_message", "updated_at"))
            unread_notifications = request.user.notifications.filter(
                conversation=conversation, read_at__isnull=True, message__created_at__lte=message.created_at,
            )
            read_ids = list(unread_notifications.values_list("public_id", flat=True))
            if read_ids:
                unread_notifications.update(read_at=message.created_at, updated_at=message.created_at)
                broadcast_notifications_read(request.user, read_ids, message.created_at)
            broadcast_read(conversation, request.user.public_id, message.public_id)
        return Response({"read_through": str(message.public_id) if message else None})


class RealtimeTicketView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "realtime_ticket"

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation_id = serializer.validated_data.get("conversation_public_id")
        conversation = _conversation(request, conversation_id) if conversation_id else None
        try:
            ticket, raw = issue_ticket(request.user, conversation)
        except MessagingError as exc:
            raise ValidationError(exc.details) from None
        return Response({
            "ticket": raw, "expires_at": ticket.expires_at,
            "websocket_path": f"/ws/v1/conversations/{conversation.public_id}/" if conversation else "/ws/v1/inbox/",
        }, status=status.HTTP_201_CREATED)

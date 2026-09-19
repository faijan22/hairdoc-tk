from django.urls import path

from .views import (
    ConversationDetailView, ConversationListView, ConversationMessagesView, ConversationReadView,
    MessageDeleteView, PrivateMessageImageView, RealtimeTicketView,
)

app_name = "messaging"

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/<uuid:public_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<uuid:public_id>/messages/", ConversationMessagesView.as_view(), name="conversation-messages"),
    path("conversations/<uuid:public_id>/messages/<uuid:message_id>/delete/", MessageDeleteView.as_view(), name="message-delete"),
    path("conversations/<uuid:public_id>/read/", ConversationReadView.as_view(), name="conversation-read"),
    path("realtime/ticket/", RealtimeTicketView.as_view(), name="realtime-ticket"),
    path("private-files/message-images/<uuid:attachment_id>/", PrivateMessageImageView.as_view(), name="message-image"),
]

from django.urls import re_path

from .consumers import ConversationConsumer, InboxConsumer

websocket_urlpatterns = [
    re_path(r"^ws/v1/inbox/$", InboxConsumer.as_asgi()),
    re_path(r"^ws/v1/conversations/(?P<public_id>[0-9a-f-]+)/$", ConversationConsumer.as_asgi()),
]

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .selectors import published_content
from .serializers import ContentItemDetailSerializer, ContentItemListSerializer


class ContentItemListView(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ContentItemListSerializer

    def get_queryset(self):
        return published_content()


class ContentItemDetailView(RetrieveAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = ContentItemDetailSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        return published_content()


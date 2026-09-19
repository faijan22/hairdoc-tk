from .base import VideoProviderError


class DisabledVideoProvider:
    code = "DISABLED"

    @property
    def is_configured(self):
        return False

    def create_room(self, **kwargs):
        raise VideoProviderError("In-app video is not enabled.")

    def issue_join_grant(self, **kwargs):
        raise VideoProviderError("In-app video is not enabled.")

    def close_room(self, **kwargs):
        return None

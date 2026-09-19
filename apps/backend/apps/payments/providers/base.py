from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CheckoutSession:
    session_id: str
    order_id: str
    url: str
    expires_at: datetime


class PaymentProviderConfigurationError(Exception):
    pass


class PaymentProvider(Protocol):
    code: str

    def create_checkout(self, *, order, attempt, return_base_url: str) -> CheckoutSession: ...

    def parse_webhook(self, payload: bytes, signature: str) -> dict: ...

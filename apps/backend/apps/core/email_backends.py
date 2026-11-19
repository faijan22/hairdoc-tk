import json
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ElasticEmailAPIError(RuntimeError):
    pass


class ElasticEmailBackend(BaseEmailBackend):
    """Django email backend for Elastic Email's transactional REST API v4."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                self._send(message)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent

    def _send(self, message):
        if not settings.ELASTIC_EMAIL_API_KEY:
            raise ElasticEmailAPIError("Elastic Email API key is not configured.")
        if message.attachments:
            raise ElasticEmailAPIError("Elastic Email attachments are not supported by this backend yet.")

        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        from_name, from_address = parseaddr(from_email)
        if not from_address:
            raise ElasticEmailAPIError("A verified sender email is required.")

        body = [{
            "ContentType": "PlainText",
            "Charset": message.encoding or settings.DEFAULT_CHARSET,
            "Content": message.body,
        }]
        for alternative in getattr(message, "alternatives", ()):
            content = getattr(alternative, "content", alternative[0])
            mimetype = getattr(alternative, "mimetype", alternative[1])
            if mimetype == "text/html":
                body.append({
                    "ContentType": "HTML",
                    "Charset": message.encoding or settings.DEFAULT_CHARSET,
                    "Content": content,
                })

        content = {
            "From": from_address,
            "Subject": message.subject,
            "Body": body,
        }
        if from_name:
            content["FromName"] = from_name
        payload = {
            "Recipients": {
                "To": list(message.to),
                "CC": list(message.cc),
                "BCC": list(message.bcc),
            },
            "Content": content,
        }
        idempotency_key = message.extra_headers.get("Idempotency-Key") or str(uuid4())
        request = Request(
            f"{settings.ELASTIC_EMAIL_API_BASE_URL.rstrip('/')}/emails/transactional",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-ElasticEmail-ApiKey": settings.ELASTIC_EMAIL_API_KEY,
                "Idempotency-Key": str(idempotency_key)[:255],
            },
        )
        try:
            with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:  # noqa: S310 - fixed HTTPS API
                result = json.loads(response.read() or b"{}")
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ElasticEmailAPIError("Elastic Email rejected or could not receive this email.") from exc
        if not result.get("TransactionID") or not result.get("MessageID"):
            raise ElasticEmailAPIError("Elastic Email returned an incomplete response.")

from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    request_id = getattr(request, "request_id", None)
    code = getattr(exc, "default_code", "request_error")
    message = "The request could not be completed."

    if isinstance(response.data, dict) and "detail" in response.data:
        detail = response.data["detail"]
        message = str(detail)
        code = getattr(detail, "code", code)

    response.data = {
        "error": {
            "code": str(code).upper(),
            "message": message,
            "details": response.data,
            "request_id": request_id,
        }
    }
    return response


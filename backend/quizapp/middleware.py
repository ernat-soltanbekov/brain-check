from django.conf import settings
from django.http import JsonResponse


class RequestSizeMiddleware:
    """Reject oversized declared bodies before Django or a multipart parser reads them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            try:
                size = int(request.META.get("CONTENT_LENGTH") or 0)
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Invalid Content-Length."}, status=400)
            if size < 0:
                return JsonResponse({"detail": "Invalid Content-Length."}, status=400)
            if size > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
                return JsonResponse({"detail": "Request exceeds the 1 MB limit."}, status=413)
        return self.get_response(request)

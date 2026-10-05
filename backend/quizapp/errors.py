from django.core.exceptions import RequestDataTooBig
from django.db import OperationalError
from django.http import UnreadablePostError
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


class Conflict(APIException):
    status_code = 409
    default_detail = "This quiz changed. Reload before continuing."


class Unavailable(APIException):
    status_code = 503
    default_detail = "The service is busy. Retry with the same submission key."


def exception_handler(exc, context):
    if isinstance(exc, OperationalError):
        return Response(
            {"detail": "Database temporarily busy. Retry your request."},
            status=503,
            headers={"Retry-After": "2"},
        )
    if isinstance(exc, (RequestDataTooBig, UnreadablePostError)):
        return Response({"detail": "Request is too large or could not be read."}, status=413)
    return drf_handler(exc, context)

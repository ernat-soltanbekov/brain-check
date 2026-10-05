"""Bound JSON reads before parsing; field validation alone happens too late."""

from io import BytesIO

from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.parsers import JSONParser


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = "Request exceeds the 1 MB limit."


class BoundedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        body = stream.read(settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)
        if len(body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            raise PayloadTooLarge()
        return super().parse(BytesIO(body), media_type, parser_context)

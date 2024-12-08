"""Модуль дополнительными утилитами."""
import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """Сериализатор для обработки передамаваемых  изображений."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


def get_request_or_user(context, value=None):
    """Проверка на наличие request и user в контексте."""
    if 'request' not in context:
        return None
    request = context['request']
    if not value:
        return request
    if not hasattr(request, 'user') or request.user.is_anonymous:
        return None
    return request.user


def get_request_attribute(context, attribute=None):
    """Проверка на наличие request, user и доп. атрибута в контексте."""
    if 'request' not in context:
        return None
    request = context['request']
    if attribute == 'user':
        if not hasattr(request, 'user') or request.user.is_anonymous:
            return None
        return request.user
    attribute = request.query_params.get(attribute)
    if not attribute:
        return None
    return attribute

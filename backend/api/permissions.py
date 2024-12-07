"""Модуль с кастомными доступами к данным."""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrAdminOrReadOnly(BasePermission):
    """
    Кастомный доступ к изменению/удалению контента.

    Только для Администратора или Автора или на чтение
    для неавторизованных пользователей.
    """

    message = 'У вас недостаточно прав для выполнения этого действия.'

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in SAFE_METHODS
            or (
                request.user.is_authenticated
                and (
                    request.user.is_superuser
                    or obj.author == request.user
                )
            )
        )

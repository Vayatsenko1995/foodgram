from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrAdminOrReadOnly(BasePermission):
    """Кастомный пермишен доступ к изменению/удалению контента
    только для Администратора или Автора или на чтение
    для неавторизованных пользователей."""

    def has_permission(self, request, view):

        return (
            request.method in SAFE_METHODS or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):

        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and (
            request.user.is_superuser
            or obj.author == request.user
        )

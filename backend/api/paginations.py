"""Модуль с кастомными пагинациями проекта."""
from rest_framework.pagination import PageNumberPagination

PAGE_SIZE = 10


class LimitPageNumberPaginator(PageNumberPagination):
    """Настройки пагинатора."""

    page_size = PAGE_SIZE
    page_size_query_param = 'limit'

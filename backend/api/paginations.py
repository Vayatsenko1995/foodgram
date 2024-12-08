"""Модуль с кастомными пагинациями проекта."""
from rest_framework.pagination import PageNumberPagination
from foodgram_backend.settings import PAGE_SIZE


class LimitPageNumberPaginator(PageNumberPagination):
    """Настройки пагинатора."""

    page_size = PAGE_SIZE
    page_size_query_param = 'limit'

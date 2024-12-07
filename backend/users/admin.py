"""Модуль админ зоны users."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Follow


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'id', 'email', 'first_name', 'last_name')
    list_filter = ('email', 'first_name')
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name'
    )


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'following')
    search_fields = (
        'user__username', 'following__username',
        'user__last_name', 'following__last_name',
        'user__first_name', 'following__first_name',
        'user__email', 'following__email',
    )
    list_filter = ('user', 'following')

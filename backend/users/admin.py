"""Модуль админ зоны users."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AbstractUser, CustomUser


@admin.register(AbstractUser)
class UserAdmin(UserAdmin):
    list_display = ('username', 'id', 'email', 'first_name', 'last_name')
    list_filter = ('email', 'first_name')


@admin.register(CustomUser)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')

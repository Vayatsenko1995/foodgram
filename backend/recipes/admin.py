"""Модуль с настройками админ зоны."""
from django.contrib import admin
from django.contrib.admin import display

from .models import (
    Favorite, Ingredient,
    RecipeIngredient, Recipe,
    ShoppingCart, Tag,
    RecipeShortLink
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'author', 'added_in_favorites')
    readonly_fields = ('added_in_favorites',)
    list_filter = ('tags',)
    search_fields = (
        'author__email',
        'author__last_name',
        'author__first_name',
        'author__username',
        'name',
    )

    @display(description='Количество в избранных')
    def added_in_favorites(self, obj):
        return obj.favorites.count()


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = (
        'user__username',
        'user__last_name',
        'user__first_name',
        'user__email',
        'recipe__name',
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = (
        'user__username',
        'user__last_name',
        'user__first_name',
        'user__email',
        'recipe__name',
    )


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'get_amount_with_unit',)
    search_fields = (
        'recipe__name',
        'ingredient__name',
    )


@admin.register(RecipeShortLink)
class RecipeShortLinkAdmin(admin.ModelAdmin):
    list_display = ('short_link', 'original_url')
    search_fields = ('short_link', 'original_url')

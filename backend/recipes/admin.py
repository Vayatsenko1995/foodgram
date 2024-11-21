from django.contrib import admin

from .models import Ingredient, Tag, Recipe

# Register your models here.
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["name", "measurement_unit"]
    search_fields = ("name",)


class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]


class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        "author",
        "name",
        "text",
        # "ingredients",
        # "tags",
        "cooking_time",
    ]


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)

from django_filters.rest_framework import FilterSet, filters
from rest_framework.pagination import PageNumberPagination

from recipes.models import Ingredient, Recipe, Tag
from users.models import CustomUser


class RecipeFilter(FilterSet):
    """Фильтр для вьюсета вывода Рецептов."""
    author = filters.NumberFilter()
    is_favorited = filters.BooleanFilter(method='get_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='get_is_in_shopping_cart')
    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags'
        )

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset


class IngredientFilter(FilterSet):
    """Фильтр для вьюсета выбора Ингредиентов."""
    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class CustomLimitPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    max_page_size = 100  # Максимальное количество элементов, которое можно запросить

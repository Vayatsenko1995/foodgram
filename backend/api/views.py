from datetime import datetime

from django.http import JsonResponse, HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from rest_framework import status, viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.reverse import reverse

from djoser.views import UserViewSet
from django_filters import rest_framework as rest_filters

from users.models import CustomUser, Follow
from recipes.models import (
    Ingredient, Tag, Recipe, ShoppingCart, Favorite, RecipeIngredient
)
from .serializers import (
    RecipeSerializer,
    RecipePostUpdateSerializer,
    IngredientSerializer, TagSerializer,
    ShoppingCartSerializer,
    FavoriteSerializer,
    FollowSerializer, AvatarSerializer,
)
from .permissions import IsAuthorOrAdminOrReadOnly
from .filters import IngredientFilter, RecipeFilter
from .utils import add_or_delete_model


class CustomUserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(IsAuthenticated,),
        url_name='me',
    )
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=False, methods=['put'], url_path='me/avatar',
            permission_classes=[IsAuthorOrAdminOrReadOnly])
    def avatar(self, request, *args, **kwargs):
        """Добавление-обновление аватара пользователя."""
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)

        if not request.data.get('avatar'):
            return Response(
                {'detail': 'Поле avatar обязательно.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @avatar.mapping.delete
    def delete_avatar(self, request, *args, **kwargs):
        """Удаление аватара пользователя."""
        user = request.user
        if user.avatar:
            user.avatar.delete() 
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Аватар отсутствует.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['GET'], url_path='subscriptions',
        permission_classes=[IsAuthenticated],
    )
    def get_subscriptions(self, request):
        """Просмотр листа подписок пользователя."""
        user = request.user
        following = Follow.objects.filter(user=user)
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = FollowSerializer(
                instance=page,
                context={'request': request},
                many=True
            )
            return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=['POST'], url_path='subscribe',
        permission_classes=[IsAuthenticated]
    )
    def get_subscribe(self, request, id=None):
        """Подписка на автора."""
        user = request.user
        following = get_object_or_404(CustomUser, pk=id)

        if user == following:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(user=user, following=following).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FollowSerializer(
            data={'following': following},
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save(
                user=request.user,
                following=following,
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @get_subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        """Отписка от автора."""
        follower = request.user
        following = get_object_or_404(CustomUser, pk=id)
        subscription = Follow.objects.filter(
            user=follower, following=following)
        if not subscription.exists():
            return Response({'detail': 'Вы не подписаны на этого автора.'},
                            status=status.HTTP_400_BAD_REQUEST)
        del_count, _ = subscription.delete()
        if del_count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Ошибка удаления подписки.'},
                        status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Описание логики работы АПИ для эндпоинта Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (AllowAny,)
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Описание логики работы АПИ для эндпоинта Tag."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class RecipeViewSet(viewsets.ModelViewSet):
    """Описание логики работы АПИ для эндпоинта Recipe."""
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """Получение сериализатора для работы с Рецептами."""

        if self.request.method == 'GET':
            return RecipeSerializer
        return RecipePostUpdateSerializer

    def perform_update(self, serializer):
        """Проверка доступа перед обновлением рецепта."""
        recipe = self.get_object()
        # Проверяем, является ли пользователь автором рецепта
        if recipe.author != self.request.user:
            raise PermissionDenied(
                "У вас нет прав для изменения этого рецепта."
            )
        serializer.save()

    def perform_create(self, serializer):
        """Подстановка текущего пользователя в авторы рецепта."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='shopping_cart',
        permission_classes=(IsAuthorOrAdminOrReadOnly,)
    )
    def shopping_cart(self, request, pk=None):
        model_name = ShoppingCart
        serializer_name = ShoppingCartSerializer
        return add_or_delete_model(request, model_name, serializer_name, pk)

    @action(methods=['get'], detail=False, url_name='download',)
    def download_shopping_cart(self, request):
        """
        Подготавливает и возвращает файл со списком покупок.
        """
        user = request.user

        ingredients = (
            RecipeIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum('amount'))
        )

        if not ingredients:
            return HttpResponse(
                'Ваш список покупок пуст.', content_type='text/plain'
            )

        today = datetime.today()
        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
            f'Дата: {today:%Y-%m-%d}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        shopping_list += f'\n\nFoodgram ({today:%Y})'

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=(IsAuthorOrAdminOrReadOnly,)
    )
    def favorite(self, request, pk=None):
        serializer_name = FavoriteSerializer
        model_name = Favorite
        return add_or_delete_model(request, model_name, serializer_name, pk)

    @action(
        methods=['get'], detail=True, url_path='get-link', url_name='get_link'
    )
    def get_link_short(self, request, pk=None):
        """View функция, возвращающая короткую постоянную ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)

        short_link = request.build_absolute_uri(
            reverse('recipe_by_short_link', args=(recipe.short_link,))
        )

        return JsonResponse({'short-link': short_link})

    def recipe_by_short_link(self, request, short_link=None):
        """View функция, для открытия информации о рецепте по короткой ссылке."""
        recipe_id = get_object_or_404(
            Recipe, short_link=short_link
        ).id

        url = reverse('api:recipes-detail', kwargs={'pk': recipe_id})
        original_url = request.build_absolute_uri(url)

        return redirect(original_url)

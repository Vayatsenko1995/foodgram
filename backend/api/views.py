"""Модуль с основными views."""
from datetime import datetime
import uuid

from django.http import HttpResponse
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from rest_framework import status, viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.reverse import reverse
from rest_framework.filters import SearchFilter
from djoser.views import UserViewSet
from django_filters import rest_framework as rest_filters

from users.models import CustomUser, Follow
from recipes.models import (
    Ingredient, Tag, Recipe, ShoppingCart, Favorite, RecipeIngredient,
    RecipeShortLink
)
from .paginations import LimitPageNumberPaginator
from .serializers import (
    RecipeSerializer, ShortLinkSerializer,
    RecipePostUpdateSerializer,
    IngredientSerializer, TagSerializer,
    ShoppingCartSerializer,
    FavoriteSerializer,
    FollowSerializer, AvatarSerializer,
)
from .permissions import IsAuthorOrAdminOrReadOnly
from .filters import (
    RecipeFilter,
)


class CustomUserViewSet(UserViewSet):
    """Кастомный ViewSet на основе djoser."""

    queryset = CustomUser.objects.all()
    pagination_class = LimitPageNumberPaginator

    def get_serializer_class(self):
        if self.action == 'avatar':
            return AvatarSerializer
        elif self.action in ['get_subscriptions', 'post_subscribe']:
            return FollowSerializer
        return super().get_serializer_class()

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
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request, *args, **kwargs):
        """Удаление аватара пользователя."""
        user = request.user
        if user.avatar:
            user.avatar.delete()
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'], url_path='subscriptions',
        permission_classes=[IsAuthenticated],
    )
    def get_subscriptions(self, request):
        """Просмотр листа подписок пользователя."""
        user = request.user
        following = Follow.objects.filter(
            user=user
        ).prefetch_related('following').order_by('id')
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = self.get_serializer(
                instance=page,
                context={'request': request},
                many=True
            )
            return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=['POST'], url_path='subscribe',
        permission_classes=[IsAuthenticated]
    )
    def post_subscribe(self, request, id=None):
        """Подписка на автора."""
        following = get_object_or_404(CustomUser, pk=id)
        serializer = self.get_serializer(
            data={
                'user': request.user.id,
                'following': following.id
            },
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @post_subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        """Отписка от автора."""
        follower = request.user
        following = get_object_or_404(CustomUser, pk=id)
        subscription = Follow.objects.filter(
            user=follower, following=following
        ).prefetch_related('following').order_by('id')
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
    filter_backends = (rest_filters.DjangoFilterBackend,
                       SearchFilter)
    search_fields = ('^name',)


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
    pagination_class = LimitPageNumberPaginator
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter

    def get_queryset(self):
        # C queryset не очень понял, надеюсь я всё таки верный вывод
        return self.queryset.select_related('author').prefetch_related(
            'ingredients', 'tags'
        ).order_by('-pub_date')

    def get_serializer_class(self):
        """Получение сериализатора для работы с Рецептами."""
        if self.action == 'favorite':
            return FavoriteSerializer
        elif self.action == 'shopping_cart':
            return ShoppingCartSerializer
        elif self.action in ['list', 'retrieve']:
            return RecipeSerializer
        return RecipePostUpdateSerializer

    def add_model(self, model, serializer, pk=None):
        """Вспомогательная функция для обавление модели."""
        request = self.request
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = serializer(
            data={
                'recipe': pk,
                'user': request.user.id,
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, recipe=recipe,)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_model(self, model, pk=None):
        """Вспомогательная функция для удаление модели."""
        recipe = get_object_or_404(Recipe, pk=pk)
        request = self.request
        data = model.objects.filter(
            user=request.user,
            recipe=recipe
        )
        deleted_count, _ = data.delete()
        if not deleted_count:
            return Response(
                {'error': 'Рецепт в списке не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """Подстановка текущего пользователя в авторы рецепта."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
        permission_classes=(IsAuthorOrAdminOrReadOnly,)
    )
    def shopping_cart(self, request, pk=None):
        model_name = ShoppingCart
        return self.add_model(model_name, self.get_serializer, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        model_name = ShoppingCart
        return self.delete_model(model_name, pk)

    @action(methods=['get'], detail=False, url_name='download',)
    def download_shopping_cart(self, request):
        """Подготавливает и возвращает файл со списком покупок."""
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
        methods=['post'],
        url_path='favorite',
        permission_classes=(IsAuthorOrAdminOrReadOnly,)
    )
    def favorite(self, request, pk=None):
        model_name = Favorite
        return self.add_model(model_name, self.get_serializer, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        model_name = Favorite
        return self.delete_model(model_name, pk)

    @action(
        methods=['get'], detail=True, url_path='get-link', url_name='get_link'
    )
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        self.get_object()
        original_url = request.META.get('HTTP_REFERER')
        if original_url is None:
            url = reverse('api:recipes-detail', kwargs={'pk': pk})
            original_url = request.build_absolute_uri(url)

        short_link_instance, _ = RecipeShortLink.objects.get_or_create(
            original_url=original_url,
            defaults={'short_link': str(uuid.uuid4())[:3]}
        )
        serializer = ShortLinkSerializer(
            short_link_instance,
            context={'request': request},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve_by_short_link(self, request, short_link=None):
        """Получение рецепта по короткой ссылке."""
        recipe = get_object_or_404(
            RecipeShortLink, short_link=short_link
        ).original_url
        return redirect(recipe)

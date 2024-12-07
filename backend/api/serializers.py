"""Модуль с сериализаторами проекта."""
from django.core.validators import MinValueValidator
from rest_framework import exceptions, serializers
from rest_framework.reverse import reverse
from djoser.serializers import UserSerializer

from users.models import CustomUser, Follow
from recipes.models import (
    Recipe, RecipeIngredient, Ingredient,
    Tag, Favorite, ShoppingCart,
    RecipeShortLink
)
from .utils import Base64ImageField, get_request_user


class CustomUserReadSerializer(UserSerializer):
    """Сериализатор для чтения пользовательских данных."""

    email = serializers.CharField(max_length=254, required=True)
    username = serializers.CharField(max_length=150, required=True)
    is_subscribed = serializers.SerializerMethodField(
        read_only=True,
    )
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        # fields = UserSerializer.Meta.fields + ('is_subscribed', 'avatar',)
        # Менять fields не вижу смысла, т.к. тогда ответ на api запрос
        # перестаёт соотвествовать необходимому по спецификации ТЗ. Можно
        # дописать конечно метод to_representation и переопределить fields,
        # но мне кажется это не целесообразным в данной ситуации и проще
        # сразу прописать необходимый fields.
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = ('id', 'is_subscribed', 'avatar',)

    def get_is_subscribed(self, obj):
        """Подписан ли пользователь на автора."""
        user = get_request_user(self.context)
        if user is None:
            return False
        return Follow.objects.filter(user=user, following=obj).exists()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Tag."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientGetSerializer(serializers.ModelSerializer):
    """Сериализатор для модели RecipeIngredient."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe. Чтение."""

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserReadSerializer(read_only=True)
    ingredients = IngredientGetSerializer(
        source='recipeingredients',
        many=True
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time',)

    def get_is_favorited(self, obj):
        """Добавлен ли рецепт в Избранное."""
        user = get_request_user(self.context)
        if user is None:
            return False
        return (
            Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Добавлен ли рецепт в список Покупок."""
        user = get_request_user(self.context)
        if user is None:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для представления данных о рецепте."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Favorite и ShoppingCart."""
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов при создании рецепта."""

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'Количество должно быть равным или больше 1!'
        }
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipePostUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe. Создание, Обновление."""

    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    cooking_time = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'Время приготовления должно быть больше нуля!'
        }
    )
    image = Base64ImageField()
    author = CustomUserReadSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'author',
                  'image', 'name',
                  'text', 'cooking_time')

    def validate_ingredients(self, value):
        ingredient_ids = [item['id'] for item in value]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться!'
            )

        # Убедимся, что все указанные ингредиенты существуют
        if not Ingredient.objects.filter(id__in=ingredient_ids).count() == len(ingredient_ids):
            raise serializers.ValidationError(
                'Некоторые ингредиенты не найдены в базе данных'
            )

        return value

    def validate_tags(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Тэги не должны повторяться!')

        return value

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if ingredients is None or len(ingredients) == 0:
            raise exceptions.ValidationError(
                'В рецепт не добавлены ингредиенты'
            )

        if tags is None or len(tags) == 0:
            raise serializers.ValidationError({
                'tags': 'Тэги не должны быть пустыми!'
            })

        return data

    def add_ingredient_tag(self, ingredients, tags, recipe):
        """Добавление ингр-ов и тэгов в рецепт при создании и ред-нии."""
        for tag in tags:
            recipe.tags.add(tag)
            recipe.save()
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'],
                amount=ingredient['amount'], )
            for ingredient in ingredients
        ])
        return recipe

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        return self.add_ingredient_tag(ingredients, tags, recipe)

    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()

        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        super().update(instance, validated_data)
        return self.add_ingredient_tag(ingredients, tags, instance)

    def to_representation(self, value):
        """Выбор сериализатора для вывода результата работы класса."""
        serializer = RecipeSerializer(value, context=self.context)
        return serializer.data


class ShoppingCartSerializer(ShortRecipeSerializer):
    """Сериализатор карты покупок."""
    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time',)

    def validate(self, data):
        request = self.context['request']
        recipe_id = request.parser_context['kwargs']['pk']
        if ShoppingCart.objects.filter(
            user=request.user, recipe__id=recipe_id
        ).exists():
            raise serializers.ValidationError(
                "Этот рецепт уже добавлен в корзину."
            )
        return data


class FavoriteSerializer(ShortRecipeSerializer):
    """Сериализатор Избранного на сайте."""
    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time',)

    def validate(self, data):
        request = self.context['request']
        recipe_id = request.parser_context['kwargs']['pk']
        if Favorite.objects.filter(
            user=request.user, recipe__id=recipe_id
        ).exists():
            raise serializers.ValidationError(
                "Этот рецепт уже добавлен в избранное."
            )
        return data


class UserRecipeSerializer(CustomUserReadSerializer):
    """Сериализатор для представления рецептов пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        read_only=True, source='recipes.count'
    )

    class Meta:
        model = CustomUser
        fields = CustomUserReadSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        queryset = Recipe.objects.filter(author=obj)
        request = self.context['request']

        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit is not None and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]
        return RecipeGetSerializer(queryset, many=True).data


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор подписок проекта."""

    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )
    following = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )

    class Meta:
        model = Follow
        fields = ('user', 'following')

    def validate(self, data):
        user = self.context['request'].user
        following_id = self.initial_data.get('following').pk

        if user.pk == following_id:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя."
            )

        if Follow.objects.filter(
            user=user, following_id=following_id
        ).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя."
            )
        return data

    def to_representation(self, instance):
        serializer = UserRecipeSerializer(
            instance.following, context=self.context
        )
        return serializer.data


class AvatarSerializer(UserSerializer):
    """Сериализатор для аватара пользователя."""

    avatar = Base64ImageField()

    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = ('avatar',)


class ShortLinkSerializer(serializers.ModelSerializer):
    """Сериализатор коротких ссылок."""

    class Meta:
        model = RecipeShortLink
        fields = ('original_url',)
        write_only_fields = ('original_url',)

    def get_short_link(self, obj):
        request = self.context['request']
        return request.build_absolute_uri(
            reverse('recipe_by_short_link', args=[obj.short_link])
        )

    def create(self, validated_data):

        instance, _ = RecipeShortLink.objects.get_or_create(**validated_data)
        return instance

    def to_representation(self, instance):
        return {'short-link': self.get_short_link(instance)}

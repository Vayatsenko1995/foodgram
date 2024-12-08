"""Модуль с сериализаторами проекта."""
from rest_framework import exceptions, serializers
from rest_framework.reverse import reverse
from djoser.serializers import UserSerializer

from users.models import CustomUser, Follow
from recipes.models import (
    Recipe, RecipeIngredient, Ingredient,
    Tag, Favorite, ShoppingCart,
    RecipeShortLink
)
from .utils import Base64ImageField, get_request_or_user


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
        fields = UserSerializer.Meta.fields + ('is_subscribed', 'avatar',)
        read_only_fields = ('id', 'is_subscribed', 'avatar',)

    def get_is_subscribed(self, obj):
        """Подписан ли пользователь на автора."""
        user = get_request_or_user(self.context, 'user')
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
        user = get_request_or_user(self.context, 'user')
        if user is None:
            return False
        return (
            Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Добавлен ли рецепт в список Покупок."""
        user = get_request_or_user(self.context, 'user')
        if user is None:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для представления данных о рецепте."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        error_messages={
            'does_not_exist': 'Ингредиент с таким ID не существует.',
            'incorrect_type': 'Неверный тип. Ожидался числовой ID.'
        }
    )
    amount = serializers.IntegerField(
        min_value=1,
        max_value=10000,
        error_messages={
            'min_value': 'Количество должно быть равным или больше 1!',
            'max_value': 'Количество не должно превышать 10000!'
        }
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipePostUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe. Создание, Обновление."""

    ingredients = RecipeIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        error_messages={
            'does_not_exist': 'Неверный id "{pk_value}" - такой тэг не '
                              'существует.'
        }
    )
    cooking_time = serializers.IntegerField(
        min_value=1,
        max_value=1440,
        error_messages={
            'min_value': 'Время приготовления должно быть больше нуля!',
            'max_value': 'Время приготовления не может превышать 24 часа!',
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
        ingredient_ids = [item['id'].id for item in value]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться!'
            )
        return value

    def validate_tags(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Тэги не должны повторяться!')

        return value

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if not ingredients:
            raise exceptions.ValidationError(
                'В рецепт не добавлены ингредиенты'
            )

        if not tags:
            raise serializers.ValidationError({
                'tags': 'Тэги не должны быть пустыми!'
            })

        return data

    def add_ingredient_tag(self, ingredients, tags, recipe):
        """Добавление ингр-ов и тэгов в рецепт при создании и ред-нии."""
        recipe.tags.set(tags)
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient['id'].id,
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


class BaseRecipeRelationSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для реляционных моделей с рецептами."""

    class Meta:
        abstract = True

    def to_representation(self, value):
        """Выбор сериализатора для вывода результата работы класса."""
        recipe = value.recipe
        serializer = RecipeGetSerializer(recipe, context=self.context)
        return serializer.data

    def validate(self, data):
        request = self.context['request']
        recipe_id = request.parser_context['kwargs']['pk']
        model = self.Meta.model
        if model.objects.filter(
            user=request.user, recipe__id=recipe_id
        ).exists():
            raise serializers.ValidationError(
                "Этот рецепт уже добавлен в "
                f"{self.Meta.model._meta.verbose_name}."
            )
        return data


class ShoppingCartSerializer(BaseRecipeRelationSerializer):
    """Сериализатор карты покупок."""

    class Meta(BaseRecipeRelationSerializer.Meta):
        model = ShoppingCart
        fields = ('user', 'recipe',)


class FavoriteSerializer(BaseRecipeRelationSerializer):
    """Сериализатор Избранного на сайте."""

    class Meta(BaseRecipeRelationSerializer.Meta):
        model = Favorite
        fields = ('user', 'recipe',)


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
        request = get_request_or_user(self.context)
        # сделал ещё get_request_attribute в utils.py не смогу решить какой
        # из методов лучше подойдёт.
        recipes_limit = request.query_params.get('recipes_limit')
        try:
            if recipes_limit is not None:
                recipes_limit_int = int(recipes_limit)
                queryset = queryset[:recipes_limit_int]
        except ValueError:
            pass
        return RecipeGetSerializer(
            queryset, many=True, context=self.context
        ).data


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор подписок проекта."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
    )
    following = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Follow
        fields = ('user', 'following')

    def validate(self, data):
        user = self.context['request'].user
        following_id = self.initial_data.get('following')

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

from django.core.validators import MinValueValidator
from rest_framework import exceptions, serializers
from djoser.serializers import UserSerializer

from users.models import CustomUser, Follow
from recipes.models import (
    Recipe, RecipeIngredient, Ingredient,
    Tag, Favorite, ShoppingCart
)
from .utils import Base64ImageField


class CustomUserSerializer(UserSerializer):
    email = serializers.CharField(max_length=254, required=True)
    username = serializers.CharField(max_length=150, required=True)
    is_subscribed = serializers.SerializerMethodField(
        read_only=True,
    )
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser

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
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=self.context['request'].user,
                                     following=obj).exists()


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
        lookup_field = 'id'


class RecipeIngredientSerializer(serializers.ModelSerializer):
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
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
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
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return (
            Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Добавлен ли рецепт в список Покупок."""
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для представления данных о рецепте."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteShoppingSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Favorite и ShoppingCart."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class IngredientForRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов при создании рецепта."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=[MinValueValidator(
            1,
            message='Количество должно быть равным или больше 1!'
        )
        ]
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipePostUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe. Создание, Обновление."""
    ingredients = IngredientForRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()
    image_url = serializers.SerializerMethodField(
        'get_image_url',
        read_only=True,
    )
    author = CustomUserSerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'author',
                  'image', 'name',
                  'image_url',
                  'text', 'cooking_time')

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

    def validate(self, data):
        """Проверка входящих данных на валидность."""
        cooking_time = data.get('cooking_time')
        ingredients = data.get('ingredients')
        tags = data.get('tags')

        # Проверка времени на готовку
        if cooking_time is None or cooking_time <= 0:
            raise exceptions.ValidationError(
                'Время приготовления должно быть больше нуля!'
            )

        # Проверка наличия ингредиентов
        if ingredients is None or len(ingredients) == 0:
            raise exceptions.ValidationError(
                'В рецепт не добавлены ингредиенты'
            )

        if len(ingredients) != len(set(item['id'] for item in ingredients)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться!'
            )

        for ingredient in ingredients:
            if not Ingredient.objects.filter(id=ingredient['id']).exists():
                raise serializers.ValidationError({
                    'ingredients': f'Ингредиента с id - {ingredient["id"]} нет в базе'
                })

    # Проверка наличия тегов
        if tags is None or len(tags) == 0:
            raise serializers.ValidationError({
                'tags': 'Тэги не должны быть пустыми!'
            })

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError({
                'tags': 'Тэги не должны повторяться!'
            })

        return data

    def add_ingredient_tag(self, ingredients, tags, recipe):
        """Добавление ингредиентов и тэгов в рецепт при создании и
        редактировании."""
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
        """Создание нового рецепта."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        return self.add_ingredient_tag(ingredients, tags, recipe)

    def update(self, instance, validated_data):
        """Обновление рецепта."""
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


class ShoppingCartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True
    )

    class Meta:
        model = ShoppingCart
        fields = ('id', 'name', 'image', 'cooking_time',)


class FavoriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(
        source='recipe.cooking_time', read_only=True
    )

    class Meta:
        model = Favorite
        fields = ('id', 'name', 'image', 'cooking_time',)
        # fields = ('id', 'recipe.name', 'recipe.image', 'recipe.cooking_time')

    # def create(self, validated_data):
    #     user = validated_data.pop('user')
    #     recipe_id = validated_data.pop('recipe_id')
    #     recipe = get_object_or_404(Recipe, id=recipe_id)
    #     return FavoriteSerializer(recipe_id)
    # # #     favorite = get_object_or_404(Favorite, user=validated_data)


class UserRecipeSerializer(CustomUserSerializer):
    """Сериализатор для представления рецептов пользователя."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        read_only=True, source='recipes.count'
    )

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_recipes(self, obj):
        """
        Получение рецептов автора.
        """
        queryset = Recipe.objects.filter(author=obj)
        request = self.context.get('request')

        recipes_limit = request.query_params.get('recipes_limit', None)
        if recipes_limit is not None and recipes_limit.isdigit():
            queryset = queryset[:int(recipes_limit)]
        return RecipeGetSerializer(queryset, many=True).data


class FollowSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.email')
    following = serializers.ReadOnlyField(source='following.email')

    class Meta:
        model = Follow
        fields = ('user', 'following')

    def to_representation(self, instance):
        serializer = UserRecipeSerializer(
            instance.following, context=self.context
        )
        return serializer.data

class AvatarSerializer(UserSerializer):
    """Сериализатор для аватара пользователя."""

    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = ('avatar',)

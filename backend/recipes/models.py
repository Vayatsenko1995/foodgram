from django.db import models
from users.models import CustomUser
from django.core.validators import MinValueValidator

import uuid


class Ingredient(models.Model):
    name = models.CharField(max_length=64, unique=True)
    measurement_unit = models.CharField(max_length=16)

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=200, unique=True, verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='Слаг'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'


class Recipe(models.Model):
    author = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(max_length=256)
    image = models.ImageField(
        upload_to='recipe/images/',
        null=False,
    )
    text = models.TextField()
    ingredients = models.ManyToManyField(Ingredient,
                                         through='RecipeIngredient',
                                         related_name='recipes',)
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тэги'
    )
    cooking_time = models.SmallIntegerField(
        validators=[
            MinValueValidator(1),
        ],
        verbose_name='Время приготовления'
    )
    short_link = models.SlugField(unique=True, editable=False)
    

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = str(uuid.uuid4())[:8]  # генерируем короткую ссылку
        super().save(*args, **kwargs)

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipeingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name='recipeingredients'
    )
    amount = models.FloatField()

    def __str__(self):
        return f"{self.amount} {self.ingredient.unit} of {self.ingredient.name}"


class Favorite(models.Model):
    """Модель Избранных рецептов."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites_user',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe',),
                name='unique_favorite',
            ),
        ]
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(models.Model):
    """Модель списка Покупок."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт'
    )

    class Meta:
        # default_related_name = 'shoppingcart'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart',
            ),
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

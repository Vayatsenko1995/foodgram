"""Модуль с моделями связанными с рецептами."""
import uuid

from django.db import models
from users.models import CustomUser
from django.core.validators import MinValueValidator


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
        return f"{self.amount} {self.ingredient.unit} \
    of {self.ingredient.name}"


class Favorite(models.Model):
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
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart',
            ),
        ]
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'


class RecipeShortLink(models.Model):
    short_link = models.CharField(
        max_length=3, unique=True, editable=False
    )
    original_url = models.CharField(max_length=256, unique=True)

    class Meta:
        verbose_name = 'Ссылка'
        verbose_name_plural = 'Ссылки'

    def __str__(self):
        return f'{self.original_url} -> {self.short_link}'

    def save(self, *args, **kwargs):
        """Переопределяем метод для генерации short_link перед сохранением."""
        if not self.short_link:
            self.short_link = str(uuid.uuid4())[:3]
        super().save(*args, **kwargs)

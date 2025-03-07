# Generated by Django 3.2.3 on 2024-12-07 13:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_auto_20241207_1643'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipeingredient',
            name='amount',
            field=models.FloatField(verbose_name='Количество'),
        ),
        migrations.AlterField(
            model_name='recipeingredient',
            name='ingredient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipeingredients', to='recipes.ingredient', verbose_name='Ингридиент'),
        ),
        migrations.AlterField(
            model_name='recipeingredient',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipeingredients', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AlterField(
            model_name='recipeshortlink',
            name='original_url',
            field=models.CharField(max_length=256, unique=True, verbose_name='Оригинальная ссылка'),
        ),
        migrations.AlterField(
            model_name='recipeshortlink',
            name='short_link',
            field=models.CharField(editable=False, max_length=3, unique=True, verbose_name='Короткая ссылка'),
        ),
    ]

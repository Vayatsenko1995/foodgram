import base64

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status

from recipes.models import Recipe

class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


def add_or_delete_model(request, model, serializer, pk=None):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == 'POST':
        serializer = serializer(data={
            'recipe': recipe.id,
            'user': request.user.id,
        })
        if not serializer.is_valid() or model.objects.filter(
            user=request.user,
            recipe=recipe
        ):
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(user=request.user, recipe=recipe,)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    elif request.method == 'DELETE':
        if not model.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists():
            return Response(
                {'error': 'Рецепт в списке не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        model.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

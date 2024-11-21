from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter


from .views import (
    CustomUserViewSet, IngredientViewSet,
    TagViewSet, RecipeViewSet,
    short_link,
)

router = DefaultRouter()

router.register(r'tags', TagViewSet, basename='tags')
router.register(r'users', CustomUserViewSet, basename='users')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')


urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),

    path('<str:short_link/', short_link, name='short_link'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

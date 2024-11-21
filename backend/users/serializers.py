# from rest_framework import serializers
# from djoser.serializers import UserSerializer

# from users.models import CustomUser, Follow
# from api.utils import Base64ImageField
# from api.mixins import RecipesMixin


# class CustomUserSerializer(UserSerializer):
#     email = serializers.CharField(max_length=254, required=True)
#     username = serializers.CharField(max_length=150, required=True)
#     is_subscribed = serializers.SerializerMethodField(
#         read_only=True,
#     )
#     avatar = Base64ImageField(required=False, allow_null=True)

#     class Meta:
#         model = CustomUser

#         fields = (
#             'email',
#             'id',
#             'username',
#             'first_name',
#             'last_name',
#             'is_subscribed',
#             'avatar',
#         )

#         read_only_fields = ('id', 'is_subscribed', 'avatar',)

#     def get_is_subscribed(self, obj):
#         """Подписан ли пользователь на автора."""
#         request = self.context.get('request')
#         if not request or request.user.is_anonymous:
#             return False
#         return Follow.objects.filter(user=self.context['request'].user,
#                                      following=obj).exists()


# class FollowSerializer(serializers.ModelSerializer, RecipesMixin):
#     user = CustomUserSerializer(read_only=True)
#     following = CustomUserSerializer(read_only=True)

#     class Meta:
#         model = Follow
#         fields = (
#             'id',
#             'user',
#             'recipes',
#             'recipes_count',  
#             'following',
#         )


# class AvatarSerializer(UserSerializer):
#     """Сериализатор для аватара пользователя."""

#     avatar = Base64ImageField(required=False, allow_null=True)

#     class Meta(UserSerializer.Meta):
#         model = CustomUser
#         fields = ('avatar',)

from rest_framework import serializers
from ..models import UserProfile, Post
from .post_serializer import PostSerializer

class UserProfileSerializer(serializers.ModelSerializer):
    posts = PostSerializer(many=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'name', 'posts']
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Name must contain min 2 symbols"
            )
        return value
    
    def validate_posts(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Posts must be submitted as a list"
            )
        if len(value) == 0:
            raise serializers.ValidationError(
                "User must have at least 1 post"
            )
        
        titles = [post.get('title', '').strip().lower() for post in value]
        if len(titles) != len(set(titles)):
            raise serializers.ValidationError(
                "One request cannot contain posts with the same titles"
            )
        
        if len(value) > 10:
            raise serializers.ValidationError(
                "Cannot create/update more than 10 posts at a time"
            )
        
        return value
    
    def create(self, validated_data):
        posts_data = validated_data.pop('posts', [])
        instance = UserProfile.objects.create(**validated_data)
        
        for post_data in posts_data:
            post_serializer = PostSerializer(data=post_data)
            if post_serializer.is_valid(raise_exception=True):
                post_serializer.save(user=instance)
        
        return instance

    def update(self, instance, validated_data):
        posts_data = validated_data.pop('posts', [])
        
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        post_ids_to_keep = set()
        
        for post_data in posts_data:
            post_id = post_data.pop('id', None)
            
            if post_id:
                try:
                    post_item = Post.objects.get(id=post_id, user=instance)
                    post_serializer = PostSerializer(post_item, data=post_data, partial=True)
                    if post_serializer.is_valid(raise_exception=True):
                        post_serializer.save()
                    post_ids_to_keep.add(post_id)
                except Post.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Post wiz id {post_id} not found for this user"
                    )
            else:
                post_serializer = PostSerializer(data=post_data)
                if post_serializer.is_valid(raise_exception=True):
                    new_post = post_serializer.save(user=instance)
                    post_ids_to_keep.add(new_post.id)
        Post.objects.filter(user=instance).exclude(id__in=post_ids_to_keep).delete()
        return instance
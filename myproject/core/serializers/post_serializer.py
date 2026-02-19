from rest_framework import serializers
from ..models import Post

class PostSerializer(serializers.ModelSerializer):
    # id field for selected post
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Post
        fields = ['id', 'title', 'content']
    
    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Title must have min 3 chars!"
            )
        return value
    
    def validate_content(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError(
                "Post content cannot be empty!"
            )
        return value
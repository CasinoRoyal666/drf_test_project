from django.db import models

class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# for nested serializers
class UserProfile(TimestampMixin):
    name = models.CharField(max_length=100)

class Post(TimestampMixin):
    user = models.ForeignKey(UserProfile, related_name='posts', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()

class Comment(TimestampMixin):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField()
    likes = models.IntegerField(default=0)

# context logic
class Passport(TimestampMixin):
    full_name = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=20)
    address = models.CharField(max_length=200)
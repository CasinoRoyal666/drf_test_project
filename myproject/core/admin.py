from django.contrib import admin
from .models import UserProfile, Post, Passport

class PostInline(admin.TabularInline):
    model = Post
    extra = 1 

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    inlines = [PostInline]

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'content_preview')
    list_filter = ('user',)
    search_fields = ('title', 'content')

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'



@admin.register(Passport)
class PassportAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'passport_number', 'address')
    search_fields = ('full_name', 'passport_number')
    list_editable = ('passport_number',) 
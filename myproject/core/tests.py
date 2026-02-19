from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import UserProfile, Post, Passport, Comment


class UserProfileSerializerTests(TestCase):
    """tests for UserProfile wiz nested posts"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/'
    
    def test_create_user_with_posts(self):
        """Create a user with posts"""
        data = {
            "name": "John Doe",
            "posts": [
                {"title": "Post 1", "content": "Content 1"},
                {"title": "Post 2", "content": "Content 2"}
            ]
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'John Doe')
        self.assertEqual(len(response.data['posts']), 2)
    
    # Validation duplicates
    def test_validation_duplicate_titles(self):
        """Val. duplicates of titles"""
        data = {
            "name": "Test User",
            "posts": [
                {"title": "Same Title", "content": "Content 1"},
                {"title": "Same Title", "content": "Content 2"}
            ]
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_max_chars(self):
        long = "aA" * 100
        data = {
            "name": "Test User",
            "posts": [
                {"title": long, "content": "Content 1"},
            ]
        }
        self.assertGreater(len(long), 100)
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # Val. limit of posts (10 per one time)
    def test_validation_max_posts_limit(self):
        posts = [{"title": f"Post {i}", "content": f"Content {i}"} for i in range(11)]
        data = {"name": "Test User", "posts": posts}
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # Val. empty content
    def test_validation_empty_content(self):
        data = {
            "name": "Test User",
            "posts": [{"title": "Valid Title", "content": ""}]
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # Update test
    def test_update_user_and_posts(self):
        user = UserProfile.objects.create(name='Test User')
        post = Post.objects.create(user=user, title='Old Title', content='Old Content')
        
        data = {
            "name": "Updated User",
            "posts": [
                {"id": post.id, "title": "New Title", "content": "New Content"},
                {"title": "New Post", "content": "New Post Content"}
            ]
        }
        
        response = self.client.put(f'{self.url}{user.id}/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['posts']), 2)

#### TASK2 #####
class PassportSerializerTests(TestCase):
    """Tests for Passport with context logic"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/passports/'
    
    # Create passport
    def test_create_passport(self):
        """Create passport"""
        data = {
            "full_name": "Ivan Petrov",
            "passport_number": "AB123456",
            "address": "Moscow, Russia",
            "checker_role": "customs"
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['full_name'], 'Ivan Petrov')
    
    # Context logic - customs role
    def test_sensitive_info_customs_role(self):
        """Full access for customs role"""
        passport = Passport.objects.create(
            full_name='Ivan Petrov',
            passport_number='AB123456',
            address='Moscow, Russia'
        )
        
        response = self.client.get(f'{self.url}{passport.id}/?checker_role=customs')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('FULL ACCESS', response.data['sensitive_info'])
        self.assertIn('AB123456', response.data['sensitive_info'])
    
    # Context logic - passport_office role
    def test_sensitive_info_passport_office_role(self):
        """Internal data for passport_office role"""
        passport = Passport.objects.create(
            full_name='Ivan Petrov',
            passport_number='AB123456',
            address='Moscow, Russia'
        )
        
        response = self.client.get(f'{self.url}{passport.id}/?checker_role=passport_office')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('INTERNAL DATA', response.data['sensitive_info'])
    
    # Context logic - no role
    def test_sensitive_info_no_role(self):
        """Access denied when role not provided"""
        passport = Passport.objects.create(
            full_name='Ivan Petrov',
            passport_number='AB123456',
            address='Moscow, Russia'
        )
        
        response = self.client.get(f'{self.url}{passport.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ACCESS DENIED', response.data['sensitive_info'])


class MostLikedCommentTests(TestCase):
    """Tests for getting most liked comment using Django ORM"""
    
    def setUp(self):
        self.user = UserProfile.objects.create(name='Test User')
        self.post = Post.objects.create(
            user=self.user,
            title='Test Post',
            content='Test Content'
        )
    
    def test_get_most_liked_comment(self):
        """Get most liked comment for a post"""
        comment1 = Comment.objects.create(post=self.post, text='Comment 1', likes=5)
        comment2 = Comment.objects.create(post=self.post, text='Comment 2', likes=15)
        comment3 = Comment.objects.create(post=self.post, text='Comment 3', likes=10)
        
        most_liked = Comment.objects.filter(
            post_id=self.post.id,
            post__user_id=self.user.id
        ).order_by('-likes').first()
        
        self.assertIsNotNone(most_liked)
        self.assertEqual(most_liked.id, comment2.id)
        self.assertEqual(most_liked.likes, 15)
        self.assertEqual(most_liked.text, 'Comment 2')

    

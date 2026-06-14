from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from splitwise.models import Group

User = get_user_model()

class AuthAndGroupTests(APITestCase):
    """
    Test suite for registration, login, and group operations under deadline.
    """
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.me_url = reverse('auth_me')
        self.group_list_url = reverse('group-list')
        
        # Create test users
        self.user1 = User.objects.create_user(email='test1@example.com', password='password123', name='Test User 1')
        self.user2 = User.objects.create_user(email='test2@example.com', password='password123', name='Test User 2')

    def test_registration(self):
        data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'name': 'New User'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'newuser@example.com')

    def test_login(self):
        data = {
            'email': 'test1@example.com',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_get_me(self):
        # Authenticate first
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test1@example.com')

    def test_group_crud(self):
        self.client.force_authenticate(user=self.user1)
        
        # 1. Create a group
        group_data = {
            'name': 'Test Group',
            'members': [self.user1.id, self.user2.id]
        }
        response = self.client.post(self.group_list_url, group_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        group_id = response.data['id']
        self.assertEqual(response.data['name'], 'Test Group')
        self.assertEqual(response.data['created_by'], self.user1.id)
        
        # 2. List groups (should see the group)
        list_response = self.client.get(self.group_list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        
        # 3. Add/Remove member (remove user2)
        detail_url = reverse('group-detail', args=[group_id])
        update_data = {
            'name': 'Updated Test Group',
            'members': [self.user1.id]  # Only user1 remains
        }
        update_response = self.client.put(detail_url, update_data, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(update_response.data['members_detail']), 1)
        self.assertEqual(update_response.data['members_detail'][0]['id'], self.user1.id)
        
        # 4. Access validation: user2 shouldn't see it anymore
        self.client.force_authenticate(user=self.user2)
        unauthorized_list = self.client.get(self.group_list_url)
        self.assertEqual(unauthorized_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(unauthorized_list.data), 0)

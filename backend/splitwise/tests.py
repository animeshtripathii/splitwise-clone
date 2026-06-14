from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from splitwise.models import Group, Expense, ExpenseShare, Settlement, ChatMessage
from decimal import Decimal

User = get_user_model()

class CompleteSplitwiseTests(APITestCase):
    """
    Complete unit tests checking auth, groups, equal/unequal/percentage/share split types,
    settlements, and chats under tight deadlines.
    """
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.me_url = reverse('auth_me')
        self.group_list_url = reverse('group-list')
        self.expense_list_url = reverse('expense-list')
        self.settlement_list_url = reverse('settlement-list')
        self.chat_list_url = reverse('chat-message-list')
        
        # Create users
        self.user1 = User.objects.create_user(email='test1@example.com', password='password123', name='User 1')
        self.user2 = User.objects.create_user(email='test2@example.com', password='password123', name='User 2')
        self.user3 = User.objects.create_user(email='test3@example.com', password='password123', name='User 3')
        
        # Create a group
        self.group = Group.objects.create(name='The Flat', created_by=self.user1)
        self.group.members.set([self.user1, self.user2, self.user3])
        self.group.save()

    def test_registration_and_login(self):
        # Register
        data = {'email': 'new@example.com', 'password': 'pass', 'name': 'New'}
        res = self.client.post(self.register_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', res.data)
        
        # Login
        data = {'email': 'new@example.com', 'password': 'pass'}
        res = self.client.post(self.login_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_group_crud(self):
        self.client.force_authenticate(user=self.user1)
        # Verify listing
        res = self.client.get(self.group_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_equal_split_rounding(self):
        self.client.force_authenticate(user=self.user1)
        # Splitting 100.00 INR among 3 people. Owed amounts should sum exactly to 100.00.
        data = {
            'group': self.group.id,
            'payer': self.user1.id,
            'amount': '100.00',
            'description': 'Pizza',
            'date': '2026-06-14',
            'split_type': 'equal',
            'shares': [
                {'user': self.user1.id},
                {'user': self.user2.id},
                {'user': self.user3.id}
            ]
        }
        res = self.client.post(self.expense_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Verify sum
        shares = ExpenseShare.objects.filter(expense_id=res.data['id'])
        self.assertEqual(shares.count(), 3)
        total_owed = sum(s.owed_amount for s in shares)
        self.assertEqual(total_owed, Decimal('100.00'))
        
        # Remainder should go to the first in the input (user1 gets 33.34, others get 33.33)
        user1_share = shares.get(user=self.user1)
        self.assertEqual(user1_share.owed_amount, Decimal('33.34'))

    def test_unequal_split_math(self):
        self.client.force_authenticate(user=self.user1)
        # Splitting 100.00 INR unequally: 50, 30, 20.
        data = {
            'group': self.group.id,
            'payer': self.user1.id,
            'amount': '100.00',
            'description': 'Pizza',
            'date': '2026-06-14',
            'split_type': 'unequal',
            'shares': [
                {'user': self.user1.id, 'raw_input_value': '50.00'},
                {'user': self.user2.id, 'raw_input_value': '30.00'},
                {'user': self.user3.id, 'raw_input_value': '20.00'}
            ]
        }
        res = self.client.post(self.expense_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        shares = ExpenseShare.objects.filter(expense_id=res.data['id'])
        self.assertEqual(shares.get(user=self.user1).owed_amount, Decimal('50.00'))
        self.assertEqual(shares.get(user=self.user2).owed_amount, Decimal('30.00'))
        self.assertEqual(shares.get(user=self.user3).owed_amount, Decimal('20.00'))
        
        # Validation failure: sum doesn't match
        data['amount'] = '150.00'
        res = self.client.post(self.expense_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_percentage_split_normalization(self):
        self.client.force_authenticate(user=self.user1)
        # Splitting 250.00 INR by percentage: 50%, 30%, 20%
        # Let's send unnormalized percents (10, 6, 4) which sum to 20. They should be normalized to (50%, 30%, 20%).
        data = {
            'group': self.group.id,
            'payer': self.user1.id,
            'amount': '250.00',
            'description': 'Uber',
            'date': '2026-06-14',
            'split_type': 'percentage',
            'shares': [
                {'user': self.user1.id, 'raw_input_value': '10.00'},
                {'user': self.user2.id, 'raw_input_value': '6.00'},
                {'user': self.user3.id, 'raw_input_value': '4.00'}
            ]
        }
        res = self.client.post(self.expense_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        shares = ExpenseShare.objects.filter(expense_id=res.data['id'])
        self.assertEqual(shares.get(user=self.user1).owed_amount, Decimal('125.00'))
        self.assertEqual(shares.get(user=self.user2).owed_amount, Decimal('75.00'))
        self.assertEqual(shares.get(user=self.user3).owed_amount, Decimal('50.00'))

    def test_share_split_math(self):
        self.client.force_authenticate(user=self.user1)
        # Splitting 300.00 INR by shares: 3 shares, 2 shares, 1 share
        data = {
            'group': self.group.id,
            'payer': self.user1.id,
            'amount': '300.00',
            'description': 'Rent',
            'date': '2026-06-14',
            'split_type': 'share',
            'shares': [
                {'user': self.user1.id, 'raw_input_value': '3.00'},
                {'user': self.user2.id, 'raw_input_value': '2.00'},
                {'user': self.user3.id, 'raw_input_value': '1.00'}
            ]
        }
        res = self.client.post(self.expense_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        shares = ExpenseShare.objects.filter(expense_id=res.data['id'])
        self.assertEqual(shares.get(user=self.user1).owed_amount, Decimal('150.00'))
        self.assertEqual(shares.get(user=self.user2).owed_amount, Decimal('100.00'))
        self.assertEqual(shares.get(user=self.user3).owed_amount, Decimal('50.00'))

    def test_settlements(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            'group': self.group.id,
            'from_user': self.user2.id,
            'to_user': self.user1.id,
            'amount': '45.50',
            'date': '2026-06-14'
        }
        res = self.client.post(self.settlement_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Same-user validation check
        data['to_user'] = self.user2.id
        res = self.client.post(self.settlement_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expense_comments_polling(self):
        self.client.force_authenticate(user=self.user1)
        
        # Create an expense
        expense = Expense.objects.create(
            group=self.group,
            payer=self.user1,
            amount=Decimal('10.00'),
            description='Test Chat Expense',
            date='2026-06-14',
            split_type='equal'
        )
        
        # Post comment
        data = {
            'expense': expense.id,
            'text': 'This is a test comment'
        }
        res = self.client.post(self.chat_list_url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['sender'], self.user1.id)
        
        # Poll comments
        res = self.client.get(f"{self.chat_list_url}?expense={expense.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['text'], 'This is a test comment')

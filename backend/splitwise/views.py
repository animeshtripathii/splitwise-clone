from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db.models import Sum
from decimal import Decimal
from splitwise.models import Group, Expense, Settlement, ChatMessage, ExpenseShare
from splitwise.serializers import (
    UserSerializer, RegisterSerializer, GroupSerializer,
    ExpenseSerializer, SettlementSerializer, ChatMessageSerializer
)

User = get_user_model()

class RegisterView(APIView):
    """
    Public registration endpoint. Creates user and returns JWT tokens immediately
    to log them in.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    """
    Returns the authenticated user's profile information.
    """
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class GroupViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for managing groups. Limits list/retrieve actions to groups
    the user is currently part of. Exposes an action /api/groups/<id>/balances/
    to compute net balances and simplified transactions.
    """
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['get'])
    def balances(self, request, pk=None):
        group = self.get_object()
        members = group.members.all()
        
        balances = []
        debtors = []
        creditors = []
        
        for member in members:
            # Paid by member
            paid = Expense.objects.filter(group=group, payer=member).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            # Owed by member
            owed = ExpenseShare.objects.filter(expense__group=group, user=member).aggregate(total=Sum('owed_amount'))['total'] or Decimal('0.00')
            # Sent settlements
            sent = Settlement.objects.filter(group=group, from_user=member).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            # Received settlements
            received = Settlement.objects.filter(group=group, to_user=member).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            net_balance = Decimal(paid) - Decimal(owed) + Decimal(sent) - Decimal(received)
            net_balance = net_balance.quantize(Decimal('0.01'))
            
            balances.append({
                'user': UserSerializer(member).data,
                'net_balance': float(net_balance)
            })
            
            if net_balance < -Decimal('0.01'):
                debtors.append({'member': member, 'balance': net_balance})
            elif net_balance > Decimal('0.01'):
                creditors.append({'member': member, 'balance': net_balance})
                
        # Simplify debts algorithm
        # Sort debtors ascending (most negative first)
        # Sort creditors descending (most positive first)
        debtors.sort(key=lambda x: x['balance'])
        creditors.sort(key=lambda x: x['balance'], reverse=True)
        
        transactions = []
        d_idx = 0
        c_idx = 0
        
        # Copy to avoid side-effects
        debts = [{'member': d['member'], 'balance': d['balance']} for d in debtors]
        credits = [{'member': c['member'], 'balance': c['balance']} for c in creditors]
        
        while d_idx < len(debts) and c_idx < len(credits):
            debtor = debts[d_idx]
            creditor = credits[c_idx]
            
            debt_amount = -debtor['balance']
            credit_amount = creditor['balance']
            
            if debt_amount == 0:
                d_idx += 1
                continue
            if credit_amount == 0:
                c_idx += 1
                continue
                
            amount_to_transfer = min(debt_amount, credit_amount)
            
            transactions.append({
                'from_user': UserSerializer(debtor['member']).data,
                'to_user': UserSerializer(creditor['member']).data,
                'amount': float(amount_to_transfer.quantize(Decimal('0.01')))
            })
            
            debtor['balance'] += amount_to_transfer
            creditor['balance'] -= amount_to_transfer
            
            if abs(debtor['balance']) < Decimal('0.01'):
                d_idx += 1
            if abs(creditor['balance']) < Decimal('0.01'):
                c_idx += 1
                
        return Response({
            'balances': balances,
            'transactions': transactions
        })

class ExpenseViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for managing expenses. Ensures users can only access expenses
    for groups they belong to.
    """
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(group__members=self.request.user).distinct().order_by('-date', '-created_at')

class SettlementViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for settlements. Ensures users can only see settlements for groups they belong to.
    """
    serializer_class = SettlementSerializer

    def get_queryset(self):
        return Settlement.objects.filter(group__members=self.request.user).distinct().order_by('-date', '-created_at')

class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for expense comment chat messages. Supports querying by ?expense=ID.
    """
    serializer_class = ChatMessageSerializer

    def get_queryset(self):
        queryset = ChatMessage.objects.filter(expense__group__members=self.request.user).distinct()
        expense_id = self.request.query_params.get('expense')
        if expense_id:
            queryset = queryset.filter(expense_id=expense_id)
        return queryset.order_by('timestamp')

from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from splitwise.models import Group, Expense, Settlement, ChatMessage
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
    the user is currently part of.
    """
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user).order_by('-created_at')

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

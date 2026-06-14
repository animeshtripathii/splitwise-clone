from rest_framework import status, viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from splitwise.models import Group
from splitwise.serializers import UserSerializer, RegisterSerializer, GroupSerializer

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
        # Only return groups the requesting user is a member of
        return Group.objects.filter(members=self.request.user).order_by('-created_at')

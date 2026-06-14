from rest_framework import serializers
from django.contrib.auth import get_user_model
from splitwise.models import Group

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer to represent user public details.
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'name')

class RegisterSerializer(serializers.Serializer):
    """
    Handles user registration under deadline — validates unique email and creates
    the user with a hashed password.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', '')
        )

class GroupSerializer(serializers.ModelSerializer):
    """
    Handles Group details. Serializes members as nested objects on GET, but allows
    writing member IDs on POST/PUT/PATCH.
    """
    members_detail = UserSerializer(source='members', many=True, read_only=True)
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )
    created_by_detail = UserSerializer(source='created_by', read_only=True)

    class Meta:
        model = Group
        fields = ('id', 'name', 'members', 'members_detail', 'created_by', 'created_by_detail', 'created_at')
        read_only_fields = ('created_by', 'created_at')

    def create(self, validated_data):
        # Automatically set created_by to the requesting user
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        members = validated_data.pop('members', [])
        group = Group.objects.create(**validated_data)
        if members:
            group.members.set(members)
        else:
            # If no members provided, default to adding the creator
            group.members.add(request.user)
        return group

    def update(self, instance, validated_data):
        members = validated_data.pop('members', None)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        if members is not None:
            instance.members.set(members)
        return instance

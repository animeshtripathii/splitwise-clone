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

from decimal import Decimal

def calculate_splits(amount, split_type, shares_data):
    """
    Split math engine: calculates exact owed amounts per participant.
    Ensures total of owed amounts exactly equals the expense amount by distributing
    rounding remainders to the first participant.
    """
    total_amount = Decimal(str(amount))
    n = len(shares_data)
    if n == 0:
        raise ValueError("At least one participant is required.")

    calculated_shares = []

    if split_type == 'equal':
        base_owed = (total_amount / n).quantize(Decimal('0.01'))
        for item in shares_data:
            calculated_shares.append({
                'user_id': item['user_id'],
                'owed_amount': base_owed,
                'raw_input_value': Decimal('1.00')
            })
        diff = total_amount - (base_owed * n)
        if diff != 0:
            calculated_shares[0]['owed_amount'] += diff

    elif split_type == 'unequal':
        sum_inputs = Decimal('0.00')
        for item in shares_data:
            val = Decimal(str(item.get('raw_input_value', 0)))
            sum_inputs += val
            calculated_shares.append({
                'user_id': item['user_id'],
                'owed_amount': val.quantize(Decimal('0.01')),
                'raw_input_value': val
            })
        if sum_inputs != total_amount:
            raise ValueError(f"Sum of unequal amounts ({sum_inputs}) must equal expense amount ({total_amount})")

    elif split_type == 'percentage':
        total_pct = sum(Decimal(str(item.get('raw_input_value', 0))) for item in shares_data)
        if total_pct == 0:
            raise ValueError("Total percentage cannot be zero.")
        running_sum = Decimal('0.00')
        for item in shares_data:
            pct = Decimal(str(item.get('raw_input_value', 0)))
            owed = (total_amount * pct / total_pct).quantize(Decimal('0.01'))
            running_sum += owed
            calculated_shares.append({
                'user_id': item['user_id'],
                'owed_amount': owed,
                'raw_input_value': pct
            })
        diff = total_amount - running_sum
        if diff != 0:
            calculated_shares[0]['owed_amount'] += diff

    elif split_type == 'share':
        total_shares = sum(Decimal(str(item.get('raw_input_value', 0))) for item in shares_data)
        if total_shares == 0:
            raise ValueError("Total shares cannot be zero.")
        running_sum = Decimal('0.00')
        for item in shares_data:
            sh = Decimal(str(item.get('raw_input_value', 0)))
            owed = (total_amount * sh / total_shares).quantize(Decimal('0.01'))
            running_sum += owed
            calculated_shares.append({
                'user_id': item['user_id'],
                'owed_amount': owed,
                'raw_input_value': sh
            })
        diff = total_amount - running_sum
        if diff != 0:
            calculated_shares[0]['owed_amount'] += diff

    return calculated_shares

from splitwise.models import Expense, ExpenseShare, Settlement, ChatMessage

class ExpenseShareSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ExpenseShare
        fields = ('id', 'user', 'user_detail', 'owed_amount', 'raw_input_value')

class ExpenseSerializer(serializers.ModelSerializer):
    shares = ExpenseShareSerializer(many=True, read_only=True)
    payer_detail = UserSerializer(source='payer', read_only=True)

    class Meta:
        model = Expense
        fields = ('id', 'group', 'payer', 'payer_detail', 'amount', 'currency', 'description', 'date', 'split_type', 'shares', 'created_at')
        read_only_fields = ('created_at',)

    def validate(self, attrs):
        group = attrs.get('group')
        payer = attrs.get('payer')
        if group and payer and not group.members.filter(id=payer.id).exists():
            raise serializers.ValidationError("Payer must be a member of the group.")
        return attrs

    def create(self, validated_data):
        shares_data = self.context.get('request').data.get('shares', [])
        if not shares_data:
            raise serializers.ValidationError({"shares": "At least one participant share is required."})

        amount = validated_data['amount']
        split_type = validated_data['split_type']
        group = validated_data['group']

        prepared_shares = []
        for s in shares_data:
            user_id = s.get('user')
            if not user_id:
                raise serializers.ValidationError({"shares": "Each share must specify a user."})
            if not group.members.filter(id=user_id).exists():
                raise serializers.ValidationError({"shares": f"User ID {user_id} is not a member of the group."})
            
            raw_val = s.get('raw_input_value')
            prepared_shares.append({
                'user_id': user_id,
                'raw_input_value': Decimal(str(raw_val)) if raw_val is not None else None
            })

        try:
            calculated_shares = calculate_splits(amount, split_type, prepared_shares)
        except ValueError as e:
            raise serializers.ValidationError({"non_field_errors": str(e)})

        expense = Expense.objects.create(**validated_data)

        for cs in calculated_shares:
            ExpenseShare.objects.create(
                expense=expense,
                user_id=cs['user_id'],
                owed_amount=cs['owed_amount'],
                raw_input_value=cs['raw_input_value']
            )

        return expense

    def update(self, instance, validated_data):
        shares_data = self.context.get('request').data.get('shares')

        instance.payer = validated_data.get('payer', instance.payer)
        instance.amount = validated_data.get('amount', instance.amount)
        instance.description = validated_data.get('description', instance.description)
        instance.date = validated_data.get('date', instance.date)
        instance.split_type = validated_data.get('split_type', instance.split_type)
        instance.group = validated_data.get('group', instance.group)
        instance.save()

        if shares_data is not None:
            instance.shares.all().delete()
            prepared_shares = []
            group = instance.group
            for s in shares_data:
                user_id = s.get('user')
                if not user_id:
                    raise serializers.ValidationError({"shares": "Each share must specify a user."})
                if not group.members.filter(id=user_id).exists():
                    raise serializers.ValidationError({"shares": f"User ID {user_id} is not a member of the group."})
                raw_val = s.get('raw_input_value')
                prepared_shares.append({
                    'user_id': user_id,
                    'raw_input_value': Decimal(str(raw_val)) if raw_val is not None else None
                })

            try:
                calculated_shares = calculate_splits(instance.amount, instance.split_type, prepared_shares)
            except ValueError as e:
                raise serializers.ValidationError({"non_field_errors": str(e)})

            for cs in calculated_shares:
                ExpenseShare.objects.create(
                    expense=instance,
                    user_id=cs['user_id'],
                    owed_amount=cs['owed_amount'],
                    raw_input_value=cs['raw_input_value']
                )

        return instance

class SettlementSerializer(serializers.ModelSerializer):
    from_user_detail = UserSerializer(source='from_user', read_only=True)
    to_user_detail = UserSerializer(source='to_user', read_only=True)

    class Meta:
        model = Settlement
        fields = ('id', 'group', 'from_user', 'from_user_detail', 'to_user', 'to_user_detail', 'amount', 'date', 'created_at')
        read_only_fields = ('created_at',)

    def validate(self, attrs):
        group = attrs.get('group')
        from_user = attrs.get('from_user')
        to_user = attrs.get('to_user')

        if from_user == to_user:
            raise serializers.ValidationError("Cannot record a settlement to the same user.")
        
        if not group.members.filter(id=from_user.id).exists():
            raise serializers.ValidationError(f"Sender {from_user} must be a member of the group.")
        
        if not group.members.filter(id=to_user.id).exists():
            raise serializers.ValidationError(f"Recipient {to_user} must be a member of the group.")
            
        if attrs.get('amount', 0) <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")

        return attrs

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_detail = UserSerializer(source='sender', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ('id', 'expense', 'sender', 'sender_detail', 'text', 'timestamp')
        read_only_fields = ('sender', 'timestamp')

    def create(self, validated_data):
        # Auto-inject the requesting user as the sender
        request = self.context.get('request')
        if request and request.user:
            validated_data['sender'] = request.user
        return super().create(validated_data)

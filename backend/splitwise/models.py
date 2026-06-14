from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    """
    Overriding default user manager under deadline to support email-only logins
    without needing username placeholders.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom user model where email is the primary identifier.
    """
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.name or self.email

class Group(models.Model):
    """
    Represents flat/roommate groups.
    """
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User, related_name='splitwise_groups')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    """
    Represents an expense split among group members.
    """
    SPLIT_TYPES = (
        ('equal', 'Equal'),
        ('unequal', 'Unequal'),
        ('percentage', 'Percentage'),
        ('share', 'Share'),
    )

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='expenses')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paid_expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    description = models.CharField(max_length=255)
    date = models.DateField()
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} ({self.amount} {self.currency})"

class ExpenseShare(models.Model):
    """
    Per-participant share showing how much they owe for a specific expense.
    We store the raw input (shares or percent) so UI can rebuild the form.
    """
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares')
    owed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    raw_input_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} owes {self.owed_amount} for {self.expense.description}"

class Settlement(models.Model):
    """
    Offsets outstanding balances between members.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='settlements')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_settlements')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_settlements')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_user.email} -> {self.to_user.email}: {self.amount}"

class ChatMessage(models.Model):
    """
    Basic comment log per expense, polled under timeline view.
    """
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.email}: {self.text[:20]}"

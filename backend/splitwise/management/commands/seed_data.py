from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from splitwise.models import Group

class Command(BaseCommand):
    help = 'Seeds initial users (Aisha, Rohan, Priya, Meera, Dev, Sam) and the default group "The Flat"'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # User details: email/username mapping
        users_data = [
            {'name': 'Aisha', 'email': 'aisha@example.com'},
            {'name': 'Rohan', 'email': 'rohan@example.com'},
            {'name': 'Priya', 'email': 'priya@example.com'},
            {'name': 'Meera', 'email': 'meera@example.com'},
            {'name': 'Dev', 'email': 'dev@example.com'},
            {'name': 'Sam', 'email': 'sam@example.com'},
        ]
        
        seeded_users = []
        for u_data in users_data:
            user, created = User.objects.get_or_create(
                email=u_data['email'],
                defaults={'name': u_data['name']}
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {u_data['name']}"))
            else:
                self.stdout.write(f"User {u_data['name']} already exists")
            seeded_users.append(user)
            
        # Create group "The Flat"
        group, created = Group.objects.get_or_create(
            name='The Flat',
            defaults={'created_by': seeded_users[0]}
        )
        if created:
            group.members.set(seeded_users)
            group.save()
            self.stdout.write(self.style.SUCCESS('Created group: "The Flat" with 6 members.'))
        else:
            # Ensure all members are present
            group.members.set(seeded_users)
            group.save()
            self.stdout.write('Group "The Flat" already exists, synced members.')

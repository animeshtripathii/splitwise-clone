import os
import csv
import re
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from splitwise.models import Group, Expense, ExpenseShare, Settlement
from splitwise.serializers import calculate_splits

User = get_user_model()

class Command(BaseCommand):
    help = 'Imports expenses and settlements from the exported CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the import in a dry-run transaction that rolls back at the end'
        )

    def map_user_name(self, raw_name):
        n = raw_name.strip().lower()
        if n in ('aisha', 'aisha '):
            return 'Aisha'
        if n in ('rohan', 'rohan '):
            return 'Rohan'
        if n in ('priya', 'priya s', 'priya s '):
            return 'Priya'
        if n == 'meera':
            return 'Meera'
        if n == 'dev':
            return 'Dev'
        if n == 'sam':
            return 'Sam'
        if 'kabir' in n:
            return 'Kabir'
        return raw_name.strip()

    def get_or_create_user(self, name):
        mapped_name = self.map_user_name(name)
        email = f"{mapped_name.lower()}@example.com"
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'name': mapped_name}
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created new user {mapped_name} ({email}) during import"))
        return user

    def parse_csv_date(self, raw_date, description):
        d_str = raw_date.strip()
        if d_str.lower() == 'mar-14':
            return datetime.strptime('14-03-2026', '%d-%m-%Y').date()
        
        # Specific anomaly row 34: 04-05-2026 sitting chronologically on April 5
        if d_str == '04-05-2026' and 'Deep cleaning' in description:
            return datetime.strptime('05-04-2026', '%d-%m-%Y').date()
            
        return datetime.strptime(d_str, '%d-%m-%Y').date()

    def parse_split_details(self, details_str):
        res = {}
        if not details_str:
            return res
        parts = details_str.split(';')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Matches names followed by a decimal number and optional % symbol
            match = re.match(r'^(.*?)\s+([\d\.]+)(%?)$', part)
            if match:
                name = match.group(1).strip()
                val = Decimal(match.group(2))
                res[self.map_user_name(name)] = val
        return res

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        csv_path = os.path.join('backend', 'data', 'Expenses_Export.csv')

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found at {csv_path}"))
            return

        self.stdout.write(f"Starting import from {csv_path} (dry-run={dry_run})...")

        try:
            with transaction.atomic():
                self.run_import(csv_path)
                if dry_run:
                    self.stdout.write(self.style.WARNING("DRY RUN: Rolling back transaction..."))
                    raise transaction.TransactionManagementError("Dry run rollback trigger")
            self.stdout.write(self.style.SUCCESS("Import completed successfully!"))
        except transaction.TransactionManagementError:
            self.stdout.write(self.style.SUCCESS("Dry run rollback executed. No database changes were saved."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {str(e)}"))
            raise e

    def run_import(self, csv_path):
        # Fetch group "The Flat", create if missing
        aisha = self.get_or_create_user('Aisha')
        group, _ = Group.objects.get_or_create(
            name='The Flat',
            defaults={'created_by': aisha}
        )

        # Set of seen unique keys (date, amount, description) to catch duplicate rows
        seen_keys = set()

        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_idx, row in enumerate(reader, start=2):
                description = row['description'].strip()
                raw_amount = row['amount'].strip().replace(',', '')
                raw_date = row['date'].strip()
                
                # Check for skipped / corrected transactions
                if not raw_amount or Decimal(raw_amount) == 0:
                    self.stdout.write(f"Row {row_idx}: Skipping zero-amount expense '{description}'")
                    continue
                
                # Check duplicate of Marina Bites (Row 6)
                if description.lower() == 'dinner - marina bites' and raw_date == '08-02-2026':
                    self.stdout.write(f"Row {row_idx}: Skipping duplicate dinner entry '{description}'")
                    continue

                # Check Thalassa double log (skip Aisha's 2400 Thalassa, keep Rohan's 2450)
                if description == 'Dinner at Thalassa' and raw_amount == '2400' and raw_date == '11-03-2026':
                    self.stdout.write(f"Row {row_idx}: Skipping wrong Thalassa dinner entry '{description}'")
                    continue

                # Parse basic values
                date = self.parse_csv_date(raw_date, description)
                amount = Decimal(raw_amount)
                currency = row['currency'].strip() or 'INR'

                # Currency conversion (USD to INR @ 83.00)
                if currency == 'USD':
                    amount = (amount * Decimal('83.00')).quantize(Decimal('0.01'))
                    currency = 'INR'

                # Clean payer name and map to user
                payer_name = row['paid_by'].strip()
                if not payer_name:
                    # Default payer to Aisha when empty (Row 13)
                    payer = self.get_or_create_user('Aisha')
                    self.stdout.write(f"Row {row_idx}: Defaulting empty payer to Aisha for '{description}'")
                else:
                    payer = self.get_or_create_user(payer_name)

                # Add payer to group members if not already in there
                if not group.members.filter(id=payer.id).exists():
                    group.members.add(payer)

                # Check if this row is actually a settlement (Rohan paid Aisha back / Sam deposit share)
                split_type = row['split_type'].strip().lower()
                split_with_str = row['split_with'].strip()

                if not split_type or 'paid aisha back' in description.lower() or 'deposit share' in description.lower():
                    # Process as Settlement
                    recipient_name = split_with_str.split(';')[0]
                    recipient = self.get_or_create_user(recipient_name)
                    
                    if not group.members.filter(id=recipient.id).exists():
                        group.members.add(recipient)

                    settlement = Settlement.objects.create(
                        group=group,
                        from_user=payer,
                        to_user=recipient,
                        amount=amount,
                        date=date
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_idx}: Imported Settlement: {payer.name} paid {recipient.name} INR {amount} on {date}"
                    ))
                    continue

                # Process as regular Expense
                participants = [self.get_or_create_user(name) for name in split_with_str.split(';') if name.strip()]
                for p in participants:
                    if not group.members.filter(id=p.id).exists():
                        group.members.add(p)

                # Deduplicate exact duplicate inserts (redundant rows)
                dup_key = (date, amount, description)
                if dup_key in seen_keys:
                    self.stdout.write(f"Row {row_idx}: Skipping redundant duplicate expense '{description}'")
                    continue
                seen_keys.add(dup_key)

                # Parse splits and details
                split_details = self.parse_split_details(row['split_details'])
                
                prepared_shares = []
                for p in participants:
                    raw_input_value = None
                    if split_type == 'unequal':
                        raw_input_value = split_details.get(p.name, Decimal('0.00'))
                    elif split_type == 'percentage':
                        raw_input_value = split_details.get(p.name, Decimal('0.00'))
                    elif split_type == 'share':
                        raw_input_value = split_details.get(p.name, Decimal('1.00'))
                    
                    prepared_shares.append({
                        'user_id': p.id,
                        'raw_input_value': raw_input_value
                    })

                # Calculate shares using our robust split-math engine
                calculated_shares = calculate_splits(amount, split_type, prepared_shares)

                # Save Expense
                expense = Expense.objects.create(
                    group=group,
                    payer=payer,
                    amount=amount,
                    currency=currency,
                    description=description,
                    date=date,
                    split_type=split_type
                )

                # Save shares
                for cs in calculated_shares:
                    ExpenseShare.objects.create(
                        expense=expense,
                        user_id=cs['user_id'],
                        owed_amount=cs['owed_amount'],
                        raw_input_value=cs['raw_input_value']
                    )

                self.stdout.write(f"Row {row_idx}: Imported Expense '{description}' (INR {amount}, split={split_type})")

        group.save()

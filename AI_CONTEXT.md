# AI Context: Splitwise Clone MVP

This is an  internship assignment to build a simplified Splitwise clone.

## Tech Stack
- **Backend**: Django REST Framework + SQLite (local) / PostgreSQL (prod, Render).
- **Frontend**: React (Vite + JS) + Vanilla CSS, deployed on Vercel.
- **Authentication**: Email + password login, JWT-based using SimpleJWT.

## Scope & Core Rules

### 1. Group & Users
- We start with one group: "The Flat".
- 6 initial users: Aisha, Rohan, Priya, Meera, Dev, Sam.
- Standard CRUD to add/remove users from the group.
- Group tracks `created_by` and `created_at`.

### 2. Expenses & Split Math
- Every expense belongs to a group.
- Fields: payer, total amount, currency (fixed to INR), description, date, split_type.
- Per-participant line items (`ExpenseShare`) tracking how much each user owes.
- **ExpenseShare** also tracks the raw split input (like percentage or share count) so the UI can rebuild the state.
- **Split types**:
  - `equal`: total / n.
  - `unequal`: exact amounts per person (must sum to total).
  - `percentage`: exact percentage per person (must sum to 100 after normalization).
  - `share`: ratio-based amounts proportional to shares.

### 3. Balances & Settlements
- Calculate net balance per user per group: (amount they paid) - (amount they owe) + (settlements).
- Generate a simplified "who owes whom" set of transactions.
- Settlements live in a separate table (`from_user`, `to_user`, `amount`, `date`, `group`) and offset balances directly.

### 4. Expense Chat
- Messages per expense (`sender`, `text`, `timestamp`).
- Polling-based, no WebSockets (timeline tradeoff, keep it simple).

### 5. Out of Scope (Future Work)
- Multi-currency live conversion.
- Push notifications.
- AI-based receipt reading or features.
- Membership history over time (balances assume static current members).

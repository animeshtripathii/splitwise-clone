# Build Plan

Execution plan for the Splitwise Clone MVP.

## Phase 1: Scaffolding & Config (Current)
- [x] Git initialization.
- [x] Documentation setup (`AI_CONTEXT.md`, `DECISIONS.md`, `BUILD_PLAN.md`, `SCOPE.md`).
- [ ] Scaffold Django project under `/backend`.
- [ ] Configure database (SQLite local, Postgres prod via env), CORS, SimpleJWT, and settings.
- [ ] Create Render deploy config files (`render.yaml`, `build.sh`, `gunicorn.conf.py`).
- [ ] Scaffold React app under `/frontend`.
- [ ] Commit initial skeleton.

## Phase 2: Schema, Models & Local Migrations
- [ ] Build models: Custom User, Group, Expense, ExpenseShare, Settlement, ChatMessage.
- [ ] Generate and run migrations locally.
- [ ] Seed script for initial 6 users (Aisha, Rohan, Priya, Meera, Dev, Sam) and default group "The Flat".
- [ ] Push skeleton backend to GitHub and deploy to Render to verify Postgres migrations work.

## Phase 3: Auth & Backend Business Logic APIs
- [ ] Auth endpoints (JWT login/refresh/register).
- [ ] Group member CRUD (add/remove from group).
- [ ] Expense CRUD:
  - Implement split calculations: Equal, Unequal, Percentage, Share.
  - Store calculations in `ExpenseShare`.
- [ ] Settlements CRUD (offsets balances).

## Phase 4: Balances & Who Owes Whom Algorithm
- [ ] Balance engine: Calculate net balance per member in the group.
- [ ] Simplification engine: Compute "who owes whom" set of transactions.
- [ ] Polling-friendly chat APIs for expenses.

## Phase 5: React Frontend UI Development
- [ ] Auth pages (Login, Signup).
- [ ] Dashboard & Group Page:
  - List of group members.
  - Net balances display.
  - Simplified "who owes whom" list.
  - Settlements trigger form.
- [ ] Expense Form:
  - Support adding expenses.
  - Dynamic forms for Equal, Unequal, Percentage, and Share splitting.
- [ ] Chat panel under each expense detail modal.

## Phase 6: Final Deployment & Verification
- [ ] Run backend tests.
- [ ] Deploy Vercel frontend.
- [ ] End-to-end user testing.

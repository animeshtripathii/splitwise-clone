# Build Plan

Execution plan for the Splitwise Clone MVP.

## Phase 1: Scaffolding & Config (Current)
- [x] Git initialization.
- [x] Documentation setup (`AI_CONTEXT.md`, `DECISIONS.md`, `BUILD_PLAN.md`, `SCOPE.md`).
- [x] Scaffold Django project under `/backend`.
- [x] Configure database (SQLite local, Postgres prod via env), CORS, SimpleJWT, and settings.
- [x] Create Render deploy config files (`render.yaml`, `build.sh`, `gunicorn.conf.py`).
- [x] Scaffold React app under `/frontend`.
- [x] Commit initial skeleton.

## Phase 2: Schema, Models & Local Migrations
- [x] Build models: Custom User, Group, Expense, ExpenseShare, Settlement, ChatMessage.
- [x] Generate and run migrations locally.
- [x] Seed script for initial 6 users (Aisha, Rohan, Priya, Meera, Dev, Sam) and default group "The Flat".
- [x] Push skeleton backend to GitHub and [/] deploy to Render to verify Postgres migrations work (run right after Auth + Group CRUD).

## Phase 3: Auth & Backend Business Logic APIs
- [x] Auth endpoints (JWT login/refresh/register/me).
- [x] Group member CRUD (add/remove from group).
- [x] Expense CRUD:
  - [x] Implement split calculations: Equal, Unequal, Percentage, Share.
  - [x] Store calculations in `ExpenseShare`.
- [x] Settlements CRUD (offsets balances).
- [ ] Finalize SCOPE.md with the anomaly log and final schema/ERD, then write a Django management command that imports Expenses_Export.csv (place it in backend/data/) applying every decision in SCOPE.md — including the two settlement rows, percentage normalization, name aliasing, date parsing, and currency conversion. Support --dry-run.

## Phase 4: Balances & Who Owes Whom Algorithm
- [x] Balance engine: Calculate net balance per member in the group.
- [x] Simplification engine: Compute "who owes whom" set of transactions.
- [x] Polling-friendly chat APIs for expenses.

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

# Architecture Decisions

### 1. Local Database
- **Options**: Local PostgreSQL vs Local SQLite.
- **Choice**: SQLite local, PostgreSQL on Render prod.
- **Why**: SQLite is zero-config and runs out of the box. Saves setup time tonight. Render will use PostgreSQL via `DATABASE_URL`.

### 2. React Stack
- **Options**: Vite + TypeScript vs Vite + JavaScript.
- **Choice**: Vite + JavaScript.
- **Why**: Avoids compile-time types overhead. We're on a deadline; speed is key.

### 3. User Authentication & Custom Model
- **Options**: Default Django User vs Custom User.
- **Choice**: Custom User with `email` as `USERNAME_FIELD`.
- **Why**: Email + password login is standard. Default Django username field is annoying to work around in client forms.

### 4. Chat implementation
- **Options**: WebSockets (Django Channels) vs Polling (HTTP).
- **Choice**: HTTP polling.
- **Why**: Channels/WebSockets require Redis and complex ASGI configuration, which adds points of failure for deployment on Render. Polling is simple, fast, and robust enough for this assignment.

### 5. Group Metadata
- **Options**: Minimal group fields vs group with audit fields.
- **Choice**: Add `created_by` and `created_at` to Group.
- **Why**: Needed to show who created the group and when it started, providing basic audit context.

### 6. Expense Split Preservation
- **Options**: Calculate and store only `owed_amount` vs store `owed_amount` + raw split input.
- **Choice**: Store `owed_amount` + nullable raw split input value.
- **Why**: Allows the UI to render the original input values (like "30%" or "2 shares") rather than reverse-engineering them from the calculated owed INR amount.

#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
python backend/manage.py migrate

# Seed initial 6 users and group
python backend/manage.py seed_data

# Collect static files
python backend/manage.py collectstatic --no-input

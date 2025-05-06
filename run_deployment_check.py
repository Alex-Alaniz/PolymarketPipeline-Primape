#!/usr/bin/env python3

"""
Run the deployment approval check for any pending markets.
"""

from main import app
import check_deployment_approvals

# Use application context for database operations
with app.app_context():
    # Check for approvals
    pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
    print(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
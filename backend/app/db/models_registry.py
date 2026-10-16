"""
Models registry for Alembic to detect all models.

This file imports all models so that Alembic can detect them when generating migrations.
"""

# Import all models here so that Alembic can detect them
from app.modules.genes.models import Gene
from app.modules.users.models import User

# Add other models as they are created
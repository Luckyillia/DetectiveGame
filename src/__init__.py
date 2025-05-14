# src/__init__.py

# This file can include initialization code for the entire package, if needed.
# For example, import key modules to make them available directly from the package.

# Import necessary classes and modules from submodules
from .ui.user_ui import UserUI
from src.services.user.user_service import UserService
from .models.user import User

# Define the public API of the package
# The following line specifies what will be available when importing from this package.
__all__ = ['UserUI', 'UserService', 'User']
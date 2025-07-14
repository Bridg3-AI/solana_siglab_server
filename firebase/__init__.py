"""
Firebase integration module for Solana SigLab Server
Centralizes all Firebase-related functionality
"""

from .core.firebase_init import get_db, get_storage, verify_token, firebase_app
from .auth.middleware import AuthMiddleware
from .database.services import FirestoreService
from .storage.services import StorageService

__all__ = [
    "get_db",
    "get_storage", 
    "verify_token",
    "firebase_app",
    "AuthMiddleware",
    "FirestoreService",
    "StorageService"
]
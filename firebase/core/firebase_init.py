"""
Firebase initialization and configuration management
Following Firebase 2025 best practices for Python backends
"""
from firebase_admin import initialize_app, firestore, storage, auth
import firebase_admin
from typing import Optional
import os


class FirebaseApp:
    """Singleton Firebase app manager for cold start optimization"""
    _app: Optional[firebase_admin.App] = None
    _db: Optional[firestore.Client] = None
    _storage: Optional[storage.Client] = None
    
    @classmethod
    def get_app(cls) -> firebase_admin.App:
        """Get or initialize Firebase app (singleton pattern for cold start optimization)"""
        if cls._app is None:
            try:
                # Try to get existing app first
                cls._app = firebase_admin.get_app()
            except ValueError:
                # Initialize new app if none exists
                cls._app = initialize_app()
        return cls._app
    
    @classmethod
    def get_firestore(cls) -> firestore.Client:
        """Get Firestore client (cached for performance)"""
        if cls._db is None:
            cls.get_app()  # Ensure app is initialized
            cls._db = firestore.client()
        return cls._db
    
    @classmethod
    def get_storage(cls) -> storage.Client:
        """Get Storage client (cached for performance)"""
        if cls._storage is None:
            cls.get_app()  # Ensure app is initialized
            cls._storage = storage.Client()
        return cls._storage
    
    @classmethod
    def verify_auth_token(cls, token: str) -> dict:
        """Verify Firebase Auth token"""
        cls.get_app()  # Ensure app is initialized
        return auth.verify_id_token(token)


# Global instances for module-level access (cold start optimization)
firebase_app = FirebaseApp()

# Convenience functions
def get_db() -> firestore.Client:
    """Get Firestore database client"""
    return firebase_app.get_firestore()

def get_storage() -> storage.Client:
    """Get Firebase Storage client"""
    return firebase_app.get_storage()

def verify_token(token: str) -> dict:
    """Verify Firebase Auth token"""
    return firebase_app.verify_auth_token(token)
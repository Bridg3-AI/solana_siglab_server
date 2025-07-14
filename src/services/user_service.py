"""
User management service
"""
from firebase_admin import firestore
from typing import Dict, List, Any, Optional


class UserService:
    def __init__(self, firestore_client):
        self.db = firestore_client
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users from Firestore"""
        try:
            users_ref = self.db.collection("users")
            users = []
            for doc in users_ref.stream():
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                users.append(user_data)
            return users
        except Exception as e:
            raise Exception(f"Failed to fetch users: {str(e)}")
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user"""
        try:
            # Add timestamp
            user_data["created_at"] = firestore.SERVER_TIMESTAMP
            user_data["updated_at"] = firestore.SERVER_TIMESTAMP
            
            # Add to Firestore
            doc_ref = self.db.collection("users").add(user_data)
            return doc_ref[1].id
        except Exception as e:
            raise Exception(f"Failed to create user: {str(e)}")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID"""
        try:
            doc_ref = self.db.collection("users").document(user_id)
            doc = doc_ref.get()
            if doc.exists:
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                return user_data
            return None
        except Exception as e:
            raise Exception(f"Failed to fetch user: {str(e)}")
    
    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update a user"""
        try:
            user_data["updated_at"] = firestore.SERVER_TIMESTAMP
            doc_ref = self.db.collection("users").document(user_id)
            doc_ref.update(user_data)
            return True
        except Exception as e:
            raise Exception(f"Failed to update user: {str(e)}")
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            doc_ref = self.db.collection("users").document(user_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete user: {str(e)}")
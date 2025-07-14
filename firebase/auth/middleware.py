"""
Authentication middleware
"""
from firebase_admin import auth
from firebase_functions import https_fn
from typing import Optional, Dict, Any
import json


class AuthMiddleware:
    @staticmethod
    def verify_token(request: https_fn.Request) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token from request headers"""
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None
            
            token = auth_header.split('Bearer ')[1]
            
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None
    
    @staticmethod
    def require_auth(request: https_fn.Request) -> Optional[https_fn.Response]:
        """Require authentication and return error response if not authenticated"""
        user = AuthMiddleware.verify_token(request)
        if not user:
            return https_fn.Response(
                json.dumps({"error": "Authentication required"}),
                status=401,
                headers={"Content-Type": "application/json"}
            )
        return None  # Authentication successful
    
    @staticmethod
    def get_user_from_request(request: https_fn.Request) -> Optional[Dict[str, Any]]:
        """Get user information from request if authenticated"""
        return AuthMiddleware.verify_token(request)
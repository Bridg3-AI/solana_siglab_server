"""
Validation utilities
"""
import re
from typing import Optional


class Validator:
    @staticmethod
    def is_valid_solana_address(address: str) -> bool:
        """Validate Solana address format"""
        if not address or not isinstance(address, str):
            return False
        
        # Solana addresses are base58 encoded and typically 32-44 characters
        pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
        return bool(re.match(pattern, address))
    
    @staticmethod
    def is_valid_transaction_signature(signature: str) -> bool:
        """Validate transaction signature format"""
        if not signature or not isinstance(signature, str):
            return False
        
        # Transaction signatures are typically 64-88 characters
        pattern = r'^[1-9A-HJ-NP-Za-km-z]{64,88}$'
        return bool(re.match(pattern, signature))
    
    @staticmethod
    def is_valid_session_id(session_id: str) -> bool:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            return False
        
        # Allow alphanumeric, hyphens, underscores, 1-100 characters
        pattern = r'^[a-zA-Z0-9_-]{1,100}$'
        return bool(re.match(pattern, session_id))
    
    @staticmethod
    def is_valid_network(network: str) -> bool:
        """Validate Solana network name"""
        valid_networks = ["mainnet-beta", "testnet", "devnet"]
        return network in valid_networks
    
    @staticmethod
    def extract_solana_address(text: str) -> Optional[str]:
        """Extract Solana address from text"""
        if not text:
            return None
        
        pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
        matches = re.findall(pattern, text)
        return matches[0] if matches else None
    
    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters and limit length
        sanitized = re.sub(r'[<>"\']', '', str(text))
        return sanitized[:max_length]
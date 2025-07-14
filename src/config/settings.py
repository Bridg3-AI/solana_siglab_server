"""
Application configuration settings
"""
import os
from typing import Dict, Any


class Settings:
    # Firebase Configuration
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "solana-siglab")
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    
    # Solana Configuration
    SOLANA_NETWORK = os.getenv("SOLANA_NETWORK", "mainnet-beta")
    SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    # Agent Configuration
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    ENABLE_MEMORY = os.getenv("ENABLE_MEMORY", "true").lower() == "true"
    MEMORY_TYPE = os.getenv("MEMORY_TYPE", "firestore")
    
    # API Configuration
    MAX_INSTANCES = int(os.getenv("MAX_INSTANCES", "10"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    @classmethod
    def get_agent_config(cls) -> Dict[str, Any]:
        """Get agent-specific configuration"""
        return {
            "network": cls.SOLANA_NETWORK,
            "rpc_url": cls.SOLANA_RPC_URL,
            "max_iterations": cls.MAX_ITERATIONS,
            "debug_mode": cls.DEBUG_MODE,
            "enable_memory": cls.ENABLE_MEMORY,
            "memory_type": cls.MEMORY_TYPE
        }
    
    @classmethod
    def get_firebase_config(cls) -> Dict[str, Any]:
        """Get Firebase-specific configuration"""
        return {
            "project_id": cls.FIREBASE_PROJECT_ID,
            "database_url": cls.FIREBASE_DATABASE_URL
        }


# Global settings instance
settings = Settings()
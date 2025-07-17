"""Configuration management for agents"""
import os
from typing import Optional


class AgentConfig:
    """Configuration class for agent settings"""
    
    def __init__(self):
        self.openai_api_key = self._get_openai_api_key()
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        self.max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
        self.timeout = int(os.getenv("AGENT_TIMEOUT", "30"))
        self.debug = os.getenv("AGENT_DEBUG", "false").lower() == "true"
    
    def _get_openai_api_key(self) -> str:
        """Get OpenAI API key from environment variable"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it or create a .env file with OPENAI_API_KEY=your-key"
            )
        return api_key
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Check required fields
            if not self.openai_api_key:
                return False
            
            # Check value ranges
            if not (0.0 <= self.temperature <= 2.0):
                return False
            
            if not (1 <= self.max_tokens <= 4000):
                return False
            
            if not (1 <= self.max_iterations <= 50):
                return False
            
            return True
        except Exception:
            return False
    
    def to_dict(self) -> dict:
        """Convert config to dictionary (excluding sensitive data)"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_iterations": self.max_iterations,
            "timeout": self.timeout,
            "debug": self.debug
        }


# Global config instance
_config: Optional[AgentConfig] = None


def get_config() -> AgentConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = AgentConfig()
    return _config


def load_env_file(env_file: str = ".env") -> None:
    """Load environment variables from file"""
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass  # .env file is optional
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")


# Auto-load .env file if it exists
load_env_file()
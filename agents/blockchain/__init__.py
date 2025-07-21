"""Blockchain integration module for Solana smart contracts"""

from .solana_client import SolanaClient
from .contract_deployer import ContractDeployer
from .transaction_manager import TransactionManager
from .oracle_client import OracleClient
from .token_manager import TokenManager

__all__ = [
    'SolanaClient',
    'ContractDeployer', 
    'TransactionManager',
    'OracleClient',
    'TokenManager'
]

# Version info
__version__ = "0.2.0"
__author__ = "Solana SigLab Team"
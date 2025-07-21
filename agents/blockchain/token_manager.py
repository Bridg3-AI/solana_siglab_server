"""SPL Token management for insurance contracts"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from spl.token.instructions import (
    create_mint, create_account, mint_to, transfer,
    MintToParams, TransferParams, CreateMintParams, CreateAccountParams
)
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.client import Token
from .solana_client import SolanaClient
from ..core.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class TokenInfo:
    """SPL Token information"""
    mint_address: str
    name: str
    symbol: str
    decimals: int
    total_supply: float
    authority: str
    freeze_authority: Optional[str]
    is_initialized: bool
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'mint_address': self.mint_address,
            'name': self.name,
            'symbol': self.symbol,
            'decimals': self.decimals,
            'total_supply': self.total_supply,
            'authority': self.authority,
            'freeze_authority': self.freeze_authority,
            'is_initialized': self.is_initialized,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class TokenAccount:
    """Token account information"""
    address: str
    mint: str
    owner: str
    amount: float
    decimals: int
    is_initialized: bool
    is_frozen: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'address': self.address,
            'mint': self.mint,
            'owner': self.owner,
            'amount': self.amount,
            'decimals': self.decimals,
            'is_initialized': self.is_initialized,
            'is_frozen': self.is_frozen
        }

@dataclass
class TokenTransfer:
    """Token transfer information"""
    signature: str
    from_address: str
    to_address: str
    mint: str
    amount: float
    decimals: int
    timestamp: datetime
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'signature': self.signature,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'mint': self.mint,
            'amount': self.amount,
            'decimals': self.decimals,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status
        }

class TokenManager:
    """SPL Token management class"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        
        # Common SPL token addresses
        self.well_known_tokens = {
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "SOL": "So11111111111111111111111111111111111111112",  # Wrapped SOL
            "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
            "SRM": "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt"
        }
    
    def get_token_address(self, symbol: str) -> Optional[str]:
        """Get token address by symbol"""
        return self.well_known_tokens.get(symbol.upper())
    
    async def create_token_mint(self, mint_keypair: Keypair, 
                              authority: Keypair,
                              decimals: int = 6,
                              freeze_authority: Optional[Keypair] = None) -> str:
        """Create a new SPL token mint"""
        try:
            async with SolanaClient(self.cluster) as client:
                # Get minimum rent for mint account
                rent_response = await client.client.get_minimum_balance_for_rent_exemption(82)
                min_rent = rent_response.value
                
                # Create mint account instruction
                create_mint_instruction = create_mint(
                    CreateMintParams(
                        program_id=TOKEN_PROGRAM_ID,
                        mint=mint_keypair.public_key,
                        decimals=decimals,
                        mint_authority=authority.public_key,
                        freeze_authority=freeze_authority.public_key if freeze_authority else None
                    )
                )
                
                # Create system account instruction
                from solana.system_program import create_account, CreateAccountParams
                create_account_instruction = create_account(
                    CreateAccountParams(
                        from_pubkey=authority.public_key,
                        new_account_pubkey=mint_keypair.public_key,
                        lamports=min_rent,
                        space=82,
                        program_id=TOKEN_PROGRAM_ID
                    )
                )
                
                # Create transaction
                transaction = Transaction()
                transaction.add(create_account_instruction)
                transaction.add(create_mint_instruction)
                
                # Send transaction
                signature = await client.send_transaction(transaction, [authority, mint_keypair])
                
                # Wait for confirmation
                confirmed = await client.wait_for_confirmation(signature)
                
                if confirmed:
                    logger.info(f"Token mint created: {mint_keypair.public_key}")
                    return str(mint_keypair.public_key)
                else:
                    raise Exception("Token mint creation failed")
                    
        except Exception as e:
            logger.error(f"Error creating token mint: {e}")
            raise
    
    async def create_token_account(self, owner: Keypair, 
                                 mint: Union[str, PublicKey],
                                 account_keypair: Optional[Keypair] = None) -> str:
        """Create a new token account"""
        try:
            if isinstance(mint, str):
                mint = PublicKey(mint)
            
            if not account_keypair:
                account_keypair = Keypair()
            
            async with SolanaClient(self.cluster) as client:
                # Get minimum rent for token account
                rent_response = await client.client.get_minimum_balance_for_rent_exemption(165)
                min_rent = rent_response.value
                
                # Create account instruction
                from solana.system_program import create_account, CreateAccountParams
                create_account_instruction = create_account(
                    CreateAccountParams(
                        from_pubkey=owner.public_key,
                        new_account_pubkey=account_keypair.public_key,
                        lamports=min_rent,
                        space=165,
                        program_id=TOKEN_PROGRAM_ID
                    )
                )
                
                # Initialize account instruction
                init_account_instruction = create_account(
                    CreateAccountParams(
                        account=account_keypair.public_key,
                        mint=mint,
                        owner=owner.public_key,
                        program_id=TOKEN_PROGRAM_ID
                    )
                )
                
                # Create transaction
                transaction = Transaction()
                transaction.add(create_account_instruction)
                transaction.add(init_account_instruction)
                
                # Send transaction
                signature = await client.send_transaction(transaction, [owner, account_keypair])
                
                # Wait for confirmation
                confirmed = await client.wait_for_confirmation(signature)
                
                if confirmed:
                    logger.info(f"Token account created: {account_keypair.public_key}")
                    return str(account_keypair.public_key)
                else:
                    raise Exception("Token account creation failed")
                    
        except Exception as e:
            logger.error(f"Error creating token account: {e}")
            raise
    
    async def mint_tokens(self, mint: Union[str, PublicKey],
                         authority: Keypair,
                         destination: Union[str, PublicKey],
                         amount: float,
                         decimals: int = 6) -> str:
        """Mint tokens to a destination account"""
        try:
            if isinstance(mint, str):
                mint = PublicKey(mint)
            if isinstance(destination, str):
                destination = PublicKey(destination)
            
            # Convert amount to token units
            token_amount = int(amount * (10 ** decimals))
            
            async with SolanaClient(self.cluster) as client:
                # Create mint instruction
                mint_instruction = mint_to(
                    MintToParams(
                        program_id=TOKEN_PROGRAM_ID,
                        mint=mint,
                        dest=destination,
                        mint_authority=authority.public_key,
                        amount=token_amount
                    )
                )
                
                # Create transaction
                transaction = Transaction()
                transaction.add(mint_instruction)
                
                # Send transaction
                signature = await client.send_transaction(transaction, [authority])
                
                # Wait for confirmation
                confirmed = await client.wait_for_confirmation(signature)
                
                if confirmed:
                    logger.info(f"Minted {amount} tokens to {destination}")
                    return signature
                else:
                    raise Exception("Token minting failed")
                    
        except Exception as e:
            logger.error(f"Error minting tokens: {e}")
            raise
    
    async def transfer_tokens(self, from_account: Union[str, PublicKey],
                            to_account: Union[str, PublicKey],
                            owner: Keypair,
                            amount: float,
                            decimals: int = 6) -> str:
        """Transfer tokens between accounts"""
        try:
            if isinstance(from_account, str):
                from_account = PublicKey(from_account)
            if isinstance(to_account, str):
                to_account = PublicKey(to_account)
            
            # Convert amount to token units
            token_amount = int(amount * (10 ** decimals))
            
            async with SolanaClient(self.cluster) as client:
                # Create transfer instruction
                transfer_instruction = transfer(
                    TransferParams(
                        program_id=TOKEN_PROGRAM_ID,
                        source=from_account,
                        dest=to_account,
                        owner=owner.public_key,
                        amount=token_amount
                    )
                )
                
                # Create transaction
                transaction = Transaction()
                transaction.add(transfer_instruction)
                
                # Send transaction
                signature = await client.send_transaction(transaction, [owner])
                
                # Wait for confirmation
                confirmed = await client.wait_for_confirmation(signature)
                
                if confirmed:
                    logger.info(f"Transferred {amount} tokens from {from_account} to {to_account}")
                    return signature
                else:
                    raise Exception("Token transfer failed")
                    
        except Exception as e:
            logger.error(f"Error transferring tokens: {e}")
            raise
    
    async def get_token_info(self, mint: Union[str, PublicKey]) -> Optional[TokenInfo]:
        """Get token mint information"""
        try:
            if isinstance(mint, str):
                mint = PublicKey(mint)
            
            async with SolanaClient(self.cluster) as client:
                account_info = await client.get_account_info(mint)
                
                if not account_info:
                    return None
                
                # Parse mint account data (simplified)
                # In production, use SPL token library for proper parsing
                return await self._parse_mint_data(account_info, str(mint))
                
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None
    
    async def _parse_mint_data(self, account_info, mint_address: str) -> TokenInfo:
        """Parse token mint account data"""
        # This is a simplified implementation
        # In production, use proper SPL token data parsing
        
        return TokenInfo(
            mint_address=mint_address,
            name="Insurance Token",
            symbol="INSUR",
            decimals=6,
            total_supply=0.0,
            authority=account_info.owner,
            freeze_authority=None,
            is_initialized=True,
            created_at=datetime.now()
        )
    
    async def get_token_account_info(self, account: Union[str, PublicKey]) -> Optional[TokenAccount]:
        """Get token account information"""
        try:
            if isinstance(account, str):
                account = PublicKey(account)
            
            async with SolanaClient(self.cluster) as client:
                account_info = await client.get_account_info(account)
                
                if not account_info:
                    return None
                
                # Parse token account data (simplified)
                return await self._parse_token_account_data(account_info, str(account))
                
        except Exception as e:
            logger.error(f"Error getting token account info: {e}")
            return None
    
    async def _parse_token_account_data(self, account_info, account_address: str) -> TokenAccount:
        """Parse token account data"""
        # This is a simplified implementation
        # In production, use proper SPL token data parsing
        
        return TokenAccount(
            address=account_address,
            mint="unknown",
            owner=account_info.owner,
            amount=0.0,
            decimals=6,
            is_initialized=True,
            is_frozen=False
        )
    
    async def get_token_balance(self, account: Union[str, PublicKey]) -> float:
        """Get token balance for an account"""
        try:
            account_info = await self.get_token_account_info(account)
            return account_info.amount if account_info else 0.0
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return 0.0
    
    async def get_token_accounts_by_owner(self, owner: Union[str, PublicKey]) -> List[TokenAccount]:
        """Get all token accounts owned by an address"""
        try:
            if isinstance(owner, str):
                owner = PublicKey(owner)
            
            async with SolanaClient(self.cluster) as client:
                token_accounts = await client.get_token_accounts(owner)
                
                accounts = []
                for account_data in token_accounts:
                    account = TokenAccount(
                        address=account_data['address'],
                        mint=account_data['mint'],
                        owner=account_data['owner'],
                        amount=float(account_data['token_amount']['amount']) / (10 ** account_data['token_amount']['decimals']),
                        decimals=account_data['token_amount']['decimals'],
                        is_initialized=True,
                        is_frozen=False
                    )
                    accounts.append(account)
                
                return accounts
                
        except Exception as e:
            logger.error(f"Error getting token accounts by owner: {e}")
            return []
    
    async def create_insurance_token(self, authority: Keypair,
                                   name: str,
                                   symbol: str,
                                   decimals: int = 6,
                                   initial_supply: float = 0) -> TokenInfo:
        """Create a new insurance token"""
        try:
            # Generate mint keypair
            mint_keypair = Keypair()
            
            # Create token mint
            mint_address = await self.create_token_mint(
                mint_keypair=mint_keypair,
                authority=authority,
                decimals=decimals
            )
            
            # Create token info
            token_info = TokenInfo(
                mint_address=mint_address,
                name=name,
                symbol=symbol,
                decimals=decimals,
                total_supply=initial_supply,
                authority=str(authority.public_key),
                freeze_authority=None,
                is_initialized=True,
                created_at=datetime.now()
            )
            
            logger.info(f"Created insurance token: {symbol} ({mint_address})")
            
            return token_info
            
        except Exception as e:
            logger.error(f"Error creating insurance token: {e}")
            raise
    
    async def setup_insurance_token_distribution(self, 
                                               token_info: TokenInfo,
                                               authority: Keypair,
                                               distribution_plan: Dict[str, float]) -> List[str]:
        """Set up initial token distribution"""
        try:
            signatures = []
            
            for recipient, amount in distribution_plan.items():
                # Create token account for recipient
                recipient_pubkey = PublicKey(recipient)
                account_keypair = Keypair()
                
                account_address = await self.create_token_account(
                    owner=authority,  # Authority creates account
                    mint=token_info.mint_address,
                    account_keypair=account_keypair
                )
                
                # Mint tokens to recipient account
                signature = await self.mint_tokens(
                    mint=token_info.mint_address,
                    authority=authority,
                    destination=account_address,
                    amount=amount,
                    decimals=token_info.decimals
                )
                
                signatures.append(signature)
                
                logger.info(f"Distributed {amount} {token_info.symbol} to {recipient}")
            
            return signatures
            
        except Exception as e:
            logger.error(f"Error setting up token distribution: {e}")
            raise
    
    async def get_token_transfer_history(self, account: Union[str, PublicKey],
                                       limit: int = 10) -> List[TokenTransfer]:
        """Get token transfer history for an account"""
        try:
            if isinstance(account, str):
                account = PublicKey(account)
            
            async with SolanaClient(self.cluster) as client:
                signatures = await client.get_signatures_for_address(account, limit)
                
                transfers = []
                for signature in signatures:
                    tx_info = await client.get_transaction_info(signature)
                    
                    if tx_info and tx_info.status == "success":
                        # Parse transaction for token transfers
                        transfer = await self._parse_token_transfer(tx_info)
                        if transfer:
                            transfers.append(transfer)
                
                return transfers
                
        except Exception as e:
            logger.error(f"Error getting token transfer history: {e}")
            return []
    
    async def _parse_token_transfer(self, tx_info) -> Optional[TokenTransfer]:
        """Parse transaction for token transfer information"""
        # This is a simplified implementation
        # In production, parse actual transaction data
        
        return TokenTransfer(
            signature=tx_info.signature,
            from_address="unknown",
            to_address="unknown",
            mint="unknown",
            amount=0.0,
            decimals=6,
            timestamp=tx_info.block_time or datetime.now(),
            status=tx_info.status
        )


# Convenience functions for direct use
async def create_insurance_token(authority: Keypair,
                               name: str,
                               symbol: str,
                               decimals: int = 6,
                               cluster: str = "mainnet-beta") -> TokenInfo:
    """Create a new insurance token"""
    token_manager = TokenManager(cluster)
    return await token_manager.create_insurance_token(authority, name, symbol, decimals)

async def get_token_balance(account: Union[str, PublicKey],
                          cluster: str = "mainnet-beta") -> float:
    """Get token balance for an account"""
    token_manager = TokenManager(cluster)
    return await token_manager.get_token_balance(account)

async def transfer_tokens(from_account: Union[str, PublicKey],
                        to_account: Union[str, PublicKey],
                        owner: Keypair,
                        amount: float,
                        decimals: int = 6,
                        cluster: str = "mainnet-beta") -> str:
    """Transfer tokens between accounts"""
    token_manager = TokenManager(cluster)
    return await token_manager.transfer_tokens(from_account, to_account, owner, amount, decimals)
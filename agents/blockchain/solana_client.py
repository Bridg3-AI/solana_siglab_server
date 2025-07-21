"""Solana RPC client wrapper with advanced features"""
import logging
from typing import Dict, List, Optional, Any, Union
import json
import base64
from datetime import datetime, timedelta
from dataclasses import dataclass
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.rpc.core import RPCException
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.system_program import transfer, TransferParams
from solana.rpc.types import TxOpts
from ..core.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class NetworkInfo:
    """Solana network information"""
    cluster: str
    rpc_url: str
    websocket_url: str
    commitment: Commitment
    slot: int
    block_height: int
    block_time: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cluster': self.cluster,
            'rpc_url': self.rpc_url,
            'websocket_url': self.websocket_url,
            'commitment': str(self.commitment),
            'slot': self.slot,
            'block_height': self.block_height,
            'block_time': self.block_time.isoformat() if self.block_time else None
        }

@dataclass
class AccountInfo:
    """Solana account information"""
    address: str
    balance: float  # SOL
    owner: str
    executable: bool
    rent_epoch: int
    data_size: int
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'address': self.address,
            'balance': self.balance,
            'owner': self.owner,
            'executable': self.executable,
            'rent_epoch': self.rent_epoch,
            'data_size': self.data_size,
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class TransactionInfo:
    """Solana transaction information"""
    signature: str
    slot: int
    block_time: Optional[datetime]
    status: str  # success, failed, pending
    fee: float  # SOL
    log_messages: List[str]
    accounts: List[str]
    instructions: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'signature': self.signature,
            'slot': self.slot,
            'block_time': self.block_time.isoformat() if self.block_time else None,
            'status': self.status,
            'fee': self.fee,
            'log_messages': self.log_messages,
            'accounts': self.accounts,
            'instructions': self.instructions
        }

class SolanaClient:
    """Enhanced Solana RPC client with insurance-specific features"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.config = get_config()
        self.cluster = cluster
        self.rpc_url = self._get_rpc_url(cluster)
        self.websocket_url = self._get_websocket_url(cluster)
        self.commitment = Commitment("confirmed")
        self.client: Optional[AsyncClient] = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        
    def _get_rpc_url(self, cluster: str) -> str:
        """Get RPC URL for cluster"""
        urls = {
            "mainnet-beta": "https://api.mainnet-beta.solana.com",
            "devnet": "https://api.devnet.solana.com",
            "testnet": "https://api.testnet.solana.com",
            "localnet": "http://127.0.0.1:8899"
        }
        
        # Use custom RPC URL if configured
        if hasattr(self.config, 'solana_rpc_url') and self.config.solana_rpc_url:
            return self.config.solana_rpc_url
            
        return urls.get(cluster, urls["mainnet-beta"])
    
    def _get_websocket_url(self, cluster: str) -> str:
        """Get WebSocket URL for cluster"""
        urls = {
            "mainnet-beta": "wss://api.mainnet-beta.solana.com",
            "devnet": "wss://api.devnet.solana.com",
            "testnet": "wss://api.testnet.solana.com",
            "localnet": "ws://127.0.0.1:8900"
        }
        return urls.get(cluster, urls["mainnet-beta"])
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = AsyncClient(self.rpc_url, commitment=self.commitment)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.close()
    
    async def get_network_info(self) -> NetworkInfo:
        """Get network information"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            # Get cluster info
            cluster_nodes = await self.client.get_cluster_nodes()
            slot_response = await self.client.get_slot()
            block_height_response = await self.client.get_block_height()
            
            slot = slot_response.value
            block_height = block_height_response.value
            
            # Get block time
            block_time = None
            try:
                block_time_response = await self.client.get_block_time(slot)
                if block_time_response.value:
                    block_time = datetime.fromtimestamp(block_time_response.value)
            except Exception as e:
                logger.warning(f"Could not get block time: {e}")
            
            return NetworkInfo(
                cluster=self.cluster,
                rpc_url=self.rpc_url,
                websocket_url=self.websocket_url,
                commitment=self.commitment,
                slot=slot,
                block_height=block_height,
                block_time=block_time
            )
            
        except RPCException as e:
            logger.error(f"RPC error getting network info: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            raise
    
    async def get_account_info(self, address: Union[str, PublicKey]) -> Optional[AccountInfo]:
        """Get account information"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(address, str):
                address = PublicKey(address)
            
            response = await self.client.get_account_info(address)
            
            if not response.value:
                return None
            
            account = response.value
            
            return AccountInfo(
                address=str(address),
                balance=account.lamports / 1_000_000_000,  # Convert lamports to SOL
                owner=str(account.owner),
                executable=account.executable,
                rent_epoch=account.rent_epoch,
                data_size=len(account.data) if account.data else 0,
                last_updated=datetime.now()
            )
            
        except RPCException as e:
            logger.error(f"RPC error getting account info: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    async def get_balance(self, address: Union[str, PublicKey]) -> float:
        """Get account balance in SOL"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(address, str):
                address = PublicKey(address)
            
            response = await self.client.get_balance(address)
            return response.value / 1_000_000_000  # Convert lamports to SOL
            
        except RPCException as e:
            logger.error(f"RPC error getting balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise
    
    async def get_transaction_info(self, signature: str) -> Optional[TransactionInfo]:
        """Get transaction information"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            response = await self.client.get_transaction(signature)
            
            if not response.value:
                return None
            
            tx = response.value
            
            # Parse transaction status
            status = "success" if tx.meta.err is None else "failed"
            
            # Extract fee
            fee = tx.meta.fee / 1_000_000_000 if tx.meta.fee else 0.0
            
            # Extract log messages
            log_messages = tx.meta.log_messages or []
            
            # Extract accounts
            accounts = [str(acc) for acc in tx.transaction.message.account_keys]
            
            # Extract instructions
            instructions = []
            for instr in tx.transaction.message.instructions:
                instructions.append({
                    'program_id': str(accounts[instr.program_id_index]),
                    'accounts': [accounts[i] for i in instr.accounts],
                    'data': base64.b64encode(instr.data).decode() if instr.data else None
                })
            
            # Get block time
            block_time = None
            if tx.block_time:
                block_time = datetime.fromtimestamp(tx.block_time)
            
            return TransactionInfo(
                signature=signature,
                slot=tx.slot,
                block_time=block_time,
                status=status,
                fee=fee,
                log_messages=log_messages,
                accounts=accounts,
                instructions=instructions
            )
            
        except RPCException as e:
            logger.error(f"RPC error getting transaction info: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting transaction info: {e}")
            raise
    
    async def send_transaction(self, transaction: Transaction, 
                            signers: List[Keypair]) -> str:
        """Send transaction to the network"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            # Get recent blockhash
            recent_blockhash = await self.client.get_recent_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            # Sign transaction
            transaction.sign(*signers)
            
            # Send transaction
            response = await self.client.send_transaction(
                transaction, 
                opts=TxOpts(
                    skip_preflight=False,
                    preflight_commitment=self.commitment
                )
            )
            
            signature = response.value
            logger.info(f"Transaction sent: {signature}")
            
            return signature
            
        except RPCException as e:
            logger.error(f"RPC error sending transaction: {e}")
            raise
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise
    
    async def transfer_sol(self, from_keypair: Keypair, to_address: Union[str, PublicKey], 
                          amount: float) -> str:
        """Transfer SOL from one account to another"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(to_address, str):
                to_address = PublicKey(to_address)
            
            # Convert SOL to lamports
            lamports = int(amount * 1_000_000_000)
            
            # Create transfer instruction
            transfer_instruction = transfer(
                TransferParams(
                    from_pubkey=from_keypair.public_key,
                    to_pubkey=to_address,
                    lamports=lamports
                )
            )
            
            # Create transaction
            transaction = Transaction()
            transaction.add(transfer_instruction)
            
            # Send transaction
            signature = await self.send_transaction(transaction, [from_keypair])
            
            logger.info(f"Transferred {amount} SOL to {to_address}: {signature}")
            
            return signature
            
        except Exception as e:
            logger.error(f"Error transferring SOL: {e}")
            raise
    
    async def wait_for_confirmation(self, signature: str, 
                                  timeout: int = 60) -> bool:
        """Wait for transaction confirmation"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            import asyncio
            
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < timeout:
                tx_info = await self.get_transaction_info(signature)
                
                if tx_info:
                    if tx_info.status == "success":
                        logger.info(f"Transaction confirmed: {signature}")
                        return True
                    elif tx_info.status == "failed":
                        logger.error(f"Transaction failed: {signature}")
                        return False
                
                # Wait before checking again
                await asyncio.sleep(1)
            
            logger.warning(f"Transaction confirmation timeout: {signature}")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def get_token_accounts(self, owner: Union[str, PublicKey]) -> List[Dict[str, Any]]:
        """Get token accounts for an owner"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(owner, str):
                owner = PublicKey(owner)
            
            response = await self.client.get_token_accounts_by_owner(owner)
            
            token_accounts = []
            for account in response.value:
                token_accounts.append({
                    'address': str(account.pubkey),
                    'mint': account.account.data.parsed['info']['mint'],
                    'token_amount': account.account.data.parsed['info']['tokenAmount'],
                    'owner': str(owner)
                })
            
            return token_accounts
            
        except RPCException as e:
            logger.error(f"RPC error getting token accounts: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting token accounts: {e}")
            raise
    
    async def get_program_accounts(self, program_id: Union[str, PublicKey]) -> List[Dict[str, Any]]:
        """Get accounts owned by a program"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(program_id, str):
                program_id = PublicKey(program_id)
            
            response = await self.client.get_program_accounts(program_id)
            
            accounts = []
            for account in response.value:
                accounts.append({
                    'address': str(account.pubkey),
                    'owner': str(program_id),
                    'data_size': len(account.account.data),
                    'executable': account.account.executable,
                    'rent_epoch': account.account.rent_epoch,
                    'lamports': account.account.lamports
                })
            
            return accounts
            
        except RPCException as e:
            logger.error(f"RPC error getting program accounts: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting program accounts: {e}")
            raise
    
    async def get_signatures_for_address(self, address: Union[str, PublicKey], 
                                       limit: int = 10) -> List[str]:
        """Get recent signatures for an address"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            if isinstance(address, str):
                address = PublicKey(address)
            
            response = await self.client.get_signatures_for_address(address, limit=limit)
            
            signatures = []
            for sig_info in response.value:
                signatures.append(sig_info.signature)
            
            return signatures
            
        except RPCException as e:
            logger.error(f"RPC error getting signatures: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting signatures: {e}")
            raise
    
    async def estimate_transaction_cost(self, transaction: Transaction) -> float:
        """Estimate transaction cost in SOL"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use within async context manager.")
        
        try:
            # Get recent blockhash
            recent_blockhash = await self.client.get_recent_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            # Get fee for transaction
            response = await self.client.get_fee_for_message(transaction.compile_message())
            
            fee_lamports = response.value
            return fee_lamports / 1_000_000_000 if fee_lamports else 0.0
            
        except RPCException as e:
            logger.error(f"RPC error estimating cost: {e}")
            raise
        except Exception as e:
            logger.error(f"Error estimating cost: {e}")
            raise
    
    def get_explorer_url(self, signature_or_address: str, 
                        type: str = "tx") -> str:
        """Get Solana explorer URL"""
        base_urls = {
            "mainnet-beta": "https://explorer.solana.com",
            "devnet": "https://explorer.solana.com",
            "testnet": "https://explorer.solana.com"
        }
        
        base_url = base_urls.get(self.cluster, base_urls["mainnet-beta"])
        
        if type == "tx":
            url = f"{base_url}/tx/{signature_or_address}"
        elif type == "account":
            url = f"{base_url}/account/{signature_or_address}"
        else:
            url = f"{base_url}/address/{signature_or_address}"
        
        if self.cluster != "mainnet-beta":
            url += f"?cluster={self.cluster}"
        
        return url


# Convenience functions for direct use
async def get_network_info(cluster: str = "mainnet-beta") -> NetworkInfo:
    """Get network information"""
    async with SolanaClient(cluster) as client:
        return await client.get_network_info()

async def get_account_balance(address: Union[str, PublicKey], 
                            cluster: str = "mainnet-beta") -> float:
    """Get account balance in SOL"""
    async with SolanaClient(cluster) as client:
        return await client.get_balance(address)

async def get_transaction_status(signature: str, 
                               cluster: str = "mainnet-beta") -> Optional[TransactionInfo]:
    """Get transaction status"""
    async with SolanaClient(cluster) as client:
        return await client.get_transaction_info(signature)
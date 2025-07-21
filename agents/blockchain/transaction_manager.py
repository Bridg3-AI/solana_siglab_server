"""Transaction management and monitoring"""
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from enum import Enum
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.transaction import Transaction
from .solana_client import SolanaClient, TransactionInfo
from ..core.config import get_config

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    """Transaction status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class TransactionRequest:
    """Transaction request data"""
    transaction_id: str
    transaction: Transaction
    signers: List[Keypair]
    max_retries: int
    timeout: int
    priority: int
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'signers_count': len(self.signers)
        }

@dataclass
class TransactionResult:
    """Transaction result data"""
    transaction_id: str
    signature: Optional[str]
    status: TransactionStatus
    attempts: int
    error_message: Optional[str]
    gas_used: float
    execution_time: float
    confirmed_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'signature': self.signature,
            'status': self.status.value,
            'attempts': self.attempts,
            'error_message': self.error_message,
            'gas_used': self.gas_used,
            'execution_time': self.execution_time,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }

@dataclass
class TransactionBatch:
    """Transaction batch for bulk processing"""
    batch_id: str
    transactions: List[TransactionRequest]
    batch_type: str
    created_at: datetime
    completed_at: Optional[datetime]
    success_count: int
    failure_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'batch_id': self.batch_id,
            'batch_type': self.batch_type,
            'transaction_count': len(self.transactions),
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'success_count': self.success_count,
            'failure_count': self.failure_count
        }

class TransactionManager:
    """Advanced transaction management with queuing and monitoring"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        
        # Transaction queues
        self.pending_transactions: Dict[str, TransactionRequest] = {}
        self.completed_transactions: Dict[str, TransactionResult] = {}
        
        # Transaction batches
        self.transaction_batches: Dict[str, TransactionBatch] = {}
        
        # Queue management
        self.processing_queue: List[TransactionRequest] = []
        self.is_processing = False
        self.max_concurrent_transactions = 10
        
        # Monitoring
        self.transaction_callbacks: Dict[str, Callable] = {}
        self.global_callbacks: List[Callable] = []
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'average_execution_time': 0.0,
            'total_gas_used': 0.0
        }
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        import uuid
        return f"tx_{uuid.uuid4().hex[:16]}"
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        import uuid
        return f"batch_{uuid.uuid4().hex[:16]}"
    
    async def submit_transaction(self, transaction: Transaction,
                               signers: List[Keypair],
                               max_retries: int = 3,
                               timeout: int = 60,
                               priority: int = 5) -> str:
        """Submit transaction to the queue"""
        transaction_id = self._generate_transaction_id()
        
        tx_request = TransactionRequest(
            transaction_id=transaction_id,
            transaction=transaction,
            signers=signers,
            max_retries=max_retries,
            timeout=timeout,
            priority=priority,
            created_at=datetime.now()
        )
        
        # Add to pending queue
        self.pending_transactions[transaction_id] = tx_request
        
        # Add to processing queue (sorted by priority)
        self.processing_queue.append(tx_request)
        self.processing_queue.sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Transaction submitted: {transaction_id}")
        
        # Start processing if not already running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        return transaction_id
    
    async def _process_queue(self):
        """Process transaction queue"""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        try:
            while self.processing_queue:
                # Process transactions concurrently
                current_batch = self.processing_queue[:self.max_concurrent_transactions]
                self.processing_queue = self.processing_queue[self.max_concurrent_transactions:]
                
                # Process current batch
                tasks = [self._process_single_transaction(tx_request) for tx_request in current_batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
        finally:
            self.is_processing = False
    
    async def _process_single_transaction(self, tx_request: TransactionRequest):
        """Process a single transaction"""
        start_time = datetime.now()
        attempts = 0
        
        async with SolanaClient(self.cluster) as client:
            while attempts < tx_request.max_retries:
                try:
                    attempts += 1
                    
                    # Send transaction
                    signature = await client.send_transaction(
                        tx_request.transaction,
                        tx_request.signers
                    )
                    
                    # Wait for confirmation
                    confirmed = await client.wait_for_confirmation(
                        signature,
                        timeout=tx_request.timeout
                    )
                    
                    if confirmed:
                        # Get transaction info for gas calculation
                        tx_info = await client.get_transaction_info(signature)
                        gas_used = tx_info.fee if tx_info else 0.0
                        
                        # Create success result
                        result = TransactionResult(
                            transaction_id=tx_request.transaction_id,
                            signature=signature,
                            status=TransactionStatus.CONFIRMED,
                            attempts=attempts,
                            error_message=None,
                            gas_used=gas_used,
                            execution_time=(datetime.now() - start_time).total_seconds(),
                            confirmed_at=datetime.now()
                        )
                        
                        await self._complete_transaction(tx_request, result)
                        return
                    
                    else:
                        # Transaction timed out
                        if attempts >= tx_request.max_retries:
                            result = TransactionResult(
                                transaction_id=tx_request.transaction_id,
                                signature=signature,
                                status=TransactionStatus.TIMEOUT,
                                attempts=attempts,
                                error_message="Transaction confirmation timeout",
                                gas_used=0.0,
                                execution_time=(datetime.now() - start_time).total_seconds(),
                                confirmed_at=None
                            )
                            
                            await self._complete_transaction(tx_request, result)
                            return
                        
                        # Wait before retry
                        await asyncio.sleep(2 ** attempts)  # Exponential backoff
                        
                except Exception as e:
                    logger.error(f"Transaction attempt {attempts} failed: {e}")
                    
                    if attempts >= tx_request.max_retries:
                        result = TransactionResult(
                            transaction_id=tx_request.transaction_id,
                            signature=None,
                            status=TransactionStatus.FAILED,
                            attempts=attempts,
                            error_message=str(e),
                            gas_used=0.0,
                            execution_time=(datetime.now() - start_time).total_seconds(),
                            confirmed_at=None
                        )
                        
                        await self._complete_transaction(tx_request, result)
                        return
                    
                    # Wait before retry
                    await asyncio.sleep(2 ** attempts)
    
    async def _complete_transaction(self, tx_request: TransactionRequest, result: TransactionResult):
        """Complete transaction processing"""
        # Remove from pending
        self.pending_transactions.pop(tx_request.transaction_id, None)
        
        # Add to completed
        self.completed_transactions[tx_request.transaction_id] = result
        
        # Update statistics
        self.stats['total_processed'] += 1
        if result.status == TransactionStatus.CONFIRMED:
            self.stats['successful_transactions'] += 1
        else:
            self.stats['failed_transactions'] += 1
        
        self.stats['total_gas_used'] += result.gas_used
        
        # Update average execution time
        total_time = (self.stats['average_execution_time'] * (self.stats['total_processed'] - 1) + 
                     result.execution_time)
        self.stats['average_execution_time'] = total_time / self.stats['total_processed']
        
        # Call callbacks
        await self._call_callbacks(tx_request, result)
        
        logger.info(f"Transaction completed: {tx_request.transaction_id} - {result.status.value}")
    
    async def _call_callbacks(self, tx_request: TransactionRequest, result: TransactionResult):
        """Call registered callbacks"""
        # Call specific callback
        if tx_request.transaction_id in self.transaction_callbacks:
            callback = self.transaction_callbacks[tx_request.transaction_id]
            try:
                await callback(tx_request, result)
            except Exception as e:
                logger.error(f"Callback error: {e}")
        
        # Call global callbacks
        for callback in self.global_callbacks:
            try:
                await callback(tx_request, result)
            except Exception as e:
                logger.error(f"Global callback error: {e}")
    
    def register_callback(self, transaction_id: str, callback: Callable):
        """Register callback for specific transaction"""
        self.transaction_callbacks[transaction_id] = callback
    
    def register_global_callback(self, callback: Callable):
        """Register global callback for all transactions"""
        self.global_callbacks.append(callback)
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction status"""
        # Check pending
        if transaction_id in self.pending_transactions:
            tx_request = self.pending_transactions[transaction_id]
            return {
                'transaction_id': transaction_id,
                'status': TransactionStatus.PENDING.value,
                'submitted_at': tx_request.created_at.isoformat(),
                'queue_position': self._get_queue_position(transaction_id)
            }
        
        # Check completed
        if transaction_id in self.completed_transactions:
            result = self.completed_transactions[transaction_id]
            return result.to_dict()
        
        return None
    
    def _get_queue_position(self, transaction_id: str) -> int:
        """Get position in processing queue"""
        for i, tx_request in enumerate(self.processing_queue):
            if tx_request.transaction_id == transaction_id:
                return i + 1
        return -1
    
    async def cancel_transaction(self, transaction_id: str) -> bool:
        """Cancel pending transaction"""
        if transaction_id in self.pending_transactions:
            tx_request = self.pending_transactions.pop(transaction_id)
            
            # Remove from processing queue
            self.processing_queue = [
                tx for tx in self.processing_queue 
                if tx.transaction_id != transaction_id
            ]
            
            # Create cancelled result
            result = TransactionResult(
                transaction_id=transaction_id,
                signature=None,
                status=TransactionStatus.CANCELLED,
                attempts=0,
                error_message="Transaction cancelled by user",
                gas_used=0.0,
                execution_time=0.0,
                confirmed_at=None
            )
            
            self.completed_transactions[transaction_id] = result
            
            logger.info(f"Transaction cancelled: {transaction_id}")
            return True
        
        return False
    
    async def create_transaction_batch(self, transactions: List[Transaction],
                                     signers_list: List[List[Keypair]],
                                     batch_type: str = "bulk_transfer") -> str:
        """Create transaction batch for bulk processing"""
        batch_id = self._generate_batch_id()
        
        # Create transaction requests
        tx_requests = []
        for i, (transaction, signers) in enumerate(zip(transactions, signers_list)):
            tx_request = TransactionRequest(
                transaction_id=f"{batch_id}_{i}",
                transaction=transaction,
                signers=signers,
                max_retries=3,
                timeout=60,
                priority=5,
                created_at=datetime.now()
            )
            tx_requests.append(tx_request)
        
        # Create batch
        batch = TransactionBatch(
            batch_id=batch_id,
            transactions=tx_requests,
            batch_type=batch_type,
            created_at=datetime.now(),
            completed_at=None,
            success_count=0,
            failure_count=0
        )
        
        self.transaction_batches[batch_id] = batch
        
        # Submit all transactions
        for tx_request in tx_requests:
            self.pending_transactions[tx_request.transaction_id] = tx_request
            self.processing_queue.append(tx_request)
        
        # Sort queue by priority
        self.processing_queue.sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Transaction batch created: {batch_id} ({len(tx_requests)} transactions)")
        
        # Start processing
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        return batch_id
    
    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch status"""
        if batch_id not in self.transaction_batches:
            return None
        
        batch = self.transaction_batches[batch_id]
        
        # Count completed transactions
        completed = 0
        success_count = 0
        failure_count = 0
        
        for tx_request in batch.transactions:
            if tx_request.transaction_id in self.completed_transactions:
                completed += 1
                result = self.completed_transactions[tx_request.transaction_id]
                if result.status == TransactionStatus.CONFIRMED:
                    success_count += 1
                else:
                    failure_count += 1
        
        # Update batch
        batch.success_count = success_count
        batch.failure_count = failure_count
        
        if completed == len(batch.transactions):
            batch.completed_at = datetime.now()
        
        return {
            'batch_id': batch_id,
            'batch_type': batch.batch_type,
            'total_transactions': len(batch.transactions),
            'completed_transactions': completed,
            'success_count': success_count,
            'failure_count': failure_count,
            'created_at': batch.created_at.isoformat(),
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
            'completion_percentage': (completed / len(batch.transactions)) * 100
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get transaction statistics"""
        current_time = datetime.now()
        
        # Calculate success rate
        success_rate = (self.stats['successful_transactions'] / self.stats['total_processed'] 
                       if self.stats['total_processed'] > 0 else 0)
        
        return {
            'total_processed': self.stats['total_processed'],
            'successful_transactions': self.stats['successful_transactions'],
            'failed_transactions': self.stats['failed_transactions'],
            'success_rate': success_rate,
            'average_execution_time': self.stats['average_execution_time'],
            'total_gas_used': self.stats['total_gas_used'],
            'pending_transactions': len(self.pending_transactions),
            'queue_length': len(self.processing_queue),
            'is_processing': self.is_processing,
            'timestamp': current_time.isoformat()
        }
    
    async def get_recent_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        recent = sorted(
            self.completed_transactions.values(),
            key=lambda x: x.confirmed_at or datetime.min,
            reverse=True
        )[:limit]
        
        return [tx.to_dict() for tx in recent]
    
    async def cleanup_old_transactions(self, max_age_hours: int = 24):
        """Clean up old completed transactions"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean completed transactions
        old_transactions = [
            tx_id for tx_id, result in self.completed_transactions.items()
            if result.confirmed_at and result.confirmed_at < cutoff_time
        ]
        
        for tx_id in old_transactions:
            del self.completed_transactions[tx_id]
        
        # Clean old batches
        old_batches = [
            batch_id for batch_id, batch in self.transaction_batches.items()
            if batch.completed_at and batch.completed_at < cutoff_time
        ]
        
        for batch_id in old_batches:
            del self.transaction_batches[batch_id]
        
        logger.info(f"Cleaned up {len(old_transactions)} old transactions and {len(old_batches)} old batches")
    
    async def monitor_pending_transactions(self):
        """Monitor and alert on stuck transactions"""
        current_time = datetime.now()
        stuck_transactions = []
        
        for tx_id, tx_request in self.pending_transactions.items():
            age = (current_time - tx_request.created_at).total_seconds()
            
            # Consider transaction stuck if pending for more than 5 minutes
            if age > 300:
                stuck_transactions.append({
                    'transaction_id': tx_id,
                    'age_seconds': age,
                    'priority': tx_request.priority
                })
        
        if stuck_transactions:
            logger.warning(f"Found {len(stuck_transactions)} stuck transactions")
            
            # Could implement alerting here
            for stuck_tx in stuck_transactions:
                logger.warning(f"Stuck transaction: {stuck_tx['transaction_id']} "
                             f"(age: {stuck_tx['age_seconds']:.1f}s)")
        
        return stuck_transactions


# Convenience functions for direct use
async def send_transaction(transaction: Transaction,
                         signers: List[Keypair],
                         cluster: str = "mainnet-beta",
                         max_retries: int = 3) -> str:
    """Send transaction with retry logic"""
    tx_manager = TransactionManager(cluster)
    return await tx_manager.submit_transaction(transaction, signers, max_retries)

async def get_transaction_result(transaction_id: str,
                               cluster: str = "mainnet-beta") -> Optional[Dict[str, Any]]:
    """Get transaction result"""
    tx_manager = TransactionManager(cluster)
    return await tx_manager.get_transaction_status(transaction_id)

async def send_bulk_transactions(transactions: List[Transaction],
                               signers_list: List[List[Keypair]],
                               cluster: str = "mainnet-beta") -> str:
    """Send bulk transactions"""
    tx_manager = TransactionManager(cluster)
    return await tx_manager.create_transaction_batch(transactions, signers_list)
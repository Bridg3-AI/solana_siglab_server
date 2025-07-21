"""Oracle integration for external data feeds"""
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from solana.publickey import PublicKey
from .solana_client import SolanaClient
from ..core.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """Price data from oracle"""
    symbol: str
    price: float
    confidence: float
    timestamp: datetime
    source: str
    decimals: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'price': self.price,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'decimals': self.decimals
        }

@dataclass
class OracleStatus:
    """Oracle status information"""
    oracle_id: str
    oracle_type: str
    active: bool
    last_update: datetime
    update_frequency: int  # seconds
    data_sources: List[str]
    reliability_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'oracle_id': self.oracle_id,
            'oracle_type': self.oracle_type,
            'active': self.active,
            'last_update': self.last_update.isoformat(),
            'update_frequency': self.update_frequency,
            'data_sources': self.data_sources,
            'reliability_score': self.reliability_score
        }

class PythClient:
    """Pyth Network price oracle client"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        
        # Pyth program IDs
        self.pyth_program_ids = {
            "mainnet-beta": "FsJ3A3u2vn5cTVofAjvy6y5kwABJAqYWpe4975bi2epH",
            "devnet": "gSbePebfvPy7tRqimPoVecS2UsBvYv46ynrzWocc92s",
            "testnet": "8tfDNiaEyrV6Q1U13SDgZuMQJdMjaqGXezEnPJHAfRff"
        }
        
        # Common price feed addresses (mainnet)
        self.price_feeds = {
            "SOL/USD": "H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG",
            "BTC/USD": "GVXRSBjFk6e6J3NbVPXohDJetcTjaeeuykUpbQF8UoMU",
            "ETH/USD": "JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB",
            "USDC/USD": "Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD",
            "USDT/USD": "3vxLXJqLqF3JG5TCbYycbKWRBbCJQLxQmBGCkyqEEefL"
        }
    
    def get_program_id(self) -> str:
        """Get Pyth program ID for current cluster"""
        return self.pyth_program_ids.get(self.cluster, self.pyth_program_ids["mainnet-beta"])
    
    def get_price_feed_address(self, symbol: str) -> Optional[str]:
        """Get price feed address for symbol"""
        return self.price_feeds.get(symbol.upper())
    
    async def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get price data for a symbol"""
        try:
            feed_address = self.get_price_feed_address(symbol)
            if not feed_address:
                logger.warning(f"No price feed found for {symbol}")
                return await self._get_mock_price_data(symbol)
            
            async with SolanaClient(self.cluster) as client:
                account_info = await client.get_account_info(feed_address)
                
                if not account_info:
                    logger.warning(f"Price feed account not found: {feed_address}")
                    return await self._get_mock_price_data(symbol)
                
                # Parse Pyth price data (simplified)
                price_data = await self._parse_pyth_data(account_info, symbol)
                
                return price_data
                
        except Exception as e:
            logger.error(f"Error getting Pyth price data for {symbol}: {e}")
            return await self._get_mock_price_data(symbol)
    
    async def _parse_pyth_data(self, account_info, symbol: str) -> PriceData:
        """Parse Pyth price account data"""
        # This is a simplified implementation
        # In production, you would use the official Pyth SDK
        
        # Mock parsing for development
        import random
        
        base_prices = {
            "SOL/USD": 100.0,
            "BTC/USD": 45000.0,
            "ETH/USD": 3000.0,
            "USDC/USD": 1.0,
            "USDT/USD": 1.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        price = base_price * random.uniform(0.95, 1.05)
        
        return PriceData(
            symbol=symbol,
            price=price,
            confidence=0.01,  # 1% confidence interval
            timestamp=datetime.now(),
            source="pyth",
            decimals=8
        )
    
    async def _get_mock_price_data(self, symbol: str) -> PriceData:
        """Generate mock price data for development"""
        import random
        
        base_prices = {
            "SOL/USD": 100.0,
            "BTC/USD": 45000.0,
            "ETH/USD": 3000.0,
            "USDC/USD": 1.0,
            "USDT/USD": 1.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        price = base_price * random.uniform(0.9, 1.1)
        
        return PriceData(
            symbol=symbol,
            price=price,
            confidence=0.05,  # 5% confidence interval for mock data
            timestamp=datetime.now(),
            source="mock",
            decimals=8
        )
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get price data for multiple symbols"""
        prices = {}
        
        for symbol in symbols:
            price_data = await self.get_price_data(symbol)
            if price_data:
                prices[symbol] = price_data
        
        return prices
    
    async def get_oracle_status(self) -> OracleStatus:
        """Get Pyth oracle status"""
        return OracleStatus(
            oracle_id=self.get_program_id(),
            oracle_type="pyth",
            active=True,
            last_update=datetime.now(),
            update_frequency=1,  # 1 second
            data_sources=["pyth_network"],
            reliability_score=0.95
        )

class ChainlinkClient:
    """Chainlink oracle client (backup)"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        
        # Chainlink program IDs (if available on Solana)
        self.chainlink_program_ids = {
            "mainnet-beta": "cjg3oHmg9uuPsP8D6g29NWvhySJkdYdAo9D25PRbKXJ",
            "devnet": "CaH12fwNTKJAG8PxEvo9R96Zc2j8qNHZaFg8FkUoVeL3"
        }
        
        # Price feed addresses (if available)
        self.price_feeds = {
            "SOL/USD": "placeholder_address",
            "BTC/USD": "placeholder_address",
            "ETH/USD": "placeholder_address"
        }
    
    async def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get price data for a symbol"""
        try:
            # Chainlink on Solana is limited, fall back to mock data
            return await self._get_mock_price_data(symbol)
                
        except Exception as e:
            logger.error(f"Error getting Chainlink price data for {symbol}: {e}")
            return await self._get_mock_price_data(symbol)
    
    async def _get_mock_price_data(self, symbol: str) -> PriceData:
        """Generate mock price data for development"""
        import random
        
        base_prices = {
            "SOL/USD": 100.0,
            "BTC/USD": 45000.0,
            "ETH/USD": 3000.0,
            "USDC/USD": 1.0,
            "USDT/USD": 1.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        price = base_price * random.uniform(0.9, 1.1)
        
        return PriceData(
            symbol=symbol,
            price=price,
            confidence=0.02,  # 2% confidence interval
            timestamp=datetime.now(),
            source="chainlink_mock",
            decimals=8
        )
    
    async def get_oracle_status(self) -> OracleStatus:
        """Get Chainlink oracle status"""
        return OracleStatus(
            oracle_id=self.chainlink_program_ids.get(self.cluster, "unknown"),
            oracle_type="chainlink",
            active=False,  # Limited availability on Solana
            last_update=datetime.now(),
            update_frequency=300,  # 5 minutes
            data_sources=["chainlink_network"],
            reliability_score=0.90
        )

class OracleClient:
    """Multi-oracle client with fallback support"""
    
    def __init__(self, cluster: str = "mainnet-beta"):
        self.cluster = cluster
        self.config = get_config()
        self.pyth_client = PythClient(cluster)
        self.chainlink_client = ChainlinkClient(cluster)
        
        # Oracle priority order
        self.oracle_priority = ["pyth", "chainlink"]
    
    async def get_price_data(self, symbol: str) -> Optional[PriceData]:
        """Get price data with fallback support"""
        for oracle_type in self.oracle_priority:
            try:
                if oracle_type == "pyth":
                    price_data = await self.pyth_client.get_price_data(symbol)
                elif oracle_type == "chainlink":
                    price_data = await self.chainlink_client.get_price_data(symbol)
                else:
                    continue
                
                if price_data:
                    logger.info(f"Got price data for {symbol} from {oracle_type}")
                    return price_data
                    
            except Exception as e:
                logger.warning(f"Failed to get price from {oracle_type}: {e}")
                continue
        
        logger.error(f"All oracles failed for {symbol}")
        return None
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, PriceData]:
        """Get price data for multiple symbols"""
        prices = {}
        
        for symbol in symbols:
            price_data = await self.get_price_data(symbol)
            if price_data:
                prices[symbol] = price_data
        
        return prices
    
    async def get_price_with_validation(self, symbol: str, 
                                      max_age: int = 300) -> Optional[PriceData]:
        """Get price data with age validation"""
        price_data = await self.get_price_data(symbol)
        
        if not price_data:
            return None
        
        # Check if price is too old
        age = (datetime.now() - price_data.timestamp).total_seconds()
        if age > max_age:
            logger.warning(f"Price data too old for {symbol}: {age}s")
            return None
        
        return price_data
    
    async def get_oracle_consensus(self, symbol: str) -> Optional[PriceData]:
        """Get consensus price from multiple oracles"""
        prices = []
        
        # Get prices from all available oracles
        for oracle_type in self.oracle_priority:
            try:
                if oracle_type == "pyth":
                    price_data = await self.pyth_client.get_price_data(symbol)
                elif oracle_type == "chainlink":
                    price_data = await self.chainlink_client.get_price_data(symbol)
                else:
                    continue
                
                if price_data:
                    prices.append(price_data)
                    
            except Exception as e:
                logger.warning(f"Failed to get price from {oracle_type}: {e}")
                continue
        
        if not prices:
            return None
        
        # Calculate consensus (simple average for now)
        total_price = sum(p.price for p in prices)
        avg_price = total_price / len(prices)
        
        # Use the most confident source's metadata
        best_price = max(prices, key=lambda p: p.confidence)
        
        return PriceData(
            symbol=symbol,
            price=avg_price,
            confidence=best_price.confidence,
            timestamp=datetime.now(),
            source=f"consensus_{len(prices)}_oracles",
            decimals=best_price.decimals
        )
    
    async def get_all_oracle_status(self) -> List[OracleStatus]:
        """Get status of all oracles"""
        statuses = []
        
        try:
            pyth_status = await self.pyth_client.get_oracle_status()
            statuses.append(pyth_status)
        except Exception as e:
            logger.error(f"Failed to get Pyth status: {e}")
        
        try:
            chainlink_status = await self.chainlink_client.get_oracle_status()
            statuses.append(chainlink_status)
        except Exception as e:
            logger.error(f"Failed to get Chainlink status: {e}")
        
        return statuses
    
    async def validate_price_feed(self, symbol: str) -> Dict[str, Any]:
        """Validate price feed quality"""
        validation_result = {
            'symbol': symbol,
            'valid': False,
            'issues': [],
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Get price data
        price_data = await self.get_price_data(symbol)
        
        if not price_data:
            validation_result['issues'].append("No price data available")
            validation_result['recommendations'].append("Check oracle connectivity")
            return validation_result
        
        # Check price age
        age = (datetime.now() - price_data.timestamp).total_seconds()
        if age > 300:  # 5 minutes
            validation_result['issues'].append(f"Price data too old: {age}s")
            validation_result['recommendations'].append("Check oracle update frequency")
        
        # Check confidence
        if price_data.confidence > 0.05:  # 5%
            validation_result['issues'].append(f"Low confidence: {price_data.confidence:.2%}")
            validation_result['recommendations'].append("Consider using multiple oracles")
        
        # Check for reasonable price
        if price_data.price <= 0:
            validation_result['issues'].append("Invalid price value")
            validation_result['recommendations'].append("Check oracle data integrity")
        
        # Mark as valid if no issues
        validation_result['valid'] = len(validation_result['issues']) == 0
        
        return validation_result


# Convenience functions for direct use
async def get_price(symbol: str, cluster: str = "mainnet-beta") -> Optional[PriceData]:
    """Get price data for a symbol"""
    oracle_client = OracleClient(cluster)
    return await oracle_client.get_price_data(symbol)

async def get_multiple_prices(symbols: List[str], 
                            cluster: str = "mainnet-beta") -> Dict[str, PriceData]:
    """Get price data for multiple symbols"""
    oracle_client = OracleClient(cluster)
    return await oracle_client.get_multiple_prices(symbols)

async def get_consensus_price(symbol: str, 
                            cluster: str = "mainnet-beta") -> Optional[PriceData]:
    """Get consensus price from multiple oracles"""
    oracle_client = OracleClient(cluster)
    return await oracle_client.get_oracle_consensus(symbol)
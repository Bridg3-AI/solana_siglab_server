"""Cryptocurrency and financial data API integration module"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import aiohttp
import json
from ..core.config import get_config

logger = logging.getLogger(__name__)

@dataclass
class CryptoData:
    """Cryptocurrency market data structure"""
    symbol: str
    name: str
    current_price: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap: float
    volume_24h: float
    circulating_supply: float
    total_supply: Optional[float]
    timestamp: datetime
    source: str
    confidence: float = 0.95
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class ExchangeRateData:
    """Exchange rate data structure"""
    base_currency: str
    target_currency: str
    exchange_rate: float
    change_24h: float
    change_percentage_24h: float
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class MarketIndicators:
    """Market indicators and economic data"""
    fear_greed_index: float
    volatility_index: float
    inflation_rate: float
    interest_rate: float
    market_sentiment: str
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class CryptoAPI:
    """Cryptocurrency and financial data API integration class"""
    
    def __init__(self):
        self.config = get_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache"""
        if not self.config.enable_cache:
            return None
            
        if key in self.cache:
            cached_data = self.cache[key]
            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cache_time < timedelta(seconds=self.config.cache_ttl):
                return cached_data['data']
            else:
                del self.cache[key]
        return None
    
    async def _set_cached_data(self, key: str, data: Dict[str, Any]):
        """Set data in cache"""
        if self.config.enable_cache:
            self.cache[key] = {
                'data': data,
                'cached_at': datetime.now().isoformat()
            }
    
    async def get_crypto_price(self, symbol: str) -> Optional[CryptoData]:
        """Get cryptocurrency price and market data"""
        cache_key = f"crypto_{symbol.lower()}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return CryptoData(**cached_data)
        
        # Try CoinGecko API first
        crypto_data = await self._get_coingecko_data(symbol)
        
        if crypto_data:
            await self._set_cached_data(cache_key, crypto_data.to_dict())
            return crypto_data
        
        # Fallback to mock data for development
        return await self._get_mock_crypto_data(symbol)
    
    async def _get_coingecko_data(self, symbol: str) -> Optional[CryptoData]:
        """Get crypto data from CoinGecko API"""
        try:
            # Map common symbols to CoinGecko IDs
            symbol_mapping = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'SOL': 'solana',
                'USDC': 'usd-coin',
                'USDT': 'tether'
            }
            
            coin_id = symbol_mapping.get(symbol.upper(), symbol.lower())
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
            
            # Add API key if available
            if self.config.coingecko_api_key:
                params['x_cg_demo_api_key'] = self.config.coingecko_api_key
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_coingecko_data(data)
                elif response.status == 429:
                    logger.warning("CoinGecko API rate limit exceeded")
                    return None
                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data: {e}")
            return None
    
    def _parse_coingecko_data(self, data: Dict[str, Any]) -> CryptoData:
        """Parse CoinGecko API response"""
        market_data = data['market_data']
        
        return CryptoData(
            symbol=data['symbol'].upper(),
            name=data['name'],
            current_price=market_data['current_price'].get('usd', 0),
            price_change_24h=market_data['price_change_24h'] or 0,
            price_change_percentage_24h=market_data['price_change_percentage_24h'] or 0,
            market_cap=market_data['market_cap'].get('usd', 0),
            volume_24h=market_data['total_volume'].get('usd', 0),
            circulating_supply=market_data['circulating_supply'] or 0,
            total_supply=market_data['total_supply'],
            timestamp=datetime.now(),
            source='coingecko',
            confidence=0.95
        )
    
    async def _get_mock_crypto_data(self, symbol: str) -> CryptoData:
        """Generate mock cryptocurrency data for development"""
        import random
        
        # Mock price data based on symbol
        price_data = {
            'BTC': {'price': 45000, 'name': 'Bitcoin'},
            'ETH': {'price': 3000, 'name': 'Ethereum'},
            'SOL': {'price': 100, 'name': 'Solana'},
            'USDC': {'price': 1.0, 'name': 'USD Coin'},
            'USDT': {'price': 1.0, 'name': 'Tether'}
        }
        
        base_data = price_data.get(symbol.upper(), {'price': 100, 'name': f'{symbol} Token'})
        base_price = base_data['price']
        
        # Add some realistic volatility
        current_price = base_price * random.uniform(0.9, 1.1)
        price_change_24h = random.uniform(-base_price * 0.1, base_price * 0.1)
        price_change_percentage_24h = (price_change_24h / current_price) * 100
        
        return CryptoData(
            symbol=symbol.upper(),
            name=base_data['name'],
            current_price=current_price,
            price_change_24h=price_change_24h,
            price_change_percentage_24h=price_change_percentage_24h,
            market_cap=current_price * random.uniform(10000000, 1000000000),
            volume_24h=current_price * random.uniform(1000000, 100000000),
            circulating_supply=random.uniform(1000000, 1000000000),
            total_supply=random.uniform(1000000, 10000000000),
            timestamp=datetime.now(),
            source='mock',
            confidence=0.8
        )
    
    async def get_solana_ecosystem_data(self) -> Dict[str, Any]:
        """Get Solana ecosystem data including SOL and SPL tokens"""
        cache_key = "solana_ecosystem"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        # Get SOL data
        sol_data = await self.get_crypto_price('SOL')
        
        # Get major SPL tokens
        spl_tokens = ['USDC', 'USDT', 'RAY', 'SRM', 'COPE']
        token_data = {}
        
        for token in spl_tokens:
            token_info = await self.get_crypto_price(token)
            if token_info:
                token_data[token] = token_info.to_dict()
        
        ecosystem_data = {
            'sol': sol_data.to_dict() if sol_data else None,
            'spl_tokens': token_data,
            'network_stats': await self._get_mock_network_stats(),
            'timestamp': datetime.now().isoformat()
        }
        
        await self._set_cached_data(cache_key, ecosystem_data)
        return ecosystem_data
    
    async def _get_mock_network_stats(self) -> Dict[str, Any]:
        """Generate mock Solana network statistics"""
        import random
        
        return {
            'tps': random.uniform(2000, 5000),
            'block_time': random.uniform(0.4, 0.6),
            'validator_count': random.randint(1500, 2000),
            'stake_accounts': random.randint(300000, 500000),
            'total_staked': random.uniform(300000000, 400000000),
            'staking_yield': random.uniform(0.06, 0.08),
            'network_fees': random.uniform(0.00025, 0.001)
        }
    
    async def get_exchange_rate(self, base_currency: str, target_currency: str) -> Optional[ExchangeRateData]:
        """Get exchange rate between two currencies"""
        cache_key = f"exchange_{base_currency}_{target_currency}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return ExchangeRateData(**cached_data)
        
        # Mock exchange rate data for development
        exchange_data = await self._get_mock_exchange_rate(base_currency, target_currency)
        
        if exchange_data:
            await self._set_cached_data(cache_key, exchange_data.to_dict())
        
        return exchange_data
    
    async def _get_mock_exchange_rate(self, base_currency: str, target_currency: str) -> ExchangeRateData:
        """Generate mock exchange rate data"""
        import random
        
        # Mock exchange rates (base rates against USD)
        base_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'JPY': 110.0,
            'GBP': 0.75,
            'KRW': 1200.0,
            'CNY': 6.5
        }
        
        base_rate = base_rates.get(base_currency.upper(), 1.0)
        target_rate = base_rates.get(target_currency.upper(), 1.0)
        
        exchange_rate = target_rate / base_rate
        change_24h = random.uniform(-exchange_rate * 0.02, exchange_rate * 0.02)
        change_percentage_24h = (change_24h / exchange_rate) * 100
        
        return ExchangeRateData(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            exchange_rate=exchange_rate,
            change_24h=change_24h,
            change_percentage_24h=change_percentage_24h,
            timestamp=datetime.now(),
            source='mock'
        )
    
    async def get_market_indicators(self) -> MarketIndicators:
        """Get market indicators and economic data"""
        cache_key = "market_indicators"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return MarketIndicators(**cached_data)
        
        # Mock market indicators for development
        indicators = await self._get_mock_market_indicators()
        
        if indicators:
            await self._set_cached_data(cache_key, indicators.to_dict())
        
        return indicators
    
    async def _get_mock_market_indicators(self) -> MarketIndicators:
        """Generate mock market indicators"""
        import random
        
        fear_greed = random.uniform(0, 100)
        sentiment_map = {
            (0, 25): 'extreme_fear',
            (25, 45): 'fear',
            (45, 55): 'neutral',
            (55, 75): 'greed',
            (75, 100): 'extreme_greed'
        }
        
        sentiment = 'neutral'
        for (low, high), sent in sentiment_map.items():
            if low <= fear_greed < high:
                sentiment = sent
                break
        
        return MarketIndicators(
            fear_greed_index=fear_greed,
            volatility_index=random.uniform(10, 40),
            inflation_rate=random.uniform(0.02, 0.08),
            interest_rate=random.uniform(0.01, 0.05),
            market_sentiment=sentiment,
            timestamp=datetime.now(),
            source='mock'
        )
    
    async def calculate_portfolio_volatility(self, portfolio: Dict[str, float]) -> Dict[str, Any]:
        """Calculate portfolio volatility for risk assessment"""
        cache_key = f"portfolio_volatility_{hash(str(portfolio))}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        # Get price data for all assets
        asset_data = {}
        for symbol, weight in portfolio.items():
            crypto_data = await self.get_crypto_price(symbol)
            if crypto_data:
                asset_data[symbol] = {
                    'weight': weight,
                    'price': crypto_data.current_price,
                    'volatility': abs(crypto_data.price_change_percentage_24h) / 100
                }
        
        # Calculate portfolio volatility
        portfolio_volatility = sum(
            data['weight'] * data['volatility'] 
            for data in asset_data.values()
        )
        
        # Calculate correlation-adjusted volatility (simplified)
        correlation_factor = 0.7  # Assume moderate correlation
        adjusted_volatility = portfolio_volatility * correlation_factor
        
        volatility_data = {
            'portfolio': portfolio,
            'individual_assets': asset_data,
            'portfolio_volatility': portfolio_volatility,
            'adjusted_volatility': adjusted_volatility,
            'risk_level': self._classify_risk_level(adjusted_volatility),
            'timestamp': datetime.now().isoformat()
        }
        
        await self._set_cached_data(cache_key, volatility_data)
        return volatility_data
    
    def _classify_risk_level(self, volatility: float) -> str:
        """Classify risk level based on volatility"""
        if volatility < 0.1:
            return 'low'
        elif volatility < 0.2:
            return 'moderate'
        elif volatility < 0.4:
            return 'high'
        else:
            return 'very_high'
    
    async def analyze_crypto_risk(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze cryptocurrency risk for insurance purposes"""
        risk_analysis = {
            'symbols': symbols,
            'individual_risks': {},
            'portfolio_risk': {},
            'market_context': {},
            'recommendations': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Analyze individual crypto risks
        for symbol in symbols:
            crypto_data = await self.get_crypto_price(symbol)
            if crypto_data:
                risk_analysis['individual_risks'][symbol] = {
                    'current_price': crypto_data.current_price,
                    'volatility': abs(crypto_data.price_change_percentage_24h) / 100,
                    'market_cap': crypto_data.market_cap,
                    'liquidity': crypto_data.volume_24h,
                    'risk_score': self._calculate_crypto_risk_score(crypto_data)
                }
        
        # Portfolio-level analysis
        if len(symbols) > 1:
            equal_weights = {symbol: 1.0/len(symbols) for symbol in symbols}
            portfolio_volatility = await self.calculate_portfolio_volatility(equal_weights)
            risk_analysis['portfolio_risk'] = portfolio_volatility
        
        # Market context
        market_indicators = await self.get_market_indicators()
        risk_analysis['market_context'] = market_indicators.to_dict()
        
        # Generate recommendations
        risk_analysis['recommendations'] = self._generate_crypto_recommendations(risk_analysis)
        
        return risk_analysis
    
    def _calculate_crypto_risk_score(self, crypto_data: CryptoData) -> float:
        """Calculate risk score for a cryptocurrency"""
        base_risk = 0.3  # Base 30% risk for crypto
        
        # Volatility factor
        volatility = abs(crypto_data.price_change_percentage_24h) / 100
        base_risk += volatility * 0.5
        
        # Market cap factor (lower market cap = higher risk)
        if crypto_data.market_cap < 1000000000:  # < $1B
            base_risk += 0.2
        elif crypto_data.market_cap < 10000000000:  # < $10B
            base_risk += 0.1
        
        # Liquidity factor (lower volume = higher risk)
        if crypto_data.volume_24h < crypto_data.market_cap * 0.01:  # < 1% of market cap
            base_risk += 0.15
        
        return min(base_risk, 1.0)
    
    def _generate_crypto_recommendations(self, risk_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on crypto risk analysis"""
        recommendations = []
        
        # Portfolio-level recommendations
        if 'portfolio_risk' in risk_analysis:
            portfolio_risk = risk_analysis['portfolio_risk']
            risk_level = portfolio_risk.get('risk_level', 'moderate')
            
            if risk_level == 'low':
                recommendations.append("Low portfolio risk - standard coverage recommended")
            elif risk_level == 'moderate':
                recommendations.append("Moderate portfolio risk - consider enhanced coverage")
            else:
                recommendations.append("High portfolio risk - maximum coverage recommended")
                recommendations.append("Consider diversification strategies")
        
        # Individual asset recommendations
        high_risk_assets = []
        for symbol, risk_data in risk_analysis['individual_risks'].items():
            if risk_data['risk_score'] > 0.7:
                high_risk_assets.append(symbol)
        
        if high_risk_assets:
            recommendations.append(f"High-risk assets detected: {', '.join(high_risk_assets)}")
            recommendations.append("Consider additional coverage for volatile assets")
        
        # Market context recommendations
        market_context = risk_analysis.get('market_context', {})
        if market_context.get('market_sentiment') in ['extreme_fear', 'extreme_greed']:
            recommendations.append("Market sentiment extreme - monitor closely")
        
        return recommendations


# Convenience functions for direct use
async def get_crypto_data(symbol: str) -> Optional[CryptoData]:
    """Get cryptocurrency market data"""
    async with CryptoAPI() as crypto_api:
        return await crypto_api.get_crypto_price(symbol)

async def get_solana_data() -> Dict[str, Any]:
    """Get Solana ecosystem data"""
    async with CryptoAPI() as crypto_api:
        return await crypto_api.get_solana_ecosystem_data()

async def get_currency_exchange(base: str, target: str) -> Optional[ExchangeRateData]:
    """Get exchange rate between currencies"""
    async with CryptoAPI() as crypto_api:
        return await crypto_api.get_exchange_rate(base, target)

async def get_crypto_risk_analysis(symbols: List[str]) -> Dict[str, Any]:
    """Get cryptocurrency risk analysis for insurance purposes"""
    async with CryptoAPI() as crypto_api:
        return await crypto_api.analyze_crypto_risk(symbols)
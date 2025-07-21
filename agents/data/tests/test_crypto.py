"""Tests for crypto API module"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from agents.data.crypto import CryptoAPI, CryptoData, ExchangeRateData, MarketIndicators
from agents.data.crypto import get_crypto_data, get_solana_data, get_currency_exchange, get_crypto_risk_analysis


class TestCryptoAPI:
    """Test cases for CryptoAPI class"""
    
    @pytest.fixture
    def crypto_api(self):
        """Create CryptoAPI instance for testing"""
        return CryptoAPI()
    
    @pytest.fixture
    def mock_coingecko_data(self):
        """Mock CoinGecko API data for testing"""
        return {
            'id': 'bitcoin',
            'symbol': 'btc',
            'name': 'Bitcoin',
            'market_data': {
                'current_price': {'usd': 45000.0},
                'price_change_24h': 500.0,
                'price_change_percentage_24h': 1.12,
                'market_cap': {'usd': 850000000000.0},
                'total_volume': {'usd': 25000000000.0},
                'circulating_supply': 19000000.0,
                'total_supply': 21000000.0
            }
        }
    
    def test_crypto_data_creation(self):
        """Test CryptoData dataclass creation"""
        crypto_data = CryptoData(
            symbol='BTC',
            name='Bitcoin',
            current_price=45000.0,
            price_change_24h=500.0,
            price_change_percentage_24h=1.12,
            market_cap=850000000000.0,
            volume_24h=25000000000.0,
            circulating_supply=19000000.0,
            total_supply=21000000.0,
            timestamp=datetime.now(),
            source='test'
        )
        
        assert crypto_data.symbol == 'BTC'
        assert crypto_data.name == 'Bitcoin'
        assert crypto_data.current_price == 45000.0
        assert crypto_data.confidence == 0.95  # default value
        
        # Test dictionary conversion
        crypto_dict = crypto_data.to_dict()
        assert crypto_dict['symbol'] == 'BTC'
        assert 'timestamp' in crypto_dict
        assert isinstance(crypto_dict['timestamp'], str)
    
    def test_exchange_rate_data_creation(self):
        """Test ExchangeRateData dataclass creation"""
        exchange_data = ExchangeRateData(
            base_currency='USD',
            target_currency='EUR',
            exchange_rate=0.85,
            change_24h=-0.01,
            change_percentage_24h=-1.16,
            timestamp=datetime.now(),
            source='test'
        )
        
        assert exchange_data.base_currency == 'USD'
        assert exchange_data.target_currency == 'EUR'
        assert exchange_data.exchange_rate == 0.85
        
        # Test dictionary conversion
        exchange_dict = exchange_data.to_dict()
        assert exchange_dict['base_currency'] == 'USD'
        assert 'timestamp' in exchange_dict
    
    def test_market_indicators_creation(self):
        """Test MarketIndicators dataclass creation"""
        market_indicators = MarketIndicators(
            fear_greed_index=75.0,
            volatility_index=25.0,
            inflation_rate=0.03,
            interest_rate=0.025,
            market_sentiment='greed',
            timestamp=datetime.now(),
            source='test'
        )
        
        assert market_indicators.fear_greed_index == 75.0
        assert market_indicators.market_sentiment == 'greed'
        assert market_indicators.inflation_rate == 0.03
        
        # Test dictionary conversion
        indicators_dict = market_indicators.to_dict()
        assert indicators_dict['fear_greed_index'] == 75.0
        assert 'timestamp' in indicators_dict
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, crypto_api):
        """Test caching functionality"""
        # Mock configuration
        crypto_api.config.enable_cache = True
        crypto_api.config.cache_ttl = 300
        
        # Test setting and getting cache
        test_data = {'test': 'crypto_data'}
        await crypto_api._set_cached_data('test_crypto_key', test_data)
        
        cached_data = await crypto_api._get_cached_data('test_crypto_key')
        assert cached_data == test_data
        
        # Test cache expiration
        crypto_api.config.cache_ttl = 0
        await asyncio.sleep(0.1)
        
        expired_data = await crypto_api._get_cached_data('test_crypto_key')
        assert expired_data is None
    
    @pytest.mark.asyncio
    async def test_coingecko_api_integration(self, crypto_api, mock_coingecko_data):
        """Test CoinGecko API integration"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_coingecko_data)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call
            result = await crypto_api._get_coingecko_data('BTC')
            
            assert result is not None
            assert result.symbol == 'BTC'
            assert result.name == 'Bitcoin'
            assert result.current_price == 45000.0
            assert result.source == 'coingecko'
    
    @pytest.mark.asyncio
    async def test_coingecko_api_rate_limit(self, crypto_api):
        """Test CoinGecko API rate limit handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock rate limit response
            mock_response = Mock()
            mock_response.status = 429
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call with rate limit
            result = await crypto_api._get_coingecko_data('BTC')
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_coingecko_api_error_handling(self, crypto_api):
        """Test CoinGecko API error handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock API error response
            mock_response = Mock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call with error
            result = await crypto_api._get_coingecko_data('INVALID')
            
            assert result is None
    
    def test_parse_coingecko_data(self, crypto_api, mock_coingecko_data):
        """Test CoinGecko data parsing"""
        result = crypto_api._parse_coingecko_data(mock_coingecko_data)
        
        assert result.symbol == 'BTC'
        assert result.name == 'Bitcoin'
        assert result.current_price == 45000.0
        assert result.price_change_24h == 500.0
        assert result.price_change_percentage_24h == 1.12
        assert result.market_cap == 850000000000.0
        assert result.volume_24h == 25000000000.0
        assert result.circulating_supply == 19000000.0
        assert result.total_supply == 21000000.0
        assert result.source == 'coingecko'
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_mock_crypto_data_generation(self, crypto_api):
        """Test mock crypto data generation"""
        result = await crypto_api._get_mock_crypto_data('BTC')
        
        assert result is not None
        assert result.symbol == 'BTC'
        assert result.name == 'Bitcoin'
        assert result.source == 'mock'
        assert result.confidence == 0.8
        assert result.current_price > 0
        assert result.market_cap > 0
        assert result.volume_24h > 0
    
    @pytest.mark.asyncio
    async def test_get_crypto_price(self, crypto_api):
        """Test get_crypto_price method"""
        # Mock the API key to force fallback to mock data
        crypto_api.config.coingecko_api_key = None
        
        result = await crypto_api.get_crypto_price('BTC')
        
        assert result is not None
        assert result.symbol == 'BTC'
        assert result.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_solana_ecosystem_data(self, crypto_api):
        """Test Solana ecosystem data retrieval"""
        ecosystem_data = await crypto_api.get_solana_ecosystem_data()
        
        assert ecosystem_data is not None
        assert 'sol' in ecosystem_data
        assert 'spl_tokens' in ecosystem_data
        assert 'network_stats' in ecosystem_data
        assert 'timestamp' in ecosystem_data
        
        # Check SOL data
        if ecosystem_data['sol']:
            assert ecosystem_data['sol']['symbol'] == 'SOL'
        
        # Check SPL tokens
        spl_tokens = ecosystem_data['spl_tokens']
        expected_tokens = ['USDC', 'USDT', 'RAY', 'SRM', 'COPE']
        for token in expected_tokens:
            if token in spl_tokens:
                assert spl_tokens[token]['symbol'] == token
        
        # Check network stats
        network_stats = ecosystem_data['network_stats']
        assert 'tps' in network_stats
        assert 'block_time' in network_stats
        assert 'validator_count' in network_stats
        assert 'staking_yield' in network_stats
    
    @pytest.mark.asyncio
    async def test_get_exchange_rate(self, crypto_api):
        """Test exchange rate retrieval"""
        exchange_data = await crypto_api.get_exchange_rate('USD', 'EUR')
        
        assert exchange_data is not None
        assert isinstance(exchange_data, ExchangeRateData)
        assert exchange_data.base_currency == 'USD'
        assert exchange_data.target_currency == 'EUR'
        assert exchange_data.source == 'mock'
        assert exchange_data.exchange_rate > 0
    
    @pytest.mark.asyncio
    async def test_mock_exchange_rate_generation(self, crypto_api):
        """Test mock exchange rate generation"""
        result = await crypto_api._get_mock_exchange_rate('USD', 'EUR')
        
        assert result.base_currency == 'USD'
        assert result.target_currency == 'EUR'
        assert result.exchange_rate > 0
        assert result.source == 'mock'
        # EUR is typically less than USD
        assert result.exchange_rate < 1.0
    
    @pytest.mark.asyncio
    async def test_get_market_indicators(self, crypto_api):
        """Test market indicators retrieval"""
        indicators = await crypto_api.get_market_indicators()
        
        assert indicators is not None
        assert isinstance(indicators, MarketIndicators)
        assert 0 <= indicators.fear_greed_index <= 100
        assert indicators.volatility_index > 0
        assert indicators.inflation_rate > 0
        assert indicators.interest_rate > 0
        assert indicators.market_sentiment in ['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']
        assert indicators.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_mock_market_indicators_generation(self, crypto_api):
        """Test mock market indicators generation"""
        result = await crypto_api._get_mock_market_indicators()
        
        assert 0 <= result.fear_greed_index <= 100
        assert result.volatility_index > 0
        assert result.inflation_rate > 0
        assert result.interest_rate > 0
        assert result.market_sentiment in ['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']
        assert result.source == 'mock'
        
        # Test sentiment mapping
        if result.fear_greed_index < 25:
            assert result.market_sentiment == 'extreme_fear'
        elif result.fear_greed_index < 45:
            assert result.market_sentiment == 'fear'
        elif result.fear_greed_index < 55:
            assert result.market_sentiment == 'neutral'
        elif result.fear_greed_index < 75:
            assert result.market_sentiment == 'greed'
        else:
            assert result.market_sentiment == 'extreme_greed'
    
    @pytest.mark.asyncio
    async def test_portfolio_volatility_calculation(self, crypto_api):
        """Test portfolio volatility calculation"""
        portfolio = {
            'BTC': 0.5,
            'ETH': 0.3,
            'SOL': 0.2
        }
        
        volatility_data = await crypto_api.calculate_portfolio_volatility(portfolio)
        
        assert volatility_data is not None
        assert 'portfolio' in volatility_data
        assert 'individual_assets' in volatility_data
        assert 'portfolio_volatility' in volatility_data
        assert 'adjusted_volatility' in volatility_data
        assert 'risk_level' in volatility_data
        assert 'timestamp' in volatility_data
        
        assert volatility_data['portfolio'] == portfolio
        assert volatility_data['portfolio_volatility'] >= 0
        assert volatility_data['adjusted_volatility'] >= 0
        assert volatility_data['risk_level'] in ['low', 'moderate', 'high', 'very_high']
        
        # Check individual assets
        individual_assets = volatility_data['individual_assets']
        for symbol, weight in portfolio.items():
            assert symbol in individual_assets
            assert individual_assets[symbol]['weight'] == weight
            assert individual_assets[symbol]['price'] > 0
            assert individual_assets[symbol]['volatility'] >= 0
    
    def test_classify_risk_level(self, crypto_api):
        """Test risk level classification"""
        test_cases = [
            (0.05, 'low'),
            (0.15, 'moderate'),
            (0.25, 'high'),
            (0.5, 'very_high')
        ]
        
        for volatility, expected_level in test_cases:
            risk_level = crypto_api._classify_risk_level(volatility)
            assert risk_level == expected_level
    
    @pytest.mark.asyncio
    async def test_crypto_risk_analysis(self, crypto_api):
        """Test cryptocurrency risk analysis"""
        symbols = ['BTC', 'ETH', 'SOL']
        
        risk_analysis = await crypto_api.analyze_crypto_risk(symbols)
        
        assert risk_analysis is not None
        assert 'symbols' in risk_analysis
        assert 'individual_risks' in risk_analysis
        assert 'portfolio_risk' in risk_analysis
        assert 'market_context' in risk_analysis
        assert 'recommendations' in risk_analysis
        assert 'timestamp' in risk_analysis
        
        assert risk_analysis['symbols'] == symbols
        assert isinstance(risk_analysis['recommendations'], list)
        
        # Check individual risks
        individual_risks = risk_analysis['individual_risks']
        for symbol in symbols:
            assert symbol in individual_risks
            risk_data = individual_risks[symbol]
            assert 'current_price' in risk_data
            assert 'volatility' in risk_data
            assert 'market_cap' in risk_data
            assert 'liquidity' in risk_data
            assert 'risk_score' in risk_data
            assert 0 <= risk_data['risk_score'] <= 1
        
        # Check portfolio risk (should exist with multiple symbols)
        assert 'portfolio_risk' in risk_analysis
        
        # Check market context
        market_context = risk_analysis['market_context']
        assert 'fear_greed_index' in market_context
        assert 'market_sentiment' in market_context
    
    def test_calculate_crypto_risk_score(self, crypto_api):
        """Test crypto risk score calculation"""
        # High volatility, low market cap crypto
        high_risk_crypto = CryptoData(
            symbol='LOWCAP',
            name='Low Cap Token',
            current_price=1.0,
            price_change_24h=-0.5,
            price_change_percentage_24h=-50.0,  # High volatility
            market_cap=500000000.0,  # < $1B
            volume_24h=1000000.0,  # Low volume
            circulating_supply=500000000.0,
            total_supply=1000000000.0,
            timestamp=datetime.now(),
            source='test'
        )
        
        risk_score = crypto_api._calculate_crypto_risk_score(high_risk_crypto)
        
        assert 0 <= risk_score <= 1
        assert risk_score > 0.5  # Should be high risk
        
        # Low volatility, high market cap crypto
        low_risk_crypto = CryptoData(
            symbol='BTC',
            name='Bitcoin',
            current_price=45000.0,
            price_change_24h=50.0,
            price_change_percentage_24h=0.1,  # Low volatility
            market_cap=850000000000.0,  # > $10B
            volume_24h=25000000000.0,  # High volume
            circulating_supply=19000000.0,
            total_supply=21000000.0,
            timestamp=datetime.now(),
            source='test'
        )
        
        low_risk_score = crypto_api._calculate_crypto_risk_score(low_risk_crypto)
        
        assert 0 <= low_risk_score <= 1
        assert low_risk_score < risk_score  # Should be lower risk
    
    def test_generate_crypto_recommendations(self, crypto_api):
        """Test crypto recommendations generation"""
        # Low risk analysis
        low_risk_analysis = {
            'individual_risks': {
                'BTC': {'risk_score': 0.3},
                'ETH': {'risk_score': 0.4}
            },
            'portfolio_risk': {'risk_level': 'low'},
            'market_context': {'market_sentiment': 'neutral'}
        }
        
        recommendations = crypto_api._generate_crypto_recommendations(low_risk_analysis)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any('Low portfolio risk' in rec for rec in recommendations)
        
        # High risk analysis
        high_risk_analysis = {
            'individual_risks': {
                'VOLATILE': {'risk_score': 0.8},
                'RISKY': {'risk_score': 0.9}
            },
            'portfolio_risk': {'risk_level': 'very_high'},
            'market_context': {'market_sentiment': 'extreme_greed'}
        }
        
        high_risk_recommendations = crypto_api._generate_crypto_recommendations(high_risk_analysis)
        
        assert isinstance(high_risk_recommendations, list)
        assert len(high_risk_recommendations) > 0
        assert any('High portfolio risk' in rec or 'maximum coverage' in rec for rec in high_risk_recommendations)
        assert any('High-risk assets detected' in rec for rec in high_risk_recommendations)
        assert any('extreme' in rec for rec in high_risk_recommendations)
    
    @pytest.mark.asyncio
    async def test_mock_network_stats(self, crypto_api):
        """Test mock network statistics generation"""
        network_stats = await crypto_api._get_mock_network_stats()
        
        assert 'tps' in network_stats
        assert 'block_time' in network_stats
        assert 'validator_count' in network_stats
        assert 'stake_accounts' in network_stats
        assert 'total_staked' in network_stats
        assert 'staking_yield' in network_stats
        assert 'network_fees' in network_stats
        
        # Check realistic ranges
        assert 2000 <= network_stats['tps'] <= 5000
        assert 0.4 <= network_stats['block_time'] <= 0.6
        assert 1500 <= network_stats['validator_count'] <= 2000
        assert 0.06 <= network_stats['staking_yield'] <= 0.08


class TestCryptoConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_get_crypto_data(self):
        """Test get_crypto_data convenience function"""
        with patch('agents.data.crypto.CryptoAPI') as mock_crypto_api:
            mock_api_instance = Mock()
            mock_crypto_data = CryptoData(
                symbol='BTC',
                name='Bitcoin',
                current_price=45000.0,
                price_change_24h=500.0,
                price_change_percentage_24h=1.12,
                market_cap=850000000000.0,
                volume_24h=25000000000.0,
                circulating_supply=19000000.0,
                total_supply=21000000.0,
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_crypto_price = AsyncMock(return_value=mock_crypto_data)
            mock_crypto_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_crypto_data('BTC')
            
            assert result == mock_crypto_data
            mock_api_instance.get_crypto_price.assert_called_once_with('BTC')
    
    @pytest.mark.asyncio
    async def test_get_solana_data(self):
        """Test get_solana_data convenience function"""
        with patch('agents.data.crypto.CryptoAPI') as mock_crypto_api:
            mock_api_instance = Mock()
            mock_solana_data = {
                'sol': {'symbol': 'SOL', 'current_price': 100.0},
                'spl_tokens': {'USDC': {'symbol': 'USDC', 'current_price': 1.0}},
                'network_stats': {'tps': 3000, 'block_time': 0.5},
                'timestamp': datetime.now().isoformat()
            }
            mock_api_instance.get_solana_ecosystem_data = AsyncMock(return_value=mock_solana_data)
            mock_crypto_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_solana_data()
            
            assert result == mock_solana_data
            mock_api_instance.get_solana_ecosystem_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_currency_exchange(self):
        """Test get_currency_exchange convenience function"""
        with patch('agents.data.crypto.CryptoAPI') as mock_crypto_api:
            mock_api_instance = Mock()
            mock_exchange_data = ExchangeRateData(
                base_currency='USD',
                target_currency='EUR',
                exchange_rate=0.85,
                change_24h=-0.01,
                change_percentage_24h=-1.16,
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_exchange_rate = AsyncMock(return_value=mock_exchange_data)
            mock_crypto_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_currency_exchange('USD', 'EUR')
            
            assert result == mock_exchange_data
            mock_api_instance.get_exchange_rate.assert_called_once_with('USD', 'EUR')
    
    @pytest.mark.asyncio
    async def test_get_crypto_risk_analysis(self):
        """Test get_crypto_risk_analysis convenience function"""
        with patch('agents.data.crypto.CryptoAPI') as mock_crypto_api:
            mock_api_instance = Mock()
            mock_risk_analysis = {
                'symbols': ['BTC', 'ETH'],
                'individual_risks': {},
                'portfolio_risk': {},
                'market_context': {},
                'recommendations': [],
                'timestamp': datetime.now().isoformat()
            }
            mock_api_instance.analyze_crypto_risk = AsyncMock(return_value=mock_risk_analysis)
            mock_crypto_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_crypto_risk_analysis(['BTC', 'ETH'])
            
            assert result == mock_risk_analysis
            mock_api_instance.analyze_crypto_risk.assert_called_once_with(['BTC', 'ETH'])


if __name__ == '__main__':
    pytest.main([__file__])
"""Test configuration and fixtures for data API tests"""
import pytest
import os
import asyncio
from unittest.mock import Mock, patch


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock()
    config.enable_cache = True
    config.cache_ttl = 300
    config.openweather_api_key = None
    config.accuweather_api_key = None
    config.flightaware_api_key = None
    config.coingecko_api_key = None
    return config


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'OPENAI_MODEL': 'gpt-4o-mini',
        'OPENAI_TEMPERATURE': '0.3',
        'OPENAI_MAX_TOKENS': '1000',
        'OPENWEATHER_API_KEY': 'test-weather-key',
        'FLIGHTAWARE_API_KEY': 'test-flight-key',
        'COINGECKO_API_KEY': 'test-crypto-key',
        'CACHE_TTL': '300',
        'ENABLE_CACHE': 'true'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing"""
    session = Mock()
    session.get = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_successful_response():
    """Mock successful HTTP response"""
    response = Mock()
    response.status = 200
    response.json = Mock()
    return response


@pytest.fixture
def mock_error_response():
    """Mock error HTTP response"""
    response = Mock()
    response.status = 404
    response.json = Mock()
    return response


@pytest.fixture
def mock_rate_limit_response():
    """Mock rate limit HTTP response"""
    response = Mock()
    response.status = 429
    response.json = Mock()
    return response


# Test data fixtures
@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing"""
    return {
        'name': 'Tokyo',
        'main': {
            'temp': 25.0,
            'humidity': 60,
            'pressure': 1013
        },
        'wind': {
            'speed': 5.0,
            'deg': 180
        },
        'weather': [
            {'description': 'clear sky'}
        ]
    }


@pytest.fixture
def sample_flight_data():
    """Sample flight data for testing"""
    return {
        'flights': [{
            'ident': 'AA123',
            'operator': 'American Airlines',
            'origin': {'code': 'JFK'},
            'destination': {'code': 'LAX'},
            'scheduled_off': '2024-01-01T10:00:00Z',
            'actual_off': '2024-01-01T10:15:00Z',
            'scheduled_on': '2024-01-01T13:00:00Z',
            'actual_on': '2024-01-01T13:15:00Z',
            'status': 'delayed',
            'aircraft_type': 'B737'
        }]
    }


@pytest.fixture
def sample_crypto_data():
    """Sample crypto data for testing"""
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


# Custom pytest markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
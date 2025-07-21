# External API Integration Documentation

## Overview

This document describes the external API integration system for the Solana SigLab Insurance Agent V0.2. The system provides unified access to weather, flight, and cryptocurrency data APIs for parametric insurance analysis.

## Architecture

### Directory Structure

```
agents/
├── data/
│   ├── __init__.py          # API exports
│   ├── weather.py           # Weather API integration
│   ├── flight.py            # Flight API integration
│   ├── crypto.py            # Cryptocurrency API integration
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py      # Test configuration
│       ├── test_weather.py  # Weather API tests
│       ├── test_flight.py   # Flight API tests
│       ├── test_crypto.py   # Crypto API tests
│       └── test_integration.py  # Integration tests
├── core/
│   └── config.py            # Configuration management
```

### Design Principles

1. **Unified Interface**: All APIs follow the same async context manager pattern
2. **Fallback Support**: Mock data generation when API keys are not available
3. **Caching Strategy**: Configurable TTL-based caching for API responses
4. **Error Handling**: Graceful degradation and comprehensive error logging
5. **Type Safety**: Full type hints and Pydantic-style data validation

## API Modules

### 1. Weather API (`agents/data/weather.py`)

#### Data Structures

**WeatherData**
```python
@dataclass
class WeatherData:
    location: str
    temperature: float          # Celsius
    humidity: float            # Percentage
    pressure: float            # hPa
    wind_speed: float          # m/s
    wind_direction: float      # Degrees
    weather_condition: str     # Description
    timestamp: datetime
    source: str               # API source
    confidence: float = 0.9   # Data reliability
```

**TyphoonData**
```python
@dataclass
class TyphoonData:
    name: str
    location: Dict[str, float]      # lat, lon
    max_wind_speed: float          # km/h
    central_pressure: float        # hPa
    movement_speed: float          # km/h
    movement_direction: float      # Degrees
    intensity: str                 # Category
    forecast_path: List[Dict[str, Any]]
    timestamp: datetime
    source: str
```

**EarthquakeData**
```python
@dataclass
class EarthquakeData:
    magnitude: float
    depth: float               # km
    location: Dict[str, float] # lat, lon
    region: str
    timestamp: datetime
    source: str
    intensity: Optional[str] = None
```

#### API Integration

- **Primary**: OpenWeatherMap API (with API key)
- **Secondary**: AccuWeather API (configured but not implemented)
- **Fallback**: Mock data generation

#### Usage Examples

```python
# Basic usage
async with WeatherAPI() as weather_api:
    weather = await weather_api.get_current_weather('Tokyo')
    forecast = await weather_api.get_weather_forecast('Tokyo', 7)
    risk = await weather_api.analyze_weather_risk('Tokyo', 'typhoon')

# Convenience functions
weather_data = await get_weather_data('Tokyo')
risk_analysis = await get_weather_risk_analysis('Tokyo', 'general')
```

### 2. Flight API (`agents/data/flight.py`)

#### Data Structures

**FlightData**
```python
@dataclass
class FlightData:
    flight_number: str
    airline: str
    origin: str               # Airport code
    destination: str          # Airport code
    scheduled_departure: datetime
    actual_departure: Optional[datetime]
    scheduled_arrival: datetime
    actual_arrival: Optional[datetime]
    status: str              # scheduled, delayed, cancelled, etc.
    delay_minutes: int
    aircraft_type: str
    timestamp: datetime
    source: str
    confidence: float = 0.9
```

**AirportData**
```python
@dataclass
class AirportData:
    airport_code: str
    airport_name: str
    city: str
    country: str
    total_flights: int
    on_time_flights: int
    delayed_flights: int
    cancelled_flights: int
    average_delay: float     # minutes
    weather_condition: str
    timestamp: datetime
    source: str
```

**AirlineData**
```python
@dataclass
class AirlineData:
    airline_code: str
    airline_name: str
    total_flights: int
    on_time_rate: float      # 0-1
    average_delay: float     # minutes
    cancellation_rate: float # 0-1
    reliability_score: float # 0-1
    timestamp: datetime
    source: str
```

#### API Integration

- **Primary**: FlightAware API (with API key)
- **Fallback**: Mock data generation with realistic flight patterns

#### Usage Examples

```python
# Basic usage
async with FlightAPI() as flight_api:
    flight = await flight_api.get_flight_status('AA123')
    airport = await flight_api.get_airport_statistics('JFK')
    airline = await flight_api.get_airline_performance('AA')
    risk = await flight_api.analyze_flight_risk('AA123', 'JFK-LAX', 'AA')

# Convenience functions
flight_info = await get_flight_info('AA123')
risk_analysis = await get_flight_risk_analysis('AA123')
```

### 3. Crypto API (`agents/data/crypto.py`)

#### Data Structures

**CryptoData**
```python
@dataclass
class CryptoData:
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
```

**ExchangeRateData**
```python
@dataclass
class ExchangeRateData:
    base_currency: str
    target_currency: str
    exchange_rate: float
    change_24h: float
    change_percentage_24h: float
    timestamp: datetime
    source: str
```

**MarketIndicators**
```python
@dataclass
class MarketIndicators:
    fear_greed_index: float    # 0-100
    volatility_index: float
    inflation_rate: float
    interest_rate: float
    market_sentiment: str      # extreme_fear, fear, neutral, greed, extreme_greed
    timestamp: datetime
    source: str
```

#### API Integration

- **Primary**: CoinGecko API (with API key)
- **Fallback**: Mock data generation with realistic market patterns

#### Usage Examples

```python
# Basic usage
async with CryptoAPI() as crypto_api:
    crypto = await crypto_api.get_crypto_price('BTC')
    solana = await crypto_api.get_solana_ecosystem_data()
    exchange = await crypto_api.get_exchange_rate('USD', 'EUR')
    indicators = await crypto_api.get_market_indicators()
    risk = await crypto_api.analyze_crypto_risk(['BTC', 'ETH', 'SOL'])

# Convenience functions
crypto_data = await get_crypto_data('BTC')
risk_analysis = await get_crypto_risk_analysis(['BTC', 'ETH'])
```

## Configuration

### Environment Variables

```bash
# API Keys
OPENWEATHER_API_KEY=your-openweather-api-key
ACCUWEATHER_API_KEY=your-accuweather-api-key
FLIGHTAWARE_API_KEY=your-flightaware-api-key
COINGECKO_API_KEY=your-coingecko-api-key

# Cache Configuration
CACHE_TTL=300              # 5 minutes
ENABLE_CACHE=true
```

### Configuration Class

```python
class AgentConfig:
    # External API settings
    openweather_api_key: Optional[str]
    accuweather_api_key: Optional[str]
    flightaware_api_key: Optional[str]
    coingecko_api_key: Optional[str]
    
    # Cache settings
    cache_ttl: int = 300       # seconds
    enable_cache: bool = True
```

## Caching Strategy

### Implementation

- **Storage**: In-memory dictionary cache per API instance
- **TTL**: Configurable time-to-live (default: 5 minutes)
- **Keys**: Unique cache keys based on API endpoint and parameters
- **Invalidation**: Automatic expiration based on timestamp

### Cache Keys

```python
# Weather API
f"weather_{location}"
f"forecast_{location}_{days}"
f"typhoon_{region}"

# Flight API
f"flight_{flight_number}_{date}"
f"airport_{airport_code}"
f"airline_{airline_code}"

# Crypto API
f"crypto_{symbol.lower()}"
f"exchange_{base_currency}_{target_currency}"
f"portfolio_volatility_{hash(str(portfolio))}"
```

## Error Handling

### Strategy

1. **API Failures**: Graceful fallback to mock data
2. **Rate Limits**: Proper handling of 429 responses
3. **Network Errors**: Retry logic with exponential backoff
4. **Data Validation**: Type checking and range validation
5. **Logging**: Comprehensive error logging with context

### Error Categories

```python
# API Response Errors
- 200: Success
- 429: Rate limit exceeded
- 404: Resource not found
- 500: Server error

# Application Errors
- InvalidApiKey: API key not configured or invalid
- DataValidationError: Response data validation failed
- CacheError: Cache operations failed
- NetworkError: Network connectivity issues
```

## Testing

### Test Structure

```
agents/data/tests/
├── test_weather.py          # Weather API unit tests
├── test_flight.py           # Flight API unit tests
├── test_crypto.py           # Crypto API unit tests
├── test_integration.py      # Cross-module integration tests
└── conftest.py             # Test configuration and fixtures
```

### Test Categories

1. **Unit Tests**: Individual API module testing
2. **Integration Tests**: Cross-module functionality
3. **Performance Tests**: Load and response time testing
4. **Mock Data Tests**: Fallback data generation testing

### Running Tests

```bash
# Run all tests
python -m pytest agents/data/tests/ -v

# Run specific module tests
python -m pytest agents/data/tests/test_weather.py -v

# Run with coverage
python -m pytest agents/data/tests/ --cov=agents.data --cov-report=html

# Run integration tests only
python -m pytest agents/data/tests/test_integration.py -v -m integration

# Run performance tests
python -m pytest agents/data/tests/test_integration.py -v -m slow
```

## Risk Analysis

### Weather Risk Factors

```python
def analyze_weather_risk(location: str, event_type: str) -> Dict[str, Any]:
    """
    Risk factors:
    - Current weather conditions
    - 7-day forecast extremes
    - Historical weather patterns
    - Seasonal adjustments
    - Event-specific risks (typhoon, earthquake, etc.)
    """
```

### Flight Risk Factors

```python
def analyze_flight_risk(flight_number: str, route: str, airline: str) -> Dict[str, Any]:
    """
    Risk factors:
    - Flight delay history
    - Airline performance metrics
    - Route-specific delay patterns
    - Weather conditions at origin/destination
    - Seasonal adjustment factors
    """
```

### Crypto Risk Factors

```python
def analyze_crypto_risk(symbols: List[str]) -> Dict[str, Any]:
    """
    Risk factors:
    - Price volatility (24h, 7d, 30d)
    - Market capitalization
    - Trading volume and liquidity
    - Correlation analysis
    - Market sentiment indicators
    """
```

## Performance Considerations

### Optimization Strategies

1. **Async Operations**: All API calls use async/await
2. **Concurrent Requests**: Batch API calls using asyncio.gather()
3. **Connection Pooling**: Reuse aiohttp sessions
4. **Caching**: Reduce API calls with intelligent caching
5. **Rate Limiting**: Respect API rate limits

### Benchmarks

```python
# Target Performance (with caching)
- Weather API: < 100ms per request
- Flight API: < 200ms per request
- Crypto API: < 150ms per request
- Risk Analysis: < 500ms per analysis

# Concurrent Performance
- 10 concurrent requests: < 2 seconds
- 50 concurrent requests: < 5 seconds
```

## Security Considerations

### API Key Management

1. **Environment Variables**: Never hard-code API keys
2. **Key Rotation**: Support for key rotation without downtime
3. **Rate Limiting**: Implement client-side rate limiting
4. **Error Handling**: Don't expose API keys in error messages

### Data Privacy

1. **Data Minimization**: Only collect necessary data
2. **Retention Policies**: Implement data retention policies
3. **Anonymization**: Remove PII from cached data
4. **Encryption**: Encrypt sensitive data in transit and at rest

## Future Enhancements

### Planned Features

1. **Additional APIs**: 
   - More weather data sources
   - Additional flight tracking APIs
   - DeFi protocol integration

2. **Advanced Caching**:
   - Redis integration
   - Distributed caching
   - Cache warming strategies

3. **Monitoring**:
   - API health checks
   - Performance metrics
   - Alert systems

4. **Data Quality**:
   - Data validation rules
   - Anomaly detection
   - Quality scoring

## Troubleshooting

### Common Issues

1. **API Key Errors**:
   ```bash
   ValueError: OPENWEATHER_API_KEY environment variable is not set
   ```
   **Solution**: Set the required environment variable

2. **Rate Limit Exceeded**:
   ```bash
   WARNING: OpenWeatherMap API rate limit exceeded
   ```
   **Solution**: Implement exponential backoff or upgrade API plan

3. **Network Timeouts**:
   ```bash
   ERROR: Error fetching OpenWeatherMap data: timeout
   ```
   **Solution**: Increase timeout values or implement retry logic

4. **Cache Issues**:
   ```bash
   WARNING: Could not set cache data
   ```
   **Solution**: Check cache configuration and memory limits

### Debug Mode

```python
# Enable debug mode
import os
os.environ['AGENT_DEBUG'] = 'true'

# Check configuration
from agents.core.config import get_config
config = get_config()
print(config.to_dict())
```

## Changelog

### Version 0.2.0 (Current)
- ✅ Complete weather API integration
- ✅ Complete flight API integration  
- ✅ Complete crypto API integration
- ✅ Unified caching system
- ✅ Comprehensive test suite
- ✅ Mock data fallback system
- ✅ Risk analysis framework

### Version 0.1.0
- Basic agent framework
- Simple tool integration
- Mock data only

---

*Last updated: 2024-01-17*
*Version: 0.2.0*
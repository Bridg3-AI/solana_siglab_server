# External Data API Integration

## Quick Start

### Installation

```bash
# Install required dependencies
pip install aiohttp dataclasses typing

# Set environment variables
export OPENWEATHER_API_KEY="your-api-key"
export FLIGHTAWARE_API_KEY="your-api-key"
export COINGECKO_API_KEY="your-api-key"
```

### Basic Usage

```python
import asyncio
from agents.data.weather import get_weather_data
from agents.data.flight import get_flight_info
from agents.data.crypto import get_crypto_data

async def main():
    # Get weather data
    weather = await get_weather_data('Tokyo')
    print(f"Temperature: {weather.temperature}°C")
    
    # Get flight info
    flight = await get_flight_info('AA123')
    print(f"Status: {flight.status}")
    
    # Get crypto data
    crypto = await get_crypto_data('BTC')
    print(f"Price: ${crypto.current_price:,.2f}")

asyncio.run(main())
```

## API Modules

### Weather API

```python
from agents.data.weather import WeatherAPI, get_weather_risk_analysis

# Direct API usage
async with WeatherAPI() as api:
    weather = await api.get_current_weather('Tokyo')
    forecast = await api.get_weather_forecast('Tokyo', 7)
    typhoons = await api.get_typhoon_data()
    earthquakes = await api.get_earthquake_data()
    risk = await api.analyze_weather_risk('Tokyo', 'general')

# Convenience functions
weather_data = await get_weather_data('Tokyo')
risk_analysis = await get_weather_risk_analysis('Tokyo', 'typhoon')
```

### Flight API

```python
from agents.data.flight import FlightAPI, get_flight_risk_analysis

# Direct API usage
async with FlightAPI() as api:
    flight = await api.get_flight_status('AA123')
    airport = await api.get_airport_statistics('JFK')
    airline = await api.get_airline_performance('AA')
    delays = await api.get_delay_statistics('JFK-LAX', 'AA')
    risk = await api.analyze_flight_risk('AA123', 'JFK-LAX', 'AA')

# Convenience functions
flight_info = await get_flight_info('AA123')
risk_analysis = await get_flight_risk_analysis('AA123')
```

### Crypto API

```python
from agents.data.crypto import CryptoAPI, get_crypto_risk_analysis

# Direct API usage
async with CryptoAPI() as api:
    crypto = await api.get_crypto_price('BTC')
    solana = await api.get_solana_ecosystem_data()
    exchange = await api.get_exchange_rate('USD', 'EUR')
    indicators = await api.get_market_indicators()
    portfolio = await api.calculate_portfolio_volatility({'BTC': 0.5, 'ETH': 0.5})
    risk = await api.analyze_crypto_risk(['BTC', 'ETH', 'SOL'])

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

# Cache Settings
CACHE_TTL=300              # 5 minutes
ENABLE_CACHE=true

# Agent Settings
AGENT_DEBUG=false
AGENT_TIMEOUT=30
```

### Configuration in Code

```python
from agents.core.config import get_config

config = get_config()
print(f"Cache TTL: {config.cache_ttl}s")
print(f"Cache enabled: {config.enable_cache}")
```

## Data Structures

### Weather Data

```python
@dataclass
class WeatherData:
    location: str
    temperature: float          # Celsius
    humidity: float            # Percentage
    pressure: float            # hPa
    wind_speed: float          # m/s
    wind_direction: float      # Degrees
    weather_condition: str
    timestamp: datetime
    source: str
    confidence: float = 0.9
```

### Flight Data

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
    status: str
    delay_minutes: int
    aircraft_type: str
    timestamp: datetime
    source: str
    confidence: float = 0.9
```

### Crypto Data

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

## Risk Analysis

### Weather Risk

```python
risk = await get_weather_risk_analysis('Tokyo', 'typhoon')
print(f"Risk Score: {risk['risk_score']:.2f}")
print(f"Recommendations: {risk['recommendations']}")
```

### Flight Risk

```python
risk = await get_flight_risk_analysis('AA123', 'JFK-LAX', 'AA')
print(f"Risk Score: {risk['risk_score']:.2f}")
print(f"Delay Probability: {risk['risk_factors']['delay_statistics']['overall_delay_probability']:.1%}")
```

### Crypto Risk

```python
risk = await get_crypto_risk_analysis(['BTC', 'ETH', 'SOL'])
print(f"Portfolio Risk: {risk['portfolio_risk']['risk_level']}")
print(f"Individual Risks: {risk['individual_risks']}")
```

## Testing

### Run Tests

```bash
# Run all tests
python -m pytest agents/data/tests/ -v

# Run specific tests
python -m pytest agents/data/tests/test_weather.py -v
python -m pytest agents/data/tests/test_flight.py -v
python -m pytest agents/data/tests/test_crypto.py -v

# Run integration tests
python -m pytest agents/data/tests/test_integration.py -v

# Run with coverage
python -m pytest agents/data/tests/ --cov=agents.data --cov-report=html
```

### Simple Test Script

```python
# test_simple.py
import asyncio
from agents.data.weather import get_weather_data
from agents.data.flight import get_flight_info
from agents.data.crypto import get_crypto_data

async def test_all():
    weather = await get_weather_data('Tokyo')
    flight = await get_flight_info('AA123')
    crypto = await get_crypto_data('BTC')
    
    print(f"Weather: {weather.location} - {weather.temperature}°C")
    print(f"Flight: {flight.flight_number} - {flight.status}")
    print(f"Crypto: {crypto.symbol} - ${crypto.current_price:,.2f}")

asyncio.run(test_all())
```

## Error Handling

### Common Patterns

```python
try:
    weather = await get_weather_data('Tokyo')
except Exception as e:
    print(f"Weather API error: {e}")
    # Fallback to mock data is handled automatically
```

### API Status Codes

- `200`: Success
- `429`: Rate limit exceeded (handled with fallback)
- `404`: Resource not found (handled with fallback)
- `500`: Server error (handled with fallback)

## Caching

### Cache Behavior

- **TTL**: 5 minutes default (configurable)
- **Scope**: Per API instance
- **Keys**: Unique per endpoint and parameters
- **Invalidation**: Automatic based on timestamp

### Cache Control

```python
# Disable caching
os.environ['ENABLE_CACHE'] = 'false'

# Custom TTL
os.environ['CACHE_TTL'] = '600'  # 10 minutes
```

## Performance

### Benchmarks

- Single API call: < 200ms
- Concurrent calls (10): < 2 seconds
- Risk analysis: < 500ms

### Optimization Tips

1. Use async/await for concurrent operations
2. Enable caching for repeated requests
3. Use specific data fields to reduce response size
4. Implement proper error handling

## Troubleshooting

### No API Key

```python
# Error: API key not configured
# Solution: Set environment variable
export OPENWEATHER_API_KEY="your-key"
```

### Rate Limit

```python
# Warning: Rate limit exceeded
# Solution: Automatic fallback to mock data
```

### Import Errors

```python
# Error: No module named 'aiohttp'
# Solution: Install dependencies
pip install aiohttp
```

## Examples

### Weather Insurance Analysis

```python
async def analyze_weather_insurance(location: str, event_type: str):
    risk = await get_weather_risk_analysis(location, event_type)
    
    if risk['risk_score'] > 0.7:
        return "High risk - premium coverage recommended"
    elif risk['risk_score'] > 0.4:
        return "Moderate risk - standard coverage"
    else:
        return "Low risk - basic coverage"
```

### Flight Delay Insurance

```python
async def analyze_flight_insurance(flight_number: str):
    risk = await get_flight_risk_analysis(flight_number)
    
    delay_prob = risk['risk_factors'].get('delay_statistics', {}).get('overall_delay_probability', 0)
    
    if delay_prob > 0.5:
        return "High delay risk - comprehensive coverage recommended"
    else:
        return "Low delay risk - basic coverage"
```

### Crypto Portfolio Insurance

```python
async def analyze_crypto_insurance(symbols: List[str]):
    risk = await get_crypto_risk_analysis(symbols)
    
    portfolio_risk = risk['portfolio_risk']['risk_level']
    
    if portfolio_risk == 'very_high':
        return "Maximum coverage required"
    elif portfolio_risk == 'high':
        return "Enhanced coverage recommended"
    else:
        return "Standard coverage sufficient"
```

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the comprehensive documentation in `docs/external-api-integration.md`
3. Run the test suite to verify functionality
4. Check environment variable configuration

---

*For complete documentation, see `docs/external-api-integration.md`*
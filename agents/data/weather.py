"""Weather data API integration module"""
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
class WeatherData:
    """Weather data structure"""
    location: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    weather_condition: str
    timestamp: datetime
    source: str
    confidence: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class TyphoonData:
    """Typhoon-specific data structure"""
    name: str
    location: Dict[str, float]  # lat, lon
    max_wind_speed: float
    central_pressure: float
    movement_speed: float
    movement_direction: float
    intensity: str
    forecast_path: List[Dict[str, Any]]
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class EarthquakeData:
    """Earthquake data structure"""
    magnitude: float
    depth: float
    location: Dict[str, float]  # lat, lon
    region: str
    timestamp: datetime
    source: str
    intensity: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class WeatherAPI:
    """Weather API integration class"""
    
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
    
    async def get_current_weather(self, location: str) -> Optional[WeatherData]:
        """Get current weather data for a location"""
        cache_key = f"weather_{location}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return WeatherData(**cached_data)
        
        # Try OpenWeatherMap API first
        weather_data = await self._get_openweather_data(location)
        
        if weather_data:
            await self._set_cached_data(cache_key, weather_data.to_dict())
            return weather_data
        
        # Fallback to mock data for development
        return await self._get_mock_weather_data(location)
    
    async def _get_openweather_data(self, location: str) -> Optional[WeatherData]:
        """Get weather data from OpenWeatherMap API"""
        if not self.config.openweather_api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.config.openweather_api_key,
                'units': 'metric'
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return WeatherData(
                        location=data['name'],
                        temperature=data['main']['temp'],
                        humidity=data['main']['humidity'],
                        pressure=data['main']['pressure'],
                        wind_speed=data['wind'].get('speed', 0),
                        wind_direction=data['wind'].get('deg', 0),
                        weather_condition=data['weather'][0]['description'],
                        timestamp=datetime.now(),
                        source='openweathermap',
                        confidence=0.95
                    )
                else:
                    logger.error(f"OpenWeatherMap API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching OpenWeatherMap data: {e}")
            return None
    
    async def _get_mock_weather_data(self, location: str) -> WeatherData:
        """Generate mock weather data for development"""
        import random
        
        # Mock data based on location
        base_temp = {
            'tokyo': 25.0,
            'seoul': 20.0,
            'new york': 18.0,
            'london': 15.0
        }.get(location.lower(), 22.0)
        
        return WeatherData(
            location=location,
            temperature=base_temp + random.uniform(-5, 5),
            humidity=random.uniform(40, 80),
            pressure=random.uniform(1000, 1030),
            wind_speed=random.uniform(0, 20),
            wind_direction=random.uniform(0, 360),
            weather_condition=random.choice(['clear', 'cloudy', 'rainy', 'stormy']),
            timestamp=datetime.now(),
            source='mock',
            confidence=0.8
        )
    
    async def get_typhoon_data(self, region: str = 'asia') -> List[TyphoonData]:
        """Get active typhoon data for a region"""
        cache_key = f"typhoon_{region}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return [TyphoonData(**item) for item in cached_data]
        
        # Mock typhoon data for development
        typhoon_data = await self._get_mock_typhoon_data(region)
        
        if typhoon_data:
            await self._set_cached_data(cache_key, [t.to_dict() for t in typhoon_data])
        
        return typhoon_data
    
    async def _get_mock_typhoon_data(self, region: str) -> List[TyphoonData]:
        """Generate mock typhoon data"""
        import random
        
        # Simulate 0-2 active typhoons
        num_typhoons = random.randint(0, 2)
        typhoons = []
        
        for i in range(num_typhoons):
            typhoon = TyphoonData(
                name=f"Typhoon_{chr(65 + i)}",
                location={'lat': random.uniform(10, 40), 'lon': random.uniform(120, 150)},
                max_wind_speed=random.uniform(60, 200),
                central_pressure=random.uniform(900, 1000),
                movement_speed=random.uniform(10, 50),
                movement_direction=random.uniform(0, 360),
                intensity=random.choice(['tropical storm', 'typhoon', 'super typhoon']),
                forecast_path=[
                    {'lat': random.uniform(10, 40), 'lon': random.uniform(120, 150), 'time': '2024-01-01T00:00:00'}
                ],
                timestamp=datetime.now(),
                source='mock'
            )
            typhoons.append(typhoon)
        
        return typhoons
    
    async def get_earthquake_data(self, region: str = 'global', min_magnitude: float = 4.0) -> List[EarthquakeData]:
        """Get recent earthquake data"""
        cache_key = f"earthquake_{region}_{min_magnitude}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return [EarthquakeData(**item) for item in cached_data]
        
        # Mock earthquake data for development
        earthquake_data = await self._get_mock_earthquake_data(region, min_magnitude)
        
        if earthquake_data:
            await self._set_cached_data(cache_key, [e.to_dict() for e in earthquake_data])
        
        return earthquake_data
    
    async def _get_mock_earthquake_data(self, region: str, min_magnitude: float) -> List[EarthquakeData]:
        """Generate mock earthquake data"""
        import random
        
        # Simulate 0-5 recent earthquakes
        num_earthquakes = random.randint(0, 5)
        earthquakes = []
        
        for i in range(num_earthquakes):
            magnitude = random.uniform(min_magnitude, 8.0)
            earthquake = EarthquakeData(
                magnitude=magnitude,
                depth=random.uniform(5, 500),
                location={'lat': random.uniform(-60, 60), 'lon': random.uniform(-180, 180)},
                region=f"Region_{i}",
                timestamp=datetime.now() - timedelta(hours=random.randint(0, 168)),  # Within last week
                source='mock',
                intensity=self._get_intensity_from_magnitude(magnitude)
            )
            earthquakes.append(earthquake)
        
        return earthquakes
    
    def _get_intensity_from_magnitude(self, magnitude: float) -> str:
        """Convert magnitude to intensity scale"""
        if magnitude < 3.0:
            return 'not felt'
        elif magnitude < 4.0:
            return 'weak'
        elif magnitude < 5.0:
            return 'light'
        elif magnitude < 6.0:
            return 'moderate'
        elif magnitude < 7.0:
            return 'strong'
        elif magnitude < 8.0:
            return 'major'
        else:
            return 'great'
    
    async def get_weather_forecast(self, location: str, days: int = 5) -> List[WeatherData]:
        """Get weather forecast for multiple days"""
        cache_key = f"forecast_{location}_{days}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return [WeatherData(**item) for item in cached_data]
        
        # Mock forecast data for development
        forecast_data = await self._get_mock_forecast_data(location, days)
        
        if forecast_data:
            await self._set_cached_data(cache_key, [f.to_dict() for f in forecast_data])
        
        return forecast_data
    
    async def _get_mock_forecast_data(self, location: str, days: int) -> List[WeatherData]:
        """Generate mock forecast data"""
        import random
        
        forecasts = []
        base_weather = await self._get_mock_weather_data(location)
        
        for i in range(days):
            forecast = WeatherData(
                location=location,
                temperature=base_weather.temperature + random.uniform(-3, 3),
                humidity=base_weather.humidity + random.uniform(-10, 10),
                pressure=base_weather.pressure + random.uniform(-5, 5),
                wind_speed=base_weather.wind_speed + random.uniform(-2, 2),
                wind_direction=base_weather.wind_direction + random.uniform(-30, 30),
                weather_condition=random.choice(['clear', 'cloudy', 'rainy', 'stormy']),
                timestamp=datetime.now() + timedelta(days=i+1),
                source='mock',
                confidence=0.8 - (i * 0.1)  # Confidence decreases with time
            )
            forecasts.append(forecast)
        
        return forecasts
    
    async def analyze_weather_risk(self, location: str, event_type: str = 'general') -> Dict[str, Any]:
        """Analyze weather-related risk for insurance purposes"""
        current_weather = await self.get_current_weather(location)
        forecast = await self.get_weather_forecast(location, 7)
        
        if event_type == 'typhoon':
            typhoons = await self.get_typhoon_data()
            risk_score = self._calculate_typhoon_risk(current_weather, forecast, typhoons)
        elif event_type == 'earthquake':
            earthquakes = await self.get_earthquake_data()
            risk_score = self._calculate_earthquake_risk(current_weather, earthquakes)
        else:
            risk_score = self._calculate_general_weather_risk(current_weather, forecast)
        
        return {
            'location': location,
            'event_type': event_type,
            'risk_score': risk_score,
            'current_weather': current_weather.to_dict() if current_weather else None,
            'forecast_summary': self._summarize_forecast(forecast),
            'timestamp': datetime.now().isoformat(),
            'confidence': current_weather.confidence if current_weather else 0.5
        }
    
    def _calculate_typhoon_risk(self, current_weather: Optional[WeatherData], 
                              forecast: List[WeatherData], 
                              typhoons: List[TyphoonData]) -> float:
        """Calculate typhoon risk score"""
        base_risk = 0.1
        
        # Increase risk if there are active typhoons
        if typhoons:
            base_risk += len(typhoons) * 0.2
        
        # Increase risk based on weather conditions
        if current_weather:
            if current_weather.wind_speed > 30:
                base_risk += 0.3
            if current_weather.pressure < 980:
                base_risk += 0.2
        
        # Consider forecast
        high_wind_days = sum(1 for f in forecast if f.wind_speed > 25)
        base_risk += high_wind_days * 0.1
        
        return min(base_risk, 1.0)
    
    def _calculate_earthquake_risk(self, current_weather: Optional[WeatherData], 
                                 earthquakes: List[EarthquakeData]) -> float:
        """Calculate earthquake risk score"""
        base_risk = 0.05
        
        # Recent earthquake activity increases risk
        recent_earthquakes = [e for e in earthquakes if 
                            datetime.now() - e.timestamp < timedelta(days=30)]
        
        if recent_earthquakes:
            max_magnitude = max(e.magnitude for e in recent_earthquakes)
            base_risk += (max_magnitude - 4.0) * 0.1
        
        return min(base_risk, 1.0)
    
    def _calculate_general_weather_risk(self, current_weather: Optional[WeatherData], 
                                      forecast: List[WeatherData]) -> float:
        """Calculate general weather risk score"""
        base_risk = 0.1
        
        if current_weather:
            # Extreme temperature
            if abs(current_weather.temperature) > 35 or current_weather.temperature < -10:
                base_risk += 0.2
            
            # High wind
            if current_weather.wind_speed > 20:
                base_risk += 0.1
            
            # Stormy conditions
            if 'storm' in current_weather.weather_condition.lower():
                base_risk += 0.2
        
        # Consider forecast extremes
        extreme_days = sum(1 for f in forecast if 
                          abs(f.temperature) > 30 or f.wind_speed > 20)
        base_risk += extreme_days * 0.05
        
        return min(base_risk, 1.0)
    
    def _summarize_forecast(self, forecast: List[WeatherData]) -> Dict[str, Any]:
        """Summarize forecast data"""
        if not forecast:
            return {}
        
        return {
            'avg_temperature': sum(f.temperature for f in forecast) / len(forecast),
            'max_temperature': max(f.temperature for f in forecast),
            'min_temperature': min(f.temperature for f in forecast),
            'avg_wind_speed': sum(f.wind_speed for f in forecast) / len(forecast),
            'max_wind_speed': max(f.wind_speed for f in forecast),
            'rainy_days': sum(1 for f in forecast if 'rain' in f.weather_condition.lower()),
            'stormy_days': sum(1 for f in forecast if 'storm' in f.weather_condition.lower())
        }


# Convenience functions for direct use
async def get_weather_data(location: str) -> Optional[WeatherData]:
    """Get current weather data for a location"""
    async with WeatherAPI() as weather_api:
        return await weather_api.get_current_weather(location)

async def get_weather_risk_analysis(location: str, event_type: str = 'general') -> Dict[str, Any]:
    """Get weather risk analysis for insurance purposes"""
    async with WeatherAPI() as weather_api:
        return await weather_api.analyze_weather_risk(location, event_type)

async def get_typhoon_tracking() -> List[TyphoonData]:
    """Get current typhoon tracking data"""
    async with WeatherAPI() as weather_api:
        return await weather_api.get_typhoon_data()

async def get_earthquake_monitoring(min_magnitude: float = 4.0) -> List[EarthquakeData]:
    """Get recent earthquake monitoring data"""
    async with WeatherAPI() as weather_api:
        return await weather_api.get_earthquake_data(min_magnitude=min_magnitude)
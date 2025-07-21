"""Tests for weather API module"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from agents.data.weather import WeatherAPI, WeatherData, TyphoonData, EarthquakeData
from agents.data.weather import get_weather_data, get_weather_risk_analysis


class TestWeatherAPI:
    """Test cases for WeatherAPI class"""
    
    @pytest.fixture
    def weather_api(self):
        """Create WeatherAPI instance for testing"""
        return WeatherAPI()
    
    @pytest.fixture
    def mock_weather_data(self):
        """Mock weather data for testing"""
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
    
    def test_weather_data_creation(self):
        """Test WeatherData dataclass creation"""
        weather_data = WeatherData(
            location='Tokyo',
            temperature=25.0,
            humidity=60,
            pressure=1013.0,
            wind_speed=5.0,
            wind_direction=180.0,
            weather_condition='clear sky',
            timestamp=datetime.now(),
            source='test'
        )
        
        assert weather_data.location == 'Tokyo'
        assert weather_data.temperature == 25.0
        assert weather_data.confidence == 0.9  # default value
        
        # Test dictionary conversion
        weather_dict = weather_data.to_dict()
        assert weather_dict['location'] == 'Tokyo'
        assert 'timestamp' in weather_dict
        assert isinstance(weather_dict['timestamp'], str)
    
    def test_typhoon_data_creation(self):
        """Test TyphoonData dataclass creation"""
        typhoon_data = TyphoonData(
            name='Typhoon_A',
            location={'lat': 35.0, 'lon': 140.0},
            max_wind_speed=150.0,
            central_pressure=950.0,
            movement_speed=20.0,
            movement_direction=315.0,
            intensity='super typhoon',
            forecast_path=[],
            timestamp=datetime.now(),
            source='test'
        )
        
        assert typhoon_data.name == 'Typhoon_A'
        assert typhoon_data.intensity == 'super typhoon'
        assert typhoon_data.location['lat'] == 35.0
    
    def test_earthquake_data_creation(self):
        """Test EarthquakeData dataclass creation"""
        earthquake_data = EarthquakeData(
            magnitude=7.0,
            depth=20.0,
            location={'lat': 35.0, 'lon': 140.0},
            region='Tokyo',
            timestamp=datetime.now(),
            source='test'
        )
        
        assert earthquake_data.magnitude == 7.0
        assert earthquake_data.region == 'Tokyo'
        assert earthquake_data.intensity is None  # default value
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, weather_api):
        """Test caching functionality"""
        # Mock configuration
        weather_api.config.enable_cache = True
        weather_api.config.cache_ttl = 300
        
        # Test setting and getting cache
        test_data = {'test': 'data'}
        await weather_api._set_cached_data('test_key', test_data)
        
        cached_data = await weather_api._get_cached_data('test_key')
        assert cached_data == test_data
        
        # Test cache expiration
        weather_api.config.cache_ttl = 0
        await asyncio.sleep(0.1)
        
        expired_data = await weather_api._get_cached_data('test_key')
        assert expired_data is None
    
    @pytest.mark.asyncio
    async def test_openweather_api_integration(self, weather_api, mock_weather_data):
        """Test OpenWeatherMap API integration"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_weather_data)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call
            result = await weather_api._get_openweather_data('Tokyo')
            
            assert result is not None
            assert result.location == 'Tokyo'
            assert result.temperature == 25.0
            assert result.source == 'openweathermap'
    
    @pytest.mark.asyncio
    async def test_openweather_api_error_handling(self, weather_api):
        """Test OpenWeatherMap API error handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock API error response
            mock_response = Mock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call with error
            result = await weather_api._get_openweather_data('InvalidCity')
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_mock_weather_data_generation(self, weather_api):
        """Test mock weather data generation"""
        result = await weather_api._get_mock_weather_data('Tokyo')
        
        assert result is not None
        assert result.location == 'Tokyo'
        assert result.source == 'mock'
        assert result.confidence == 0.8
        assert -10 <= result.temperature <= 35  # reasonable range
    
    @pytest.mark.asyncio
    async def test_get_current_weather(self, weather_api):
        """Test get_current_weather method"""
        # Mock the API key to force fallback to mock data
        weather_api.config.openweather_api_key = None
        
        result = await weather_api.get_current_weather('Tokyo')
        
        assert result is not None
        assert result.location == 'Tokyo'
        assert result.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_typhoon_data_retrieval(self, weather_api):
        """Test typhoon data retrieval"""
        typhoons = await weather_api.get_typhoon_data('asia')
        
        assert isinstance(typhoons, list)
        assert len(typhoons) <= 2  # Mock generates 0-2 typhoons
        
        if typhoons:
            typhoon = typhoons[0]
            assert isinstance(typhoon, TyphoonData)
            assert typhoon.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_earthquake_data_retrieval(self, weather_api):
        """Test earthquake data retrieval"""
        earthquakes = await weather_api.get_earthquake_data('global', 4.0)
        
        assert isinstance(earthquakes, list)
        assert len(earthquakes) <= 5  # Mock generates 0-5 earthquakes
        
        if earthquakes:
            earthquake = earthquakes[0]
            assert isinstance(earthquake, EarthquakeData)
            assert earthquake.magnitude >= 4.0
            assert earthquake.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_weather_forecast(self, weather_api):
        """Test weather forecast retrieval"""
        forecast = await weather_api.get_weather_forecast('Tokyo', 5)
        
        assert isinstance(forecast, list)
        assert len(forecast) == 5
        
        for i, day_forecast in enumerate(forecast):
            assert isinstance(day_forecast, WeatherData)
            assert day_forecast.location == 'Tokyo'
            assert day_forecast.source == 'mock'
            # Confidence should decrease with time
            assert day_forecast.confidence == 0.8 - (i * 0.1)
    
    def test_intensity_from_magnitude(self, weather_api):
        """Test earthquake intensity classification"""
        test_cases = [
            (2.0, 'not felt'),
            (3.5, 'weak'),
            (4.5, 'light'),
            (5.5, 'moderate'),
            (6.5, 'strong'),
            (7.5, 'major'),
            (8.5, 'great')
        ]
        
        for magnitude, expected_intensity in test_cases:
            intensity = weather_api._get_intensity_from_magnitude(magnitude)
            assert intensity == expected_intensity
    
    @pytest.mark.asyncio
    async def test_weather_risk_analysis(self, weather_api):
        """Test weather risk analysis"""
        risk_analysis = await weather_api.analyze_weather_risk('Tokyo', 'general')
        
        assert 'location' in risk_analysis
        assert 'event_type' in risk_analysis
        assert 'risk_score' in risk_analysis
        assert 'current_weather' in risk_analysis
        assert 'forecast_summary' in risk_analysis
        assert 'timestamp' in risk_analysis
        assert 'confidence' in risk_analysis
        
        assert risk_analysis['location'] == 'Tokyo'
        assert risk_analysis['event_type'] == 'general'
        assert 0 <= risk_analysis['risk_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_typhoon_risk_calculation(self, weather_api):
        """Test typhoon risk calculation"""
        # Create mock data
        current_weather = WeatherData(
            location='Tokyo',
            temperature=25.0,
            humidity=80,
            pressure=970.0,  # Low pressure
            wind_speed=35.0,  # High wind
            wind_direction=180.0,
            weather_condition='stormy',
            timestamp=datetime.now(),
            source='mock'
        )
        
        forecast = [
            WeatherData(
                location='Tokyo',
                temperature=25.0,
                humidity=80,
                pressure=980.0,
                wind_speed=30.0,  # High wind
                wind_direction=180.0,
                weather_condition='stormy',
                timestamp=datetime.now() + timedelta(days=1),
                source='mock'
            )
        ]
        
        typhoons = [
            TyphoonData(
                name='TestTyphoon',
                location={'lat': 35.0, 'lon': 140.0},
                max_wind_speed=150.0,
                central_pressure=950.0,
                movement_speed=20.0,
                movement_direction=315.0,
                intensity='super typhoon',
                forecast_path=[],
                timestamp=datetime.now(),
                source='mock'
            )
        ]
        
        risk_score = weather_api._calculate_typhoon_risk(current_weather, forecast, typhoons)
        
        assert 0 <= risk_score <= 1
        assert risk_score > 0.5  # Should be high risk due to conditions
    
    def test_forecast_summary(self, weather_api):
        """Test forecast summary generation"""
        forecast = [
            WeatherData(
                location='Tokyo',
                temperature=25.0,
                humidity=60,
                pressure=1013.0,
                wind_speed=5.0,
                wind_direction=180.0,
                weather_condition='clear',
                timestamp=datetime.now(),
                source='mock'
            ),
            WeatherData(
                location='Tokyo',
                temperature=30.0,
                humidity=70,
                pressure=1010.0,
                wind_speed=10.0,
                wind_direction=180.0,
                weather_condition='rainy',
                timestamp=datetime.now() + timedelta(days=1),
                source='mock'
            )
        ]
        
        summary = weather_api._summarize_forecast(forecast)
        
        assert 'avg_temperature' in summary
        assert 'max_temperature' in summary
        assert 'min_temperature' in summary
        assert 'avg_wind_speed' in summary
        assert 'max_wind_speed' in summary
        assert 'rainy_days' in summary
        assert 'stormy_days' in summary
        
        assert summary['avg_temperature'] == 27.5
        assert summary['max_temperature'] == 30.0
        assert summary['min_temperature'] == 25.0
        assert summary['rainy_days'] == 1
        assert summary['stormy_days'] == 0


class TestWeatherConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_get_weather_data(self):
        """Test get_weather_data convenience function"""
        with patch('agents.data.weather.WeatherAPI') as mock_weather_api:
            mock_api_instance = Mock()
            mock_weather_data = WeatherData(
                location='Tokyo',
                temperature=25.0,
                humidity=60,
                pressure=1013.0,
                wind_speed=5.0,
                wind_direction=180.0,
                weather_condition='clear',
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_current_weather = AsyncMock(return_value=mock_weather_data)
            mock_weather_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_weather_data('Tokyo')
            
            assert result == mock_weather_data
            mock_api_instance.get_current_weather.assert_called_once_with('Tokyo')
    
    @pytest.mark.asyncio
    async def test_get_weather_risk_analysis(self):
        """Test get_weather_risk_analysis convenience function"""
        with patch('agents.data.weather.WeatherAPI') as mock_weather_api:
            mock_api_instance = Mock()
            mock_risk_analysis = {
                'location': 'Tokyo',
                'event_type': 'general',
                'risk_score': 0.3,
                'current_weather': None,
                'forecast_summary': {},
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.8
            }
            mock_api_instance.analyze_weather_risk = AsyncMock(return_value=mock_risk_analysis)
            mock_weather_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_weather_risk_analysis('Tokyo', 'general')
            
            assert result == mock_risk_analysis
            mock_api_instance.analyze_weather_risk.assert_called_once_with('Tokyo', 'general')


if __name__ == '__main__':
    pytest.main([__file__])
"""Tests for flight API module"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from agents.data.flight import FlightAPI, FlightData, AirportData, AirlineData
from agents.data.flight import get_flight_info, get_airport_info, get_airline_info, get_flight_risk_analysis


class TestFlightAPI:
    """Test cases for FlightAPI class"""
    
    @pytest.fixture
    def flight_api(self):
        """Create FlightAPI instance for testing"""
        return FlightAPI()
    
    @pytest.fixture
    def mock_flight_data(self):
        """Mock flight data for testing"""
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
    
    def test_flight_data_creation(self):
        """Test FlightData dataclass creation"""
        flight_data = FlightData(
            flight_number='AA123',
            airline='American Airlines',
            origin='JFK',
            destination='LAX',
            scheduled_departure=datetime.now(),
            actual_departure=datetime.now() + timedelta(minutes=15),
            scheduled_arrival=datetime.now() + timedelta(hours=3),
            actual_arrival=datetime.now() + timedelta(hours=3, minutes=15),
            status='delayed',
            delay_minutes=15,
            aircraft_type='B737',
            timestamp=datetime.now(),
            source='test'
        )
        
        assert flight_data.flight_number == 'AA123'
        assert flight_data.airline == 'American Airlines'
        assert flight_data.delay_minutes == 15
        assert flight_data.confidence == 0.9  # default value
        
        # Test dictionary conversion
        flight_dict = flight_data.to_dict()
        assert flight_dict['flight_number'] == 'AA123'
        assert 'scheduled_departure' in flight_dict
        assert isinstance(flight_dict['scheduled_departure'], str)
    
    def test_airport_data_creation(self):
        """Test AirportData dataclass creation"""
        airport_data = AirportData(
            airport_code='JFK',
            airport_name='John F. Kennedy International Airport',
            city='New York',
            country='USA',
            total_flights=500,
            on_time_flights=400,
            delayed_flights=80,
            cancelled_flights=20,
            average_delay=25.5,
            weather_condition='clear',
            timestamp=datetime.now(),
            source='test'
        )
        
        assert airport_data.airport_code == 'JFK'
        assert airport_data.city == 'New York'
        assert airport_data.total_flights == 500
        
        # Test dictionary conversion
        airport_dict = airport_data.to_dict()
        assert airport_dict['airport_code'] == 'JFK'
        assert 'timestamp' in airport_dict
    
    def test_airline_data_creation(self):
        """Test AirlineData dataclass creation"""
        airline_data = AirlineData(
            airline_code='AA',
            airline_name='American Airlines',
            total_flights=1000,
            on_time_rate=0.85,
            average_delay=20.0,
            cancellation_rate=0.02,
            reliability_score=0.84,
            timestamp=datetime.now(),
            source='test'
        )
        
        assert airline_data.airline_code == 'AA'
        assert airline_data.airline_name == 'American Airlines'
        assert airline_data.on_time_rate == 0.85
        
        # Test dictionary conversion
        airline_dict = airline_data.to_dict()
        assert airline_dict['airline_code'] == 'AA'
        assert 'timestamp' in airline_dict
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, flight_api):
        """Test caching functionality"""
        # Mock configuration
        flight_api.config.enable_cache = True
        flight_api.config.cache_ttl = 300
        
        # Test setting and getting cache
        test_data = {'test': 'flight_data'}
        await flight_api._set_cached_data('test_flight_key', test_data)
        
        cached_data = await flight_api._get_cached_data('test_flight_key')
        assert cached_data == test_data
        
        # Test cache expiration
        flight_api.config.cache_ttl = 0
        await asyncio.sleep(0.1)
        
        expired_data = await flight_api._get_cached_data('test_flight_key')
        assert expired_data is None
    
    @pytest.mark.asyncio
    async def test_flightaware_api_integration(self, flight_api, mock_flight_data):
        """Test FlightAware API integration"""
        # Mock API key
        flight_api.config.flightaware_api_key = 'test_key'
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_flight_data)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call
            result = await flight_api._get_flightaware_data('AA123', '2024-01-01')
            
            assert result is not None
            assert result.flight_number == 'AA123'
            assert result.airline == 'American Airlines'
            assert result.source == 'flightaware'
            assert result.delay_minutes == 15
    
    @pytest.mark.asyncio
    async def test_flightaware_api_no_key(self, flight_api):
        """Test FlightAware API without API key"""
        # Ensure no API key is set
        flight_api.config.flightaware_api_key = None
        
        result = await flight_api._get_flightaware_data('AA123', '2024-01-01')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_flightaware_api_error_handling(self, flight_api):
        """Test FlightAware API error handling"""
        flight_api.config.flightaware_api_key = 'test_key'
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock API error response
            mock_response = Mock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test API call with error
            result = await flight_api._get_flightaware_data('INVALID', '2024-01-01')
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_mock_flight_data_generation(self, flight_api):
        """Test mock flight data generation"""
        result = await flight_api._get_mock_flight_data('AA123', '2024-01-01')
        
        assert result is not None
        assert result.flight_number == 'AA123'
        assert result.source == 'mock'
        assert result.confidence == 0.8
        assert result.airline in ['AA', 'DL', 'UA', 'WN', 'BA', 'LH', 'JL', 'KE']
        assert result.origin != result.destination
    
    @pytest.mark.asyncio
    async def test_get_flight_status(self, flight_api):
        """Test get_flight_status method"""
        # Mock the API key to force fallback to mock data
        flight_api.config.flightaware_api_key = None
        
        result = await flight_api.get_flight_status('AA123')
        
        assert result is not None
        assert result.flight_number == 'AA123'
        assert result.source == 'mock'
    
    @pytest.mark.asyncio
    async def test_airport_statistics(self, flight_api):
        """Test airport statistics retrieval"""
        airport_data = await flight_api.get_airport_statistics('JFK')
        
        assert airport_data is not None
        assert isinstance(airport_data, AirportData)
        assert airport_data.airport_code == 'JFK'
        assert airport_data.source == 'mock'
        assert airport_data.total_flights > 0
    
    @pytest.mark.asyncio
    async def test_airline_performance(self, flight_api):
        """Test airline performance retrieval"""
        airline_data = await flight_api.get_airline_performance('AA')
        
        assert airline_data is not None
        assert isinstance(airline_data, AirlineData)
        assert airline_data.airline_code == 'AA'
        assert airline_data.source == 'mock'
        assert 0 <= airline_data.on_time_rate <= 1
        assert 0 <= airline_data.cancellation_rate <= 1
    
    @pytest.mark.asyncio
    async def test_delay_statistics(self, flight_api):
        """Test delay statistics retrieval"""
        delay_stats = await flight_api.get_delay_statistics('JFK-LAX', 'AA')
        
        assert delay_stats is not None
        assert 'route' in delay_stats
        assert 'airline' in delay_stats
        assert 'overall_delay_probability' in delay_stats
        assert 'average_delay_minutes' in delay_stats
        assert 'delay_patterns' in delay_stats
        assert 'seasonal_factors' in delay_stats
        assert 'weather_factors' in delay_stats
        assert 'historical_data' in delay_stats
        
        assert delay_stats['route'] == 'JFK-LAX'
        assert delay_stats['airline'] == 'AA'
        assert 0 <= delay_stats['overall_delay_probability'] <= 1
    
    @pytest.mark.asyncio
    async def test_flight_risk_analysis(self, flight_api):
        """Test flight risk analysis"""
        risk_analysis = await flight_api.analyze_flight_risk(
            flight_number='AA123',
            route='JFK-LAX',
            airline='AA',
            date='2024-01-01'
        )
        
        assert 'flight_number' in risk_analysis
        assert 'route' in risk_analysis
        assert 'airline' in risk_analysis
        assert 'date' in risk_analysis
        assert 'risk_score' in risk_analysis
        assert 'risk_factors' in risk_analysis
        assert 'recommendations' in risk_analysis
        assert 'timestamp' in risk_analysis
        
        assert risk_analysis['flight_number'] == 'AA123'
        assert risk_analysis['route'] == 'JFK-LAX'
        assert risk_analysis['airline'] == 'AA'
        assert 0 <= risk_analysis['risk_score'] <= 1
        assert isinstance(risk_analysis['recommendations'], list)
    
    def test_flight_risk_score_calculation(self, flight_api):
        """Test flight risk score calculation"""
        risk_factors = {
            'flight_data': {
                'status': 'delayed',
                'delay_minutes': 30
            },
            'airline_performance': {
                'on_time_rate': 0.75,
                'cancellation_rate': 0.05
            },
            'delay_statistics': {
                'overall_delay_probability': 0.3,
                'average_delay_minutes': 25
            }
        }
        
        risk_score = flight_api._calculate_flight_risk_score(risk_factors)
        
        assert 0 <= risk_score <= 1
        assert risk_score > 0.2  # Should be higher than base risk due to delay
    
    def test_flight_recommendations_generation(self, flight_api):
        """Test flight recommendations generation"""
        test_cases = [
            (0.2, ["Low risk - standard coverage recommended"]),
            (0.4, ["Moderate risk - consider additional coverage", "Monitor weather conditions"]),
            (0.6, ["High risk - premium coverage recommended", "Consider flexible booking options"]),
            (0.8, ["Very high risk - maximum coverage recommended", "Consider alternative travel dates", "Monitor airline and route performance"])
        ]
        
        for risk_score, expected_keywords in test_cases:
            recommendations = flight_api._generate_flight_recommendations(risk_score)
            
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            
            # Check that at least one expected keyword is in the recommendations
            recommendation_text = ' '.join(recommendations)
            for keyword in expected_keywords:
                if any(word in recommendation_text for word in keyword.split()):
                    break
            else:
                pytest.fail(f"No expected keywords found in recommendations for risk score {risk_score}")
    
    @pytest.mark.asyncio
    async def test_mock_delay_statistics(self, flight_api):
        """Test mock delay statistics generation"""
        delay_stats = await flight_api._get_mock_delay_statistics('JFK-LAX', 'AA')
        
        assert 'route' in delay_stats
        assert 'airline' in delay_stats
        assert 'delay_patterns' in delay_stats
        assert 'seasonal_factors' in delay_stats
        assert 'weather_factors' in delay_stats
        assert 'historical_data' in delay_stats
        
        # Check delay patterns structure
        delay_patterns = delay_stats['delay_patterns']
        assert 'morning' in delay_patterns
        assert 'afternoon' in delay_patterns
        assert 'evening' in delay_patterns
        assert 'night' in delay_patterns
        
        for pattern in delay_patterns.values():
            assert 'avg_delay' in pattern
            assert 'probability' in pattern
            assert 0 <= pattern['probability'] <= 1
        
        # Check seasonal factors
        seasonal_factors = delay_stats['seasonal_factors']
        assert 'winter' in seasonal_factors
        assert 'spring' in seasonal_factors
        assert 'summer' in seasonal_factors
        assert 'fall' in seasonal_factors
        
        # Check weather factors
        weather_factors = delay_stats['weather_factors']
        assert 'clear' in weather_factors
        assert 'stormy' in weather_factors
        assert weather_factors['clear'] < weather_factors['stormy']
    
    @pytest.mark.asyncio
    async def test_mock_airport_data(self, flight_api):
        """Test mock airport data generation"""
        airport_data = await flight_api._get_mock_airport_data('JFK')
        
        assert airport_data.airport_code == 'JFK'
        assert airport_data.airport_name == 'John F. Kennedy International Airport'
        assert airport_data.city == 'New York'
        assert airport_data.country == 'USA'
        assert airport_data.total_flights > 0
        assert airport_data.on_time_flights + airport_data.delayed_flights + airport_data.cancelled_flights == airport_data.total_flights
    
    @pytest.mark.asyncio
    async def test_mock_airline_data(self, flight_api):
        """Test mock airline data generation"""
        airline_data = await flight_api._get_mock_airline_data('AA')
        
        assert airline_data.airline_code == 'AA'
        assert airline_data.airline_name == 'American Airlines'
        assert airline_data.total_flights > 0
        assert 0 <= airline_data.on_time_rate <= 1
        assert 0 <= airline_data.cancellation_rate <= 1
        assert 0 <= airline_data.reliability_score <= 1
    
    def test_parse_flightaware_data(self, flight_api):
        """Test FlightAware data parsing"""
        flight_info = {
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
        }
        
        result = flight_api._parse_flightaware_data(flight_info)
        
        assert result.flight_number == 'AA123'
        assert result.airline == 'American Airlines'
        assert result.origin == 'JFK'
        assert result.destination == 'LAX'
        assert result.status == 'delayed'
        assert result.aircraft_type == 'B737'
        assert result.delay_minutes == 15
        assert result.source == 'flightaware'
        assert result.confidence == 0.95


class TestFlightConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_get_flight_info(self):
        """Test get_flight_info convenience function"""
        with patch('agents.data.flight.FlightAPI') as mock_flight_api:
            mock_api_instance = Mock()
            mock_flight_data = FlightData(
                flight_number='AA123',
                airline='American Airlines',
                origin='JFK',
                destination='LAX',
                scheduled_departure=datetime.now(),
                actual_departure=None,
                scheduled_arrival=datetime.now() + timedelta(hours=3),
                actual_arrival=None,
                status='scheduled',
                delay_minutes=0,
                aircraft_type='B737',
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_flight_status = AsyncMock(return_value=mock_flight_data)
            mock_flight_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_flight_info('AA123')
            
            assert result == mock_flight_data
            mock_api_instance.get_flight_status.assert_called_once_with('AA123', None)
    
    @pytest.mark.asyncio
    async def test_get_airport_info(self):
        """Test get_airport_info convenience function"""
        with patch('agents.data.flight.FlightAPI') as mock_flight_api:
            mock_api_instance = Mock()
            mock_airport_data = AirportData(
                airport_code='JFK',
                airport_name='John F. Kennedy International Airport',
                city='New York',
                country='USA',
                total_flights=500,
                on_time_flights=400,
                delayed_flights=80,
                cancelled_flights=20,
                average_delay=25.5,
                weather_condition='clear',
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_airport_statistics = AsyncMock(return_value=mock_airport_data)
            mock_flight_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_airport_info('JFK')
            
            assert result == mock_airport_data
            mock_api_instance.get_airport_statistics.assert_called_once_with('JFK')
    
    @pytest.mark.asyncio
    async def test_get_airline_info(self):
        """Test get_airline_info convenience function"""
        with patch('agents.data.flight.FlightAPI') as mock_flight_api:
            mock_api_instance = Mock()
            mock_airline_data = AirlineData(
                airline_code='AA',
                airline_name='American Airlines',
                total_flights=1000,
                on_time_rate=0.85,
                average_delay=20.0,
                cancellation_rate=0.02,
                reliability_score=0.84,
                timestamp=datetime.now(),
                source='mock'
            )
            mock_api_instance.get_airline_performance = AsyncMock(return_value=mock_airline_data)
            mock_flight_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_airline_info('AA')
            
            assert result == mock_airline_data
            mock_api_instance.get_airline_performance.assert_called_once_with('AA')
    
    @pytest.mark.asyncio
    async def test_get_flight_risk_analysis(self):
        """Test get_flight_risk_analysis convenience function"""
        with patch('agents.data.flight.FlightAPI') as mock_flight_api:
            mock_api_instance = Mock()
            mock_risk_analysis = {
                'flight_number': 'AA123',
                'route': 'JFK-LAX',
                'airline': 'AA',
                'date': '2024-01-01',
                'risk_score': 0.3,
                'risk_factors': {},
                'recommendations': ['Low risk - standard coverage recommended'],
                'timestamp': datetime.now().isoformat()
            }
            mock_api_instance.analyze_flight_risk = AsyncMock(return_value=mock_risk_analysis)
            mock_flight_api.return_value.__aenter__.return_value = mock_api_instance
            
            result = await get_flight_risk_analysis('AA123', 'JFK-LAX', 'AA', '2024-01-01')
            
            assert result == mock_risk_analysis
            mock_api_instance.analyze_flight_risk.assert_called_once_with('AA123', 'JFK-LAX', 'AA', '2024-01-01')


if __name__ == '__main__':
    pytest.main([__file__])
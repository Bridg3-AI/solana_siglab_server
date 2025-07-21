"""Integration tests for external data API modules"""
import pytest
import asyncio
from unittest.mock import patch, Mock
from datetime import datetime

from agents.data.weather import WeatherAPI, get_weather_data, get_weather_risk_analysis
from agents.data.flight import FlightAPI, get_flight_info, get_flight_risk_analysis
from agents.data.crypto import CryptoAPI, get_crypto_data, get_crypto_risk_analysis


class TestAPIIntegration:
    """Integration tests for all API modules"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_weather_api_integration(self):
        """Test weather API integration"""
        async with WeatherAPI() as weather_api:
            # Test current weather
            weather_data = await weather_api.get_current_weather('Tokyo')
            assert weather_data is not None
            assert weather_data.location == 'Tokyo'
            assert weather_data.source == 'mock'  # No API key configured
            
            # Test forecast
            forecast = await weather_api.get_weather_forecast('Tokyo', 3)
            assert len(forecast) == 3
            assert all(f.location == 'Tokyo' for f in forecast)
            
            # Test risk analysis
            risk_analysis = await weather_api.analyze_weather_risk('Tokyo', 'general')
            assert risk_analysis['location'] == 'Tokyo'
            assert 'risk_score' in risk_analysis
            assert 0 <= risk_analysis['risk_score'] <= 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flight_api_integration(self):
        """Test flight API integration"""
        async with FlightAPI() as flight_api:
            # Test flight status
            flight_data = await flight_api.get_flight_status('AA123')
            assert flight_data is not None
            assert flight_data.flight_number == 'AA123'
            assert flight_data.source == 'mock'  # No API key configured
            
            # Test airport statistics
            airport_data = await flight_api.get_airport_statistics('JFK')
            assert airport_data is not None
            assert airport_data.airport_code == 'JFK'
            
            # Test airline performance
            airline_data = await flight_api.get_airline_performance('AA')
            assert airline_data is not None
            assert airline_data.airline_code == 'AA'
            
            # Test risk analysis
            risk_analysis = await flight_api.analyze_flight_risk('AA123', 'JFK-LAX', 'AA')
            assert risk_analysis['flight_number'] == 'AA123'
            assert 'risk_score' in risk_analysis
            assert 0 <= risk_analysis['risk_score'] <= 1
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_crypto_api_integration(self):
        """Test crypto API integration"""
        async with CryptoAPI() as crypto_api:
            # Test crypto price
            crypto_data = await crypto_api.get_crypto_price('BTC')
            assert crypto_data is not None
            assert crypto_data.symbol == 'BTC'
            assert crypto_data.source == 'mock'  # No API key configured
            
            # Test Solana ecosystem
            solana_data = await crypto_api.get_solana_ecosystem_data()
            assert solana_data is not None
            assert 'sol' in solana_data
            assert 'spl_tokens' in solana_data
            assert 'network_stats' in solana_data
            
            # Test exchange rate
            exchange_data = await crypto_api.get_exchange_rate('USD', 'EUR')
            assert exchange_data is not None
            assert exchange_data.base_currency == 'USD'
            assert exchange_data.target_currency == 'EUR'
            
            # Test risk analysis
            risk_analysis = await crypto_api.analyze_crypto_risk(['BTC', 'ETH'])
            assert risk_analysis['symbols'] == ['BTC', 'ETH']
            assert 'individual_risks' in risk_analysis
            assert 'portfolio_risk' in risk_analysis
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_convenience_functions_integration(self):
        """Test convenience functions integration"""
        # Test weather convenience functions
        weather_data = await get_weather_data('Tokyo')
        assert weather_data is not None
        assert weather_data.location == 'Tokyo'
        
        weather_risk = await get_weather_risk_analysis('Tokyo', 'general')
        assert weather_risk['location'] == 'Tokyo'
        
        # Test flight convenience functions
        flight_data = await get_flight_info('AA123')
        assert flight_data is not None
        assert flight_data.flight_number == 'AA123'
        
        flight_risk = await get_flight_risk_analysis('AA123')
        assert flight_risk['flight_number'] == 'AA123'
        
        # Test crypto convenience functions
        crypto_data = await get_crypto_data('BTC')
        assert crypto_data is not None
        assert crypto_data.symbol == 'BTC'
        
        crypto_risk = await get_crypto_risk_analysis(['BTC', 'ETH'])
        assert crypto_risk['symbols'] == ['BTC', 'ETH']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cross_module_data_consistency(self):
        """Test data consistency across modules"""
        # Test that all modules handle similar data types consistently
        timestamp = datetime.now()
        
        # Weather data
        weather_data = await get_weather_data('Tokyo')
        assert weather_data.timestamp.date() == timestamp.date()
        
        # Flight data
        flight_data = await get_flight_info('AA123')
        assert flight_data.timestamp.date() == timestamp.date()
        
        # Crypto data
        crypto_data = await get_crypto_data('BTC')
        assert crypto_data.timestamp.date() == timestamp.date()
        
        # All should have similar confidence ranges
        assert 0.5 <= weather_data.confidence <= 1.0
        assert 0.5 <= flight_data.confidence <= 1.0
        assert 0.5 <= crypto_data.confidence <= 1.0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_consistency(self):
        """Test that all modules handle errors consistently"""
        # Test with invalid inputs
        weather_data = await get_weather_data('')
        assert weather_data is not None  # Mock data should still be returned
        
        flight_data = await get_flight_info('')
        assert flight_data is not None  # Mock data should still be returned
        
        crypto_data = await get_crypto_data('')
        assert crypto_data is not None  # Mock data should still be returned
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_consistency(self):
        """Test caching behavior across modules"""
        # Test weather caching
        async with WeatherAPI() as weather_api:
            weather_api.config.enable_cache = True
            weather_api.config.cache_ttl = 300
            
            # First call should fetch data
            data1 = await weather_api.get_current_weather('Tokyo')
            # Second call should use cache
            data2 = await weather_api.get_current_weather('Tokyo')
            
            assert data1.location == data2.location
            assert data1.timestamp == data2.timestamp
        
        # Test flight caching
        async with FlightAPI() as flight_api:
            flight_api.config.enable_cache = True
            flight_api.config.cache_ttl = 300
            
            # First call should fetch data
            data1 = await flight_api.get_flight_status('AA123')
            # Second call should use cache
            data2 = await flight_api.get_flight_status('AA123')
            
            assert data1.flight_number == data2.flight_number
            assert data1.timestamp == data2.timestamp
        
        # Test crypto caching
        async with CryptoAPI() as crypto_api:
            crypto_api.config.enable_cache = True
            crypto_api.config.cache_ttl = 300
            
            # First call should fetch data
            data1 = await crypto_api.get_crypto_price('BTC')
            # Second call should use cache
            data2 = await crypto_api.get_crypto_price('BTC')
            
            assert data1.symbol == data2.symbol
            assert data1.timestamp == data2.timestamp
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_parallel_api_calls(self):
        """Test parallel API calls across modules"""
        # Test that multiple API calls can run concurrently
        tasks = [
            get_weather_data('Tokyo'),
            get_flight_info('AA123'),
            get_crypto_data('BTC'),
            get_weather_risk_analysis('Tokyo', 'general'),
            get_flight_risk_analysis('AA123'),
            get_crypto_risk_analysis(['BTC'])
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        weather_data, flight_data, crypto_data, weather_risk, flight_risk, crypto_risk = results
        
        assert weather_data.location == 'Tokyo'
        assert flight_data.flight_number == 'AA123'
        assert crypto_data.symbol == 'BTC'
        assert weather_risk['location'] == 'Tokyo'
        assert flight_risk['flight_number'] == 'AA123'
        assert crypto_risk['symbols'] == ['BTC']
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_comprehensive_risk_analysis(self):
        """Test comprehensive risk analysis using all modules"""
        # Simulate a comprehensive insurance risk analysis
        location = 'Tokyo'
        flight_number = 'AA123'
        crypto_symbols = ['BTC', 'ETH', 'SOL']
        
        # Gather all risk data
        weather_risk = await get_weather_risk_analysis(location, 'general')
        flight_risk = await get_flight_risk_analysis(flight_number)
        crypto_risk = await get_crypto_risk_analysis(crypto_symbols)
        
        # Verify comprehensive analysis
        assert weather_risk['location'] == location
        assert flight_risk['flight_number'] == flight_number
        assert crypto_risk['symbols'] == crypto_symbols
        
        # All should have risk scores
        assert 0 <= weather_risk['risk_score'] <= 1
        assert 0 <= flight_risk['risk_score'] <= 1
        assert len(crypto_risk['individual_risks']) == len(crypto_symbols)
        
        # All should have recommendations
        assert isinstance(weather_risk.get('confidence'), (int, float))
        assert isinstance(flight_risk['recommendations'], list)
        assert isinstance(crypto_risk['recommendations'], list)
        
        # Calculate overall risk score (simplified)
        overall_risk = (
            weather_risk['risk_score'] * 0.3 +
            flight_risk['risk_score'] * 0.3 +
            sum(crypto_risk['individual_risks'][symbol]['risk_score'] 
                for symbol in crypto_symbols) / len(crypto_symbols) * 0.4
        )
        
        assert 0 <= overall_risk <= 1


class TestAPIPerformance:
    """Performance tests for API modules"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_weather_api_performance(self):
        """Test weather API performance"""
        import time
        
        async with WeatherAPI() as weather_api:
            start_time = time.time()
            
            # Test multiple concurrent calls
            tasks = [
                weather_api.get_current_weather(f'City{i}') 
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete within reasonable time
            assert duration < 5.0  # 5 seconds max
            assert len(results) == 10
            assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_flight_api_performance(self):
        """Test flight API performance"""
        import time
        
        async with FlightAPI() as flight_api:
            start_time = time.time()
            
            # Test multiple concurrent calls
            tasks = [
                flight_api.get_flight_status(f'AA{i}') 
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete within reasonable time
            assert duration < 5.0  # 5 seconds max
            assert len(results) == 10
            assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_crypto_api_performance(self):
        """Test crypto API performance"""
        import time
        
        async with CryptoAPI() as crypto_api:
            start_time = time.time()
            
            # Test multiple concurrent calls
            symbols = ['BTC', 'ETH', 'SOL', 'USDC', 'USDT']
            tasks = [
                crypto_api.get_crypto_price(symbol) 
                for symbol in symbols
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete within reasonable time
            assert duration < 5.0  # 5 seconds max
            assert len(results) == len(symbols)
            assert all(r is not None for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
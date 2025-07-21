"""Flight data API integration module"""
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
class FlightData:
    """Flight information data structure"""
    flight_number: str
    airline: str
    origin: str
    destination: str
    scheduled_departure: datetime
    actual_departure: Optional[datetime]
    scheduled_arrival: datetime
    actual_arrival: Optional[datetime]
    status: str  # scheduled, delayed, cancelled, diverted, landed
    delay_minutes: int
    aircraft_type: str
    timestamp: datetime
    source: str
    confidence: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['scheduled_departure'] = self.scheduled_departure.isoformat()
        data['actual_departure'] = self.actual_departure.isoformat() if self.actual_departure else None
        data['scheduled_arrival'] = self.scheduled_arrival.isoformat()
        data['actual_arrival'] = self.actual_arrival.isoformat() if self.actual_arrival else None
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class AirportData:
    """Airport status and statistics"""
    airport_code: str
    airport_name: str
    city: str
    country: str
    total_flights: int
    on_time_flights: int
    delayed_flights: int
    cancelled_flights: int
    average_delay: float
    weather_condition: str
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class AirlineData:
    """Airline performance statistics"""
    airline_code: str
    airline_name: str
    total_flights: int
    on_time_rate: float
    average_delay: float
    cancellation_rate: float
    reliability_score: float
    timestamp: datetime
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class FlightAPI:
    """Flight data API integration class"""
    
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
    
    async def get_flight_status(self, flight_number: str, date: Optional[str] = None) -> Optional[FlightData]:
        """Get flight status for a specific flight"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        cache_key = f"flight_{flight_number}_{date}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return FlightData(**cached_data)
        
        # Try FlightAware API first
        flight_data = await self._get_flightaware_data(flight_number, date)
        
        if flight_data:
            await self._set_cached_data(cache_key, flight_data.to_dict())
            return flight_data
        
        # Fallback to mock data for development
        return await self._get_mock_flight_data(flight_number, date)
    
    async def _get_flightaware_data(self, flight_number: str, date: str) -> Optional[FlightData]:
        """Get flight data from FlightAware API"""
        if not self.config.flightaware_api_key:
            logger.warning("FlightAware API key not configured")
            return None
        
        try:
            url = f"https://aeroapi.flightaware.com/aeroapi/flights/{flight_number}"
            headers = {
                'x-apikey': self.config.flightaware_api_key,
                'Accept': 'application/json'
            }
            params = {
                'start': date,
                'end': date
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('flights'):
                        flight_info = data['flights'][0]  # Get first flight
                        return self._parse_flightaware_data(flight_info)
                else:
                    logger.error(f"FlightAware API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching FlightAware data: {e}")
            return None
    
    def _parse_flightaware_data(self, flight_info: Dict[str, Any]) -> FlightData:
        """Parse FlightAware API response"""
        scheduled_departure = datetime.fromisoformat(flight_info['scheduled_off'].replace('Z', '+00:00'))
        actual_departure = None
        if flight_info.get('actual_off'):
            actual_departure = datetime.fromisoformat(flight_info['actual_off'].replace('Z', '+00:00'))
        
        scheduled_arrival = datetime.fromisoformat(flight_info['scheduled_on'].replace('Z', '+00:00'))
        actual_arrival = None
        if flight_info.get('actual_on'):
            actual_arrival = datetime.fromisoformat(flight_info['actual_on'].replace('Z', '+00:00'))
        
        # Calculate delay
        delay_minutes = 0
        if actual_departure and scheduled_departure:
            delay_minutes = int((actual_departure - scheduled_departure).total_seconds() / 60)
        
        return FlightData(
            flight_number=flight_info['ident'],
            airline=flight_info.get('operator', 'Unknown'),
            origin=flight_info['origin']['code'],
            destination=flight_info['destination']['code'],
            scheduled_departure=scheduled_departure,
            actual_departure=actual_departure,
            scheduled_arrival=scheduled_arrival,
            actual_arrival=actual_arrival,
            status=flight_info.get('status', 'scheduled'),
            delay_minutes=delay_minutes,
            aircraft_type=flight_info.get('aircraft_type', 'Unknown'),
            timestamp=datetime.now(),
            source='flightaware',
            confidence=0.95
        )
    
    async def _get_mock_flight_data(self, flight_number: str, date: str) -> FlightData:
        """Generate mock flight data for development"""
        import random
        
        # Common airlines and routes
        airlines = ['AA', 'DL', 'UA', 'WN', 'BA', 'LH', 'JL', 'KE']
        airports = ['JFK', 'LAX', 'ORD', 'DFW', 'ATL', 'LHR', 'CDG', 'NRT', 'ICN']
        statuses = ['scheduled', 'delayed', 'on_time', 'cancelled']
        
        # Generate realistic flight data
        airline = random.choice(airlines)
        origin = random.choice(airports)
        destination = random.choice([a for a in airports if a != origin])
        
        scheduled_departure = datetime.now() + timedelta(hours=random.randint(1, 12))
        scheduled_arrival = scheduled_departure + timedelta(hours=random.randint(1, 8))
        
        status = random.choice(statuses)
        delay_minutes = 0
        actual_departure = None
        actual_arrival = None
        
        if status == 'delayed':
            delay_minutes = random.randint(15, 180)
            actual_departure = scheduled_departure + timedelta(minutes=delay_minutes)
            actual_arrival = scheduled_arrival + timedelta(minutes=delay_minutes)
        elif status == 'on_time':
            actual_departure = scheduled_departure
            actual_arrival = scheduled_arrival
        
        return FlightData(
            flight_number=flight_number,
            airline=airline,
            origin=origin,
            destination=destination,
            scheduled_departure=scheduled_departure,
            actual_departure=actual_departure,
            scheduled_arrival=scheduled_arrival,
            actual_arrival=actual_arrival,
            status=status,
            delay_minutes=delay_minutes,
            aircraft_type=random.choice(['B737', 'A320', 'B777', 'A350']),
            timestamp=datetime.now(),
            source='mock',
            confidence=0.8
        )
    
    async def get_airport_statistics(self, airport_code: str) -> Optional[AirportData]:
        """Get airport performance statistics"""
        cache_key = f"airport_{airport_code}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return AirportData(**cached_data)
        
        # Mock airport data for development
        airport_data = await self._get_mock_airport_data(airport_code)
        
        if airport_data:
            await self._set_cached_data(cache_key, airport_data.to_dict())
        
        return airport_data
    
    async def _get_mock_airport_data(self, airport_code: str) -> AirportData:
        """Generate mock airport statistics"""
        import random
        
        # Airport information
        airport_info = {
            'JFK': ('John F. Kennedy International Airport', 'New York', 'USA'),
            'LAX': ('Los Angeles International Airport', 'Los Angeles', 'USA'),
            'ORD': ('Chicago O\'Hare International Airport', 'Chicago', 'USA'),
            'LHR': ('London Heathrow Airport', 'London', 'UK'),
            'NRT': ('Narita International Airport', 'Tokyo', 'Japan'),
            'ICN': ('Incheon International Airport', 'Seoul', 'South Korea')
        }
        
        name, city, country = airport_info.get(airport_code, (f'{airport_code} Airport', 'Unknown', 'Unknown'))
        
        total_flights = random.randint(200, 1000)
        delayed_flights = random.randint(20, total_flights // 3)
        cancelled_flights = random.randint(5, total_flights // 10)
        on_time_flights = total_flights - delayed_flights - cancelled_flights
        
        return AirportData(
            airport_code=airport_code,
            airport_name=name,
            city=city,
            country=country,
            total_flights=total_flights,
            on_time_flights=on_time_flights,
            delayed_flights=delayed_flights,
            cancelled_flights=cancelled_flights,
            average_delay=random.uniform(15, 45),
            weather_condition=random.choice(['clear', 'cloudy', 'rainy', 'stormy']),
            timestamp=datetime.now(),
            source='mock'
        )
    
    async def get_airline_performance(self, airline_code: str) -> Optional[AirlineData]:
        """Get airline performance statistics"""
        cache_key = f"airline_{airline_code}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return AirlineData(**cached_data)
        
        # Mock airline data for development
        airline_data = await self._get_mock_airline_data(airline_code)
        
        if airline_data:
            await self._set_cached_data(cache_key, airline_data.to_dict())
        
        return airline_data
    
    async def _get_mock_airline_data(self, airline_code: str) -> AirlineData:
        """Generate mock airline performance data"""
        import random
        
        # Airline information
        airline_info = {
            'AA': 'American Airlines',
            'DL': 'Delta Air Lines',
            'UA': 'United Airlines',
            'WN': 'Southwest Airlines',
            'BA': 'British Airways',
            'LH': 'Lufthansa',
            'JL': 'Japan Airlines',
            'KE': 'Korean Air'
        }
        
        name = airline_info.get(airline_code, f'{airline_code} Airlines')
        
        total_flights = random.randint(1000, 5000)
        on_time_rate = random.uniform(0.75, 0.95)
        average_delay = random.uniform(10, 30)
        cancellation_rate = random.uniform(0.01, 0.05)
        reliability_score = on_time_rate * 0.7 + (1 - cancellation_rate) * 0.3
        
        return AirlineData(
            airline_code=airline_code,
            airline_name=name,
            total_flights=total_flights,
            on_time_rate=on_time_rate,
            average_delay=average_delay,
            cancellation_rate=cancellation_rate,
            reliability_score=reliability_score,
            timestamp=datetime.now(),
            source='mock'
        )
    
    async def get_delay_statistics(self, route: str = None, airline: str = None) -> Dict[str, Any]:
        """Get delay statistics for specific route or airline"""
        cache_key = f"delay_stats_{route}_{airline}"
        cached_data = await self._get_cached_data(cache_key)
        
        if cached_data:
            return cached_data
        
        # Mock delay statistics
        delay_stats = await self._get_mock_delay_statistics(route, airline)
        
        if delay_stats:
            await self._set_cached_data(cache_key, delay_stats)
        
        return delay_stats
    
    async def _get_mock_delay_statistics(self, route: str, airline: str) -> Dict[str, Any]:
        """Generate mock delay statistics"""
        import random
        
        # Generate realistic delay patterns
        delay_patterns = {
            'morning': {'avg_delay': 15, 'probability': 0.2},
            'afternoon': {'avg_delay': 25, 'probability': 0.3},
            'evening': {'avg_delay': 20, 'probability': 0.25},
            'night': {'avg_delay': 10, 'probability': 0.15}
        }
        
        seasonal_factors = {
            'winter': 1.3,
            'spring': 0.9,
            'summer': 1.1,
            'fall': 0.8
        }
        
        weather_factors = {
            'clear': 0.8,
            'cloudy': 1.0,
            'rainy': 1.4,
            'stormy': 2.0,
            'snowy': 1.8
        }
        
        return {
            'route': route,
            'airline': airline,
            'overall_delay_probability': random.uniform(0.15, 0.35),
            'average_delay_minutes': random.uniform(15, 45),
            'delay_patterns': delay_patterns,
            'seasonal_factors': seasonal_factors,
            'weather_factors': weather_factors,
            'historical_data': {
                'last_30_days': {
                    'total_flights': random.randint(500, 2000),
                    'delayed_flights': random.randint(100, 600),
                    'cancelled_flights': random.randint(10, 50),
                    'average_delay': random.uniform(20, 40)
                }
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def analyze_flight_risk(self, flight_number: str = None, route: str = None, 
                                 airline: str = None, date: str = None) -> Dict[str, Any]:
        """Analyze flight delay risk for insurance purposes"""
        risk_factors = {}
        
        if flight_number:
            flight_data = await self.get_flight_status(flight_number, date)
            if flight_data:
                risk_factors['flight_data'] = flight_data.to_dict()
        
        if route:
            delay_stats = await self.get_delay_statistics(route, airline)
            risk_factors['delay_statistics'] = delay_stats
        
        if airline:
            airline_data = await self.get_airline_performance(airline)
            if airline_data:
                risk_factors['airline_performance'] = airline_data.to_dict()
        
        # Calculate overall risk score
        risk_score = self._calculate_flight_risk_score(risk_factors)
        
        return {
            'flight_number': flight_number,
            'route': route,
            'airline': airline,
            'date': date,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': self._generate_flight_recommendations(risk_score),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_flight_risk_score(self, risk_factors: Dict[str, Any]) -> float:
        """Calculate overall flight risk score"""
        base_risk = 0.2  # Base 20% risk
        
        # Flight-specific factors
        if 'flight_data' in risk_factors:
            flight_data = risk_factors['flight_data']
            if flight_data['status'] == 'delayed':
                base_risk += 0.3
            elif flight_data['status'] == 'cancelled':
                base_risk += 0.5
        
        # Airline performance factors
        if 'airline_performance' in risk_factors:
            airline_data = risk_factors['airline_performance']
            on_time_rate = airline_data.get('on_time_rate', 0.8)
            base_risk += (1 - on_time_rate) * 0.5
        
        # Route delay statistics
        if 'delay_statistics' in risk_factors:
            delay_stats = risk_factors['delay_statistics']
            delay_prob = delay_stats.get('overall_delay_probability', 0.2)
            base_risk += delay_prob * 0.3
        
        return min(base_risk, 1.0)
    
    def _generate_flight_recommendations(self, risk_score: float) -> List[str]:
        """Generate recommendations based on risk score"""
        recommendations = []
        
        if risk_score < 0.3:
            recommendations.append("Low risk - standard coverage recommended")
        elif risk_score < 0.5:
            recommendations.append("Moderate risk - consider additional coverage")
            recommendations.append("Monitor weather conditions")
        elif risk_score < 0.7:
            recommendations.append("High risk - premium coverage recommended")
            recommendations.append("Consider flexible booking options")
        else:
            recommendations.append("Very high risk - maximum coverage recommended")
            recommendations.append("Consider alternative travel dates")
            recommendations.append("Monitor airline and route performance")
        
        return recommendations


# Convenience functions for direct use
async def get_flight_info(flight_number: str, date: str = None) -> Optional[FlightData]:
    """Get flight information"""
    async with FlightAPI() as flight_api:
        return await flight_api.get_flight_status(flight_number, date)

async def get_airport_info(airport_code: str) -> Optional[AirportData]:
    """Get airport statistics"""
    async with FlightAPI() as flight_api:
        return await flight_api.get_airport_statistics(airport_code)

async def get_airline_info(airline_code: str) -> Optional[AirlineData]:
    """Get airline performance data"""
    async with FlightAPI() as flight_api:
        return await flight_api.get_airline_performance(airline_code)

async def get_flight_risk_analysis(flight_number: str = None, route: str = None, 
                                 airline: str = None, date: str = None) -> Dict[str, Any]:
    """Get flight risk analysis for insurance purposes"""
    async with FlightAPI() as flight_api:
        return await flight_api.analyze_flight_risk(flight_number, route, airline, date)
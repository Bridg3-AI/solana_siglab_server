"""Data integration modules for external APIs"""

from .weather import WeatherAPI
from .flight import FlightAPI
from .crypto import CryptoAPI

__all__ = ["WeatherAPI", "FlightAPI", "CryptoAPI"]
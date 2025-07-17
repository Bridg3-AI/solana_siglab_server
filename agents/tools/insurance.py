"""Insurance-related tools for V0.1 MVP"""
import random
from typing import Dict, Any
from langchain_core.tools import tool


@tool
async def collect_event_data(event_type: str) -> Dict[str, Any]:
    """
    Collect historical event data for the given event type.
    
    V0.1 Implementation: Returns mock data for testing purposes.
    
    Args:
        event_type: Type of event (e.g., "typhoon", "flight_delay", "earthquake")
        
    Returns:
        Dictionary containing event data with historical statistics
    """
    # Mock data for different event types
    mock_data = {
        "typhoon": {
            "event_type": "typhoon",
            "historical_frequency": 0.15,  # 15% chance per year
            "average_damage": 150000,  # USD
            "affected_regions": ["Tokyo", "Osaka", "Kyoto"],
            "season": "summer",
            "data_source": "JMA_historical_data_mock"
        },
        "flight_delay": {
            "event_type": "flight_delay",
            "historical_frequency": 0.25,  # 25% chance for 2+ hour delays
            "average_delay": 3.5,  # hours
            "affected_airports": ["NRT", "HND", "KIX"],
            "peak_season": "summer",
            "data_source": "aviation_api_mock"
        },
        "earthquake": {
            "event_type": "earthquake",
            "historical_frequency": 0.08,  # 8% chance for major quakes
            "average_magnitude": 6.2,
            "affected_regions": ["Kanto", "Kansai", "Kyushu"],
            "depth": "shallow",
            "data_source": "usgs_mock"
        }
    }
    
    # Return mock data with some randomization
    base_data = mock_data.get(event_type, {
        "event_type": event_type,
        "historical_frequency": random.uniform(0.05, 0.30),
        "data_source": "generic_mock"
    })
    
    # Add some random variation to make it more realistic
    if "historical_frequency" in base_data:
        base_data["historical_frequency"] *= random.uniform(0.8, 1.2)
    
    base_data["timestamp"] = "2024-07-17T10:30:00Z"
    base_data["confidence_level"] = random.uniform(0.85, 0.95)
    
    return base_data


@tool
async def calculate_loss_ratio(event_data: Dict[str, Any]) -> float:
    """
    Calculate loss ratio based on event data.
    
    V0.1 Implementation: Simple calculation for testing purposes.
    
    Args:
        event_data: Dictionary containing event statistics
        
    Returns:
        Loss ratio as a float between 0.0 and 1.0
    """
    if not event_data:
        return 0.0
    
    # Basic loss ratio calculation based on historical frequency
    frequency = event_data.get("historical_frequency", 0.1)
    
    # Adjust based on event type
    event_type = event_data.get("event_type", "")
    
    multipliers = {
        "typhoon": 1.2,
        "earthquake": 1.5,
        "flight_delay": 0.8,
        "flood": 1.3,
        "drought": 1.1
    }
    
    multiplier = multipliers.get(event_type, 1.0)
    
    # Calculate base loss ratio
    base_ratio = frequency * multiplier
    
    # Add confidence adjustment
    confidence = event_data.get("confidence_level", 0.9)
    adjusted_ratio = base_ratio * confidence
    
    # Ensure ratio is within reasonable bounds
    loss_ratio = min(max(adjusted_ratio, 0.0), 0.95)
    
    return round(loss_ratio, 4)
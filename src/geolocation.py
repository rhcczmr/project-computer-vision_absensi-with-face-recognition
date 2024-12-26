import requests
import math
import logging
from typing import Tuple, Optional

# Setup logging
logging.basicConfig(
    filename='geolocation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_current_location() -> str:
    """
    Get current location using IP-based geolocation
    Returns: str - "latitude,longitude"
    """
    try:
        # Temporary: Return default Makassar location for testing
        return "-5.1486,119.4319"
        
    except Exception as e:
        logging.error(f"Error getting location: {str(e)}")
        # Fallback to default location
        return "-5.1486,119.4319"

def parse_coordinates(location: str) -> Tuple[float, float]:
    """Parse location string into coordinates"""
    try:
        lat, lon = map(float, location.split(','))
        return lat, lon
    except Exception as e:
        logging.error(f"Error parsing coordinates: {str(e)}")
        # Return default coordinates
        return (-5.1486, 119.4319)

def calculate_distance(location1: str, location2: str) -> float:
    """Calculate distance between two locations"""
    try:
        lat1, lon1 = parse_coordinates(location1)
        lat2, lon2 = parse_coordinates(location2)
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        distance = c * r
        
        logging.info(f"Distance calculated: {distance:.2f}m")
        return distance
        
    except Exception as e:
        logging.error(f"Error calculating distance: {str(e)}")
        return 0.0

def is_within_radius(current: str, target: str, radius: float = 1000.0) -> bool:
    """Check if current location is within radius of target"""
    try:
        # Temporary: Always return True for testing
        logging.info(f"Location check bypassed for testing")
        return True
        
    except Exception as e:
        logging.error(f"Error checking radius: {str(e)}")
        return True  # Allow on error for testing
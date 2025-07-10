import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Configuration class for Fuel2go application"""
    
    def __init__(self):
        self.google_maps_api_key: Optional[str] = os.getenv('GOOGLE_MAPS_API_KEY')
        self.google_routes_api_key: Optional[str] = os.getenv('GOOGLE_ROUTES_API_KEY')
        self.google_places_api_key: Optional[str] = os.getenv('GOOGLE_PLACES_API_KEY') or self.google_routes_api_key

        # API endpoints
        self.routes_api_base_url = "https://routes.googleapis.com/directions/v2"
        self.compute_routes_endpoint = f"{self.routes_api_base_url}:computeRoutes"
        self.places_api_base_url = "https://places.googleapis.com/v1"
        self.nearby_search_endpoint = f"{self.places_api_base_url}/places:searchNearby"
        self.place_details_endpoint = f"{self.places_api_base_url}/places"

        # Default request settings
        self.default_travel_mode = "DRIVE"
        self.default_polyline_quality = "OVERVIEW"
        self.default_routing_preference = "TRAFFIC_AWARE"
        
        # Rate limiting
        self.requests_per_minute = 60
        self.requests_per_day = 25000
        
    def validate_api_keys(self) -> bool:
        """Validate that required API keys are present"""
        if not self.google_routes_api_key:
            raise ValueError("GOOGLE_ROUTES_API_KEY is required in .env file")
        if not self.google_places_api_key:
            # If places key is still missing after fallback, then raise error.
            raise ValueError("GOOGLE_PLACES_API_KEY or GOOGLE_ROUTES_API_KEY must be set in the .env file.")
        return True
    
    def get_headers(self) -> dict:
        """Get standard headers for API requests"""
        return {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.google_routes_api_key,
            'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.legs,routes.polyline.encodedPolyline'
        }

# Global config instance
config = Config()
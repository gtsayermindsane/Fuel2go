import os
from dotenv import load_dotenv
from typing import Optional

# Streamlit imports (sadece gerekli olduğunda)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

load_dotenv()

class Config:
    """Configuration class for Fuel2go application"""
    
    def __init__(self):
        # Önce env dosyasından oku, yoksa Streamlit secrets'den oku
        self.google_maps_api_key: Optional[str] = self._get_config_value('GOOGLE_MAPS_API_KEY')
        self.google_routes_api_key: Optional[str] = self._get_config_value('GOOGLE_ROUTES_API_KEY')
        self.google_places_api_key: Optional[str] = self._get_config_value('GOOGLE_PLACES_API_KEY') or self.google_routes_api_key

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
    
    def _get_config_value(self, key: str) -> Optional[str]:
        """
        Önce environment variable'dan oku, yoksa Streamlit secrets'den oku.
        
        Args:
            key (str): Config anahtarı
            
        Returns:
            Optional[str]: Config değeri veya None
        """
        # Önce environment variable'dan dene
        value = os.getenv(key)
        
        if value:
            return value
            
        # Eğer Streamlit mevcutsa ve secrets var ise oradan dene
        if STREAMLIT_AVAILABLE:
            try:
                if hasattr(st, 'secrets') and key in st.secrets:
                    return st.secrets[key]
            except Exception:
                # Secrets erişimi başarısız olursa geç
                pass
        
        return None
        
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
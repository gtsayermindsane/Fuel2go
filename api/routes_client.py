import requests
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
import logging

from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleRoutesClient:
    """Google Routes API client for route calculation and optimization"""
    
    def __init__(self):
        self.config = config
        self.config.validate_api_keys()
        self.session = requests.Session()
        self.session.headers.update(self.config.get_headers())
        
        # Rate limiting
        self.last_request_time = 0
        self.min_interval = 60 / self.config.requests_per_minute  # seconds between requests
        
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def compute_route(self, 
                     origin: Dict[str, float], 
                     destination: Dict[str, float],
                     travel_mode: str = "DRIVE",
                     routing_preference: str = "TRAFFIC_AWARE",
                     departure_time: Optional[str] = None,
                     waypoints: Optional[List[Dict[str, float]]] = None,
                     compute_alternative_routes: bool = False) -> Dict[str, Any]:
        """
        Compute route between origin and destination
        
        Args:
            origin: {"latitude": float, "longitude": float}
            destination: {"latitude": float, "longitude": float}
            travel_mode: "DRIVE", "WALK", "BICYCLE", "TRANSIT"
            routing_preference: "TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL", "FUEL_EFFICIENT"
            departure_time: ISO 8601 format string (e.g., "2025-07-10T15:00:00Z")
            waypoints: List of waypoint coordinates
            compute_alternative_routes: Whether to compute alternative routes
            
        Returns:
            Dictionary containing route information
        """
        self._rate_limit()
        
        # Prepare request body
        request_body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin["latitude"],
                        "longitude": origin["longitude"]
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination["latitude"],
                        "longitude": destination["longitude"]
                    }
                }
            },
            "travelMode": travel_mode,
            "routingPreference": routing_preference,
            "polylineQuality": "OVERVIEW",
            "computeAlternativeRoutes": compute_alternative_routes
        }
        
        # Add departure time if provided
        if departure_time:
            request_body["departureTime"] = departure_time
        elif routing_preference in ["TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL"]:
            # Use current time for traffic-aware routing, slightly in the future
            future_time = datetime.now(timezone.utc) + timedelta(seconds=10)
            request_body["departureTime"] = future_time.isoformat()
        
        # Add waypoints if provided
        if waypoints:
            request_body["intermediates"] = []
            for waypoint in waypoints:
                request_body["intermediates"].append({
                    "location": {
                        "latLng": {
                            "latitude": waypoint["latitude"],
                            "longitude": waypoint["longitude"]
                        }
                    }
                })
        
        try:
            logger.info(f"Making request to Google Routes API: {self.config.compute_routes_endpoint}")
            response = self.session.post(
                self.config.compute_routes_endpoint,
                json=request_body,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error making request to Google Routes API: {e}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Google Routes API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            raise
    
    def get_route_details(self, route_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format route details from API response
        
        Args:
            route_response: Raw response from compute_route
            
        Returns:
            Formatted route details
        """
        if "routes" not in route_response or not route_response["routes"]:
            raise ValueError("No routes found in response")
        
        route = route_response["routes"][0]  # Take first route
        
        # Extract basic route information
        route_details = {
            "distance_meters": route.get("distanceMeters", 0),
            "distance_km": route.get("distanceMeters", 0) / 1000,
            "duration_seconds": route.get("duration", "0s").replace("s", ""),
            "duration_minutes": int(route.get("duration", "0s").replace("s", "")) / 60,
            "polyline": route.get("polyline", {}).get("encodedPolyline", ""),
            "legs": []
        }
        
        # Extract leg information
        if "legs" in route:
            for leg in route["legs"]:
                leg_info = {
                    "distance_meters": leg.get("distanceMeters", 0),
                    "distance_km": leg.get("distanceMeters", 0) / 1000,
                    "duration_seconds": leg.get("duration", "0s").replace("s", ""),
                    "duration_minutes": int(leg.get("duration", "0s").replace("s", "")) / 60,
                    "start_location": leg.get("startLocation", {}),
                    "end_location": leg.get("endLocation", {}),
                    "steps": len(leg.get("steps", []))
                }
                route_details["legs"].append(leg_info)
        
        return route_details
    
    def calculate_carbon_emission(self, distance_km: float, 
                                vehicle_type: str = "gasoline_car") -> Dict[str, float]:
        """
        Calculate carbon emission based on distance and vehicle type
        
        Args:
            distance_km: Distance in kilometers
            vehicle_type: Type of vehicle (gasoline_car, diesel_car, electric_car)
            
        Returns:
            Carbon emission data
        """
        # Emission factors (kg CO2 per km) - based on average values
        emission_factors = {
            "gasoline_car": 0.192,    # kg CO2/km
            "diesel_car": 0.171,      # kg CO2/km
            "electric_car": 0.067,    # kg CO2/km (considering electricity mix)
            "hybrid_car": 0.104       # kg CO2/km
        }
        
        emission_factor = emission_factors.get(vehicle_type, emission_factors["gasoline_car"])
        total_emission = distance_km * emission_factor
        
        return {
            "distance_km": distance_km,
            "vehicle_type": vehicle_type,
            "emission_factor_kg_per_km": emission_factor,
            "total_emission_kg": total_emission,
            "total_emission_tons": total_emission / 1000
        }
    
    def get_traffic_conditions(self, route_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract traffic condition information from route response
        
        Args:
            route_response: Raw response from compute_route
            
        Returns:
            Traffic condition data
        """
        if "routes" not in route_response or not route_response["routes"]:
            return {"traffic_conditions": "no_data"}
        
        route = route_response["routes"][0]
        
        # Calculate traffic delay by comparing duration in traffic vs without
        duration_in_traffic = int(route.get("duration", "0s").replace("s", ""))
        
        # This is a simplified approach - in real implementation, you'd compare
        # with duration without traffic if available
        traffic_info = {
            "duration_in_traffic_seconds": duration_in_traffic,
            "duration_in_traffic_minutes": duration_in_traffic / 60,
            "has_traffic_data": "duration" in route,
            "route_computed_at": datetime.now(timezone.utc).isoformat()
        }
        
        return traffic_info
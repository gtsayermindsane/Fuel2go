#!/usr/bin/env python3
"""
Google Places API client for finding places of interest.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
import logging

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GooglePlacesClient:
    """
    Client for Google Places API to find details about locations.
    """
    
    def __init__(self):
        self.config = config
        self.config.validate_api_keys()
        self.session = requests.Session()
        
    def get_headers(self) -> dict:
        """Get standard headers for Places API requests"""
        return {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.config.google_places_api_key,
            'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.id,places.types,places.websiteUri,places.businessStatus'
        }

    def search_nearby(self, 
                      latitude: float, 
                      longitude: float, 
                      radius_meters: int, 
                      place_types: List[str]) -> List[Dict[str, Any]]:
        """
        Search for places of a specific type near a location.
        """
        request_body = {
            "includedTypes": place_types,
            "maxResultCount": 10, # Max allowed by API is 20
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius_meters
                }
            }
        }
        
        try:
            logger.info(f"Searching for {place_types} near ({latitude}, {longitude})")
            response = self.session.post(
                self.config.nearby_search_endpoint,
                json=request_body,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('places', [])
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during nearby search: {e}")
            logger.error(f"Response content: {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during nearby search: {e}")
            return []

    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific place.
        """
        if not place_id.startswith('places/'):
             place_id_url = f"places/{place_id}"
        else:
            place_id_url = place_id
            
        full_url = f"{self.config.place_details_endpoint}/{place_id_url}"
        
        try:
            logger.info(f"Fetching details for place: {place_id}")
            response = self.session.get(
                full_url,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error fetching place details: {e}")
            logger.error(f"Response content: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching place details: {e}")
            return None 
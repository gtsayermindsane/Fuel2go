#!/usr/bin/env python3
"""
Google Geocoding API Client
Şehir isimlerini koordinatlara çevirmek için geocoding servisi
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeocodingClient:
    """
    Google Geocoding API ile şehir isimlerini koordinatlara dönüştürme işlemleri.
    
    Bu sınıf, kullanıcıların şehir adı girerek koordinat elde etmesini sağlar.
    """
    
    def __init__(self):
        """
        GeocodingClient sınıfını başlatır.
        """
        self.config = config
        self.config.validate_api_keys()
        self.session = requests.Session()
        
        # Geocoding API endpoint
        self.geocoding_endpoint = "https://maps.googleapis.com/maps/api/geocode/json"
        
    def get_city_coordinates(self, city_name: str, country: str = "Turkey") -> Optional[Dict[str, Any]]:
        """
        Şehir adından koordinatları bulur.
        
        Args:
            city_name (str): Şehir adı (örn: "Istanbul", "Ankara")
            country (str): Ülke adı (varsayılan: "Turkey")
            
        Returns:
            Optional[Dict[str, Any]]: Şehir bilgileri ve koordinatları, bulunamazsa None
        """
        # Arama terimi oluştur
        query = f"{city_name}, {country}"
        
        params = {
            'address': query,
            'key': self.config.google_routes_api_key,  # Routes API anahtarı kullanılıyor
            'language': 'tr',
            'region': 'tr'
        }
        
        try:
            logger.info(f"Geocoding search for: {query}")
            response = self.session.get(self.geocoding_endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                result = data['results'][0]  # İlk sonucu al
                
                location = result['geometry']['location']
                formatted_address = result['formatted_address']
                
                # Şehir komponenti bul
                city_component = None
                for component in result.get('address_components', []):
                    if 'locality' in component.get('types', []) or 'administrative_area_level_1' in component.get('types', []):
                        city_component = component['long_name']
                        break
                
                return {
                    'city_name': city_component or city_name,
                    'formatted_address': formatted_address,
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'country': country,
                    'search_query': query
                }
            else:
                logger.warning(f"No results found for: {query}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during geocoding request: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            return None
    
    def search_cities_in_country(self, country: str = "Turkey") -> List[Dict[str, Any]]:
        """
        Bir ülkedeki büyük şehirlerin listesini döndürür.
        
        Args:
            country (str): Ülke adı
            
        Returns:
            List[Dict[str, Any]]: Şehir listesi ve koordinatları
        """
        # Türkiye'nin büyük şehirleri
        turkish_cities = [
            "Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", 
            "Konya", "Gaziantep", "Mersin", "Diyarbakır", "Kayseri", "Eskişehir",
            "Urfa", "Malatya", "Erzurum", "Van", "Batman", "Elazığ",
            "Sivas", "Manisa", "Tarsus", "Trabzon", "Kahramanmaraş", "Ordu"
        ]
        
        cities_with_coords = []
        
        for city in turkish_cities:
            coords = self.get_city_coordinates(city, country)
            if coords:
                cities_with_coords.append(coords)
                
        logger.info(f"Found coordinates for {len(cities_with_coords)} cities in {country}")
        return cities_with_coords
    
    def get_predefined_turkish_cities(self) -> List[Dict[str, Any]]:
        """
        Önceden tanımlı Türkiye şehirleri listesi döndürür.
        API çağrısı yapmadan hızlı erişim için.
        
        Returns:
            List[Dict[str, Any]]: Türkiye'nin büyük şehirleri ve koordinatları
        """
        return [
            {"city_name": "Istanbul", "latitude": 41.0082, "longitude": 28.9784, "formatted_address": "İstanbul, Türkiye"},
            {"city_name": "Ankara", "latitude": 39.9334, "longitude": 32.8597, "formatted_address": "Ankara, Türkiye"},
            {"city_name": "Izmir", "latitude": 38.4192, "longitude": 27.1287, "formatted_address": "İzmir, Türkiye"},
            {"city_name": "Bursa", "latitude": 40.1826, "longitude": 29.0665, "formatted_address": "Bursa, Türkiye"},
            {"city_name": "Antalya", "latitude": 36.8969, "longitude": 30.7133, "formatted_address": "Antalya, Türkiye"},
            {"city_name": "Adana", "latitude": 37.0000, "longitude": 35.3213, "formatted_address": "Adana, Türkiye"},
            {"city_name": "Konya", "latitude": 37.8713, "longitude": 32.4846, "formatted_address": "Konya, Türkiye"},
            {"city_name": "Gaziantep", "latitude": 37.0662, "longitude": 37.3833, "formatted_address": "Gaziantep, Türkiye"},
            {"city_name": "Mersin", "latitude": 36.8000, "longitude": 34.6333, "formatted_address": "Mersin, Türkiye"},
            {"city_name": "Diyarbakır", "latitude": 37.9144, "longitude": 40.2306, "formatted_address": "Diyarbakır, Türkiye"},
            {"city_name": "Kayseri", "latitude": 38.7312, "longitude": 35.4787, "formatted_address": "Kayseri, Türkiye"},
            {"city_name": "Eskişehir", "latitude": 39.7667, "longitude": 30.5256, "formatted_address": "Eskişehir, Türkiye"},
            {"city_name": "Urfa", "latitude": 37.1674, "longitude": 38.7955, "formatted_address": "Şanlıurfa, Türkiye"},
            {"city_name": "Malatya", "latitude": 38.3552, "longitude": 38.3095, "formatted_address": "Malatya, Türkiye"},
            {"city_name": "Erzurum", "latitude": 39.9334, "longitude": 41.2767, "formatted_address": "Erzurum, Türkiye"},
            {"city_name": "Van", "latitude": 38.4891, "longitude": 43.4089, "formatted_address": "Van, Türkiye"},
            {"city_name": "Trabzon", "latitude": 41.0015, "longitude": 39.7178, "formatted_address": "Trabzon, Türkiye"},
            {"city_name": "Samsun", "latitude": 41.2867, "longitude": 36.3300, "formatted_address": "Samsun, Türkiye"},
            {"city_name": "Denizli", "latitude": 37.7765, "longitude": 29.0864, "formatted_address": "Denizli, Türkiye"},
            {"city_name": "Sakarya", "latitude": 40.6940, "longitude": 30.4358, "formatted_address": "Sakarya, Türkiye"}
        ]
    
    def find_city_by_name(self, city_name: str) -> Optional[Dict[str, Any]]:
        """
        Şehir adına göre önceden tanımlı listeden şehir bulur.
        
        Args:
            city_name (str): Aranacak şehir adı
            
        Returns:
            Optional[Dict[str, Any]]: Bulunan şehir bilgileri veya None
        """
        cities = self.get_predefined_turkish_cities()
        
        # Büyük/küçük harf duyarsız arama
        city_name_lower = city_name.lower()
        
        for city in cities:
            if city['city_name'].lower() == city_name_lower:
                return city
        
        # Bulunamazsa API ile ara
        return self.get_city_coordinates(city_name, "Turkey")
    
    def get_route_cities(self) -> List[Dict[str, Any]]:
        """
        Rota hesaplaması için popüler şehirler döndürür.
        
        Returns:
            List[Dict[str, Any]]: Popüler rota şehirleri
        """
        popular_cities = [
            {"city_name": "Istanbul", "latitude": 41.0082, "longitude": 28.9784},
            {"city_name": "Ankara", "latitude": 39.9334, "longitude": 32.8597},
            {"city_name": "Izmir", "latitude": 38.4192, "longitude": 27.1287},
            {"city_name": "Bursa", "latitude": 40.1826, "longitude": 29.0665},
            {"city_name": "Antalya", "latitude": 36.8969, "longitude": 30.7133},
            {"city_name": "Adana", "latitude": 37.0000, "longitude": 35.3213},
            {"city_name": "Trabzon", "latitude": 41.0015, "longitude": 39.7178},
            {"city_name": "Erzurum", "latitude": 39.9334, "longitude": 41.2767},
            {"city_name": "Gaziantep", "latitude": 37.0662, "longitude": 37.3833},
            {"city_name": "Samsun", "latitude": 41.2867, "longitude": 36.3300}
        ]
        
        return popular_cities
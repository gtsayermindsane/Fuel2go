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
    Google Places API ile etkileşim kurarak mekanları (örneğin, benzin istasyonları)
    bulmak için bir istemci sınıfı.
    
    Bu sınıf, yakındaki yerleri arama ve belirli bir yerin detaylarını getirme
    gibi işlemleri yönetir. Gerekli API anahtarını `config` modülünden alır.
    """
    
    def __init__(self):
        """
        GooglePlacesClient sınıfını başlatır.
        
        Yapılandırmayı yükler, API anahtarlarını doğrular ve bir `requests.Session`
        nesnesi oluşturur.
        """
        self.config = config
        self.config.validate_api_keys()
        self.session = requests.Session()
        
    def get_headers(self) -> dict:
        """
        Places API istekleri için standart HTTP başlıklarını (headers) oluşturur.
        
        Bu başlıklar, API anahtarını ve yanıtta dönmesi istenen alanları (`FieldMask`)
        içerir. Bu sayede sadece ihtiyaç duyulan veriler istenerek API kullanımı
        optimize edilir.

        Returns:
            dict: API isteği için gerekli başlıkları içeren sözlük.
        """
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
        Belirtilen bir konuma yakın, belirli türdeki yerleri arar.

        Args:
            latitude (float): Aramanın yapılacağı merkez noktanın enlemi.
            longitude (float): Aramanın yapılacağı merkez noktanın boylamı.
            radius_meters (int): Arama yapılacak alanın yarıçapı (metre cinsinden).
            place_types (List[str]): Aranacak yer türlerinin listesi (örn: ["gas_station"]).

        Returns:
            List[Dict[str, Any]]: Bulunan yerlerin listesi. Her bir yer, API'den
                                  dönen ham verileri içeren bir sözlüktür. Hata
                                  durumunda boş bir liste döner.
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
        Belirli bir yerin detaylı bilgilerini getirir.

        Args:
            place_id (str): Detayları alınacak yerin kimliği (place ID).

        Returns:
            Optional[Dict[str, Any]]: İstenen yerin detaylarını içeren bir sözlük.
                                      Hata durumunda veya yer bulunamazsa None döner.
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

    def search_truck_friendly_places(self, 
                                   latitude: float, 
                                   longitude: float, 
                                   radius_meters: int = 50000,
                                   place_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Şoförlere yönelik yerleri arar (benzin istasyonları, truck stop'lar, dinlenme alanları).
        
        Args:
            latitude (float): Aramanın yapılacağı merkez noktanın enlemi.
            longitude (float): Aramanın yapılacağı merkez noktanın boylamı.
            radius_meters (int, optional): Arama yarıçapı. Varsayılan 50km.
            place_types (List[str], optional): Aranacak yer türleri. Varsayılan truck-friendly yerler.
        
        Returns:
            List[Dict[str, Any]]: Bulunan şoför dostu yerlerin listesi.
        """
        if place_types is None:
            place_types = ["truck_stop", "gas_station", "rest_stop"]
        
        logger.info(f"Searching for truck-friendly places: {place_types} near ({latitude}, {longitude})")
        
        request_body = {
            "includedTypes": place_types,
            "maxResultCount": 20,
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
            response = self.session.post(
                self.config.nearby_search_endpoint,
                json=request_body,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            logger.info(f"Found {len(places)} truck-friendly places")
            return places
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during truck-friendly search: {e}")
            logger.error(f"Response content: {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during truck-friendly search: {e}")
            return []

    def search_adblue_stations(self, 
                              latitude: float, 
                              longitude: float, 
                              radius_meters: int = 25000) -> List[Dict[str, Any]]:
        """
        AdBlue servisi sunan benzin istasyonlarını arar.
        
        Args:
            latitude (float): Aramanın yapılacağı merkez noktanın enlemi.
            longitude (float): Aramanın yapılacağı merkez noktanın boylamı.
            radius_meters (int, optional): Arama yarıçapı. Varsayılan 25km.
        
        Returns:
            List[Dict[str, Any]]: AdBlue servisi sunan istasyonların listesi.
        """
        logger.info(f"Searching for AdBlue stations near ({latitude}, {longitude})")
        
        # İlk olarak benzin istasyonlarını ara
        gas_stations = self.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            place_types=["gas_station"]
        )
        
        # AdBlue servisi sunan istasyonları filtrele (isimlere göre)
        adblue_indicators = [
            "adblue", "ad blue", "def", "diesel exhaust fluid",
            "truck", "kamyon", "ağır vasıta", "commercial"
        ]
        
        adblue_stations = []
        for station in gas_stations:
            display_name = station.get('displayName', {})
            name = display_name.get('text', '').lower() if display_name else ''
            
            # İsimde AdBlue göstergesi var mı kontrol et
            if any(indicator in name for indicator in adblue_indicators):
                adblue_stations.append(station)
            
            # Alternatif olarak, büyük benzin istasyonu markalarını ekle
            major_brands = ["shell", "bp", "total", "opet", "petrol ofisi", "lukoil"]
            if any(brand in name for brand in major_brands):
                adblue_stations.append(station)
        
        logger.info(f"Found {len(adblue_stations)} potential AdBlue stations")
        return adblue_stations

    def search_driver_amenities(self, 
                              latitude: float, 
                              longitude: float, 
                              radius_meters: int = 30000,
                              amenity_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Şoför ihtiyaçlarına yönelik tesisleri arar (restoran, motel, duş, vs.).
        
        Args:
            latitude (float): Aramanın yapılacağı merkez noktanın enlemi.
            longitude (float): Aramanın yapılacağı merkez noktanın boylamı.
            radius_meters (int, optional): Arama yarıçapı. Varsayılan 30km.
            amenity_types (List[str], optional): Aranacak tesis türleri.
        
        Returns:
            List[Dict[str, Any]]: Şoför tesislerinin listesi.
        """
        if amenity_types is None:
            amenity_types = ["restaurant", "lodging", "motel", "rv_park", "campground"]
        
        logger.info(f"Searching for driver amenities: {amenity_types} near ({latitude}, {longitude})")
        
        request_body = {
            "includedTypes": amenity_types,
            "maxResultCount": 20,
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
            response = self.session.post(
                self.config.nearby_search_endpoint,
                json=request_body,
                headers=self.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            places = data.get('places', [])
            logger.info(f"Found {len(places)} driver amenity places")
            return places
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during amenity search: {e}")
            logger.error(f"Response content: {e.response.text}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during amenity search: {e}")
            return []

    def search_24h_services(self, 
                           latitude: float, 
                           longitude: float, 
                           radius_meters: int = 50000) -> List[Dict[str, Any]]:
        """
        24 saat açık olan servisleri arar (benzin istasyonları, restoranlar).
        
        Args:
            latitude (float): Aramanın yapılacağı merkez noktanın enlemi.
            longitude (float): Aramanın yapılacağı merkez noktanın boylamı.
            radius_meters (int, optional): Arama yarıçapı. Varsayılan 50km.
        
        Returns:
            List[Dict[str, Any]]: 24 saat açık servislerin listesi.
        """
        logger.info(f"Searching for 24h services near ({latitude}, {longitude})")
        
        # 24 saat açık olabilecek yer türleri
        service_types = ["gas_station", "convenience_store", "restaurant"]
        
        all_services = []
        for service_type in service_types:
            places = self.search_nearby(
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
                place_types=[service_type]
            )
            
            # 24 saat açık olma potansiyeli olan yerleri filtrele
            for place in places:
                display_name = place.get('displayName', {})
                name = display_name.get('text', '').lower() if display_name else ''
                
                # 24 saat göstergeleri
                if any(indicator in name for indicator in ["24", "nonstop", "gece", "açık"]):
                    all_services.append(place)
                # Büyük zincirler genelde 24 saat açık
                elif any(chain in name for chain in ["shell", "bp", "mcdonalds", "burger king"]):
                    all_services.append(place)
        
        logger.info(f"Found {len(all_services)} potential 24h services")
        return all_services
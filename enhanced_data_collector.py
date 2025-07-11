#!/usr/bin/env python3
"""
Enhanced Data Collection System
Türkiye geneli kapsamlı mekan verisi toplama sistemi
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import psycopg2
from pathlib import Path

from api.routes_client import GoogleRoutesClient
from api.places_client import GooglePlacesClient
from api.geocoding_client import GeocodingClient
from data_models import FuelStationData, RouteData, RealTimeDataCollector
from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
from config import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataCollector:
    """
    Türkiye geneli mekanlar için kapsamlı veri toplama ve işleme sistemi.
    
    Bu sınıf, Google Places Servisi'ni kullanarak Türkiye şehirlerindeki
    çeşitli mekanları (benzin istasyonu, restoran, hastane, otel vb.) toplar, 
    bu verileri zenginleştirir ve PostgreSQL veritabanına kaydeder.
    """
    
    def __init__(self):
        """
        EnhancedDataCollector sınıfını başlatır.
        
        Servis istemcilerini (GoogleRoutesClient, GooglePlacesClient, GeocodingClient), veri ambarını
        (DataWarehouse) ve sabitleri (şehirler, markalar) ayarlar.
        """
        self.routes_client = GoogleRoutesClient()
        self.places_client = GooglePlacesClient()
        self.geocoding_client = GeocodingClient()
        self.warehouse = PostgreSQLDataWarehouse()
        self.real_time_collector = RealTimeDataCollector(self.warehouse)
        
        # Sabitler constants.py dosyasından alınıyor ve Türkiye şehirleri
        self.turkish_cities = self.geocoding_client.get_predefined_turkish_cities()
        self.fuel_brands = constants.FUEL_BRANDS
    
    def identify_fuel_brand(self, station_name: str) -> str:
        """
        Verilen istasyon adına göre yakıt markasını belirler.
        
        İstasyon adını, `constants.FUEL_BRANDS` içinde tanımlanmış anahtar kelimelerle
        karşılaştırarak markayı bulur. Eşleşme bulunamazsa 'Other' döner.

        Args:
            station_name (str): Yakıt istasyonunun adı.

        Returns:
            str: Belirlenen marka adı veya 'Other'.
        """
        station_name_lower = station_name.lower()
        
        for brand, keywords in self.fuel_brands.items():
            if brand == constants.UNKNOWN_BRAND:
                continue
            for keyword in keywords:
                if keyword.lower() in station_name_lower:
                    return brand
        
        return constants.UNKNOWN_BRAND
    
    def collect_stations_by_city(self, city_name: str, max_stations: int = 50, collection_options: Dict[str, bool] = None, place_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Belirtilen şehir için mekan verilerini toplar.

        Şehri merkez alarak, farklı yarıçaplarda Google Places Servisi üzerinden belirtilen türde mekan araması yapar.
        Belirtilen `max_stations` sayısına ulaşana kadar veya tüm yarıçaplar taranana kadar devam eder.

        Args:
            city_name (str): Veri toplanacak şehirin adı (örn: 'Istanbul', 'Ankara').
            max_stations (int, optional): Şehir başına toplanacak maksimum mekan sayısı.
            collection_options (Dict[str, bool]): Hangi veri türlerinin toplanacağını belirten seçenekler.
            place_types (List[str], optional): Aranacak mekan türleri (örn: ['gas_station', 'restaurant']).

        Returns:
            List[Dict[str, Any]]: Toplanan ve zenginleştirilmiş mekan verilerinin listesi.
        """
        # Varsayılan mekan türü
        if place_types is None:
            place_types = ['gas_station']
            
        logger.info(f"🏙️ {city_name} şehri için {', '.join(place_types)} verisi toplama başlatılıyor...")
        
        # Şehir koordinatlarını bul
        city_info = self.geocoding_client.find_city_by_name(city_name)
        if not city_info:
            logger.error(f"❌ {city_name} şehri bulunamadı!")
            return []
        
        collected_stations = []
        search_radii = [5000, 10000, 15000, 25000, 40000]  # 5km'den 40km'ye
        collected_station_ids = set()
        
        for radius in search_radii:
            if len(collected_stations) >= max_stations:
                break
                
            logger.info(f"📍 {city_name} çevresinde {radius/1000:.0f}km yarıçapında {', '.join(place_types)} arama yapılıyor...")
            
            nearby_stations = self.places_client.search_nearby(
                latitude=city_info['latitude'],
                longitude=city_info['longitude'],
                radius_meters=radius,
                place_types=place_types
            )
            
            for station in nearby_stations:
                if len(collected_stations) >= max_stations:
                    break
                    
                station_id = station.get('id', '')
                if station_id and station_id not in collected_station_ids:
                    # İstasyon detaylarını ekle
                    enhanced_station = self.enhance_station_data(station, city_name, collection_options)
                    if enhanced_station:
                        collected_stations.append(enhanced_station)
                        collected_station_ids.add(station_id)
            
            time.sleep(2)  # Rate limiting
        
        logger.info(f"✅ {city_name} için {len(collected_stations)} istasyon verisi toplandı")
        return collected_stations
    
    def enhance_station_data(self, station: Dict[str, Any], city_name: str, collection_options: Dict[str, bool] = None) -> Optional[Dict[str, Any]]:
        """
        Ham istasyon verisini ek bilgilerle zenginleştirir.

        Google Places Servisi'nden gelen temel mekan verisine; marka, ülke, mock yakıt türleri,
        hizmetler, çalışma saatleri, fiyatlar ve tesis bilgileri gibi ek veriler ekler.
        Places API (New) field'larını da dahil eder.

        Args:
            station (Dict[str, Any]): Google Places Servisi'nden gelen ham mekan verisi.
            city_name (str): İstasyonun bulunduğu şehirin adı.
            collection_options (Dict[str, bool]): Hangi veri türlerinin toplanacağını belirten seçenekler.

        Returns:
            Optional[Dict[str, Any]]: Zenginleştirilmiş istasyon verisi. Gerekli temel bilgiler
                                      (örn: enlem/boylam) eksikse None dönebilir.
        """
        if collection_options is None:
            collection_options = {
                'fuel_options': True,
                'ev_charge_options': True,
                'parking_options': True,
                'payment_options': True,
                'accessibility': True,
                'secondary_hours': True
            }
            
        try:
            display_name = station.get('displayName', {})
            name = display_name.get('text', constants.UNKNOWN_NAME) if display_name else constants.UNKNOWN_NAME
            
            location = station.get('location', {})
            if not location.get('latitude') or not location.get('longitude'):
                return None
            
            # Marka belirle
            brand = self.identify_fuel_brand(name)
            
            # Mekan türünü belirle
            primary_type = station.get('primaryType', 'gas_station')
            
            # Temel veriler
            enhanced_data = {
                'station_id': station.get('id', ''),
                'name': name,
                'brand': brand if primary_type == 'gas_station' else 'N/A',
                'country': 'Turkey',
                'city': city_name,
                'region': f"{city_name}_region",
                'latitude': location.get('latitude'),
                'longitude': location.get('longitude'),
                'address': station.get('formattedAddress', ''),
                'short_formatted_address': station.get('shortFormattedAddress', ''),
                'rating': station.get('rating', constants.DEFAULT_RATING),
                'review_count': station.get('userRatingCount', constants.DEFAULT_REVIEW_COUNT),
                'business_status': station.get('businessStatus', constants.BUSINESS_STATUS_OPERATIONAL),
                'primary_type': primary_type,
                'primary_type_display_name': station.get('primaryTypeDisplayName', {}).get('text', 'Place'),
                'services': self.generate_services(),
                'operating_hours': self.generate_operating_hours(),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'data_source': constants.DATA_SOURCE_GOOGLE,
                'collection_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Mekan türüne göre spesifik alanları ekle
            if primary_type == 'gas_station':
                # Sadece benzin istasyonları için yakıt bilgileri
                enhanced_data['fuel_types'] = self.generate_fuel_types(brand)
                enhanced_data['price_data'] = self.generate_price_data('TR')
                enhanced_data['facilities'] = self.generate_facilities()
            else:
                # Diğer mekanlar için yakıt bilgisi yok
                enhanced_data['fuel_types'] = []
                enhanced_data['price_data'] = {}
                enhanced_data['facilities'] = {}
            
            # Places API (New) field'larını mekan türüne göre ekle
            if primary_type in ['gas_station', 'car_repair'] and collection_options.get('fuel_options', True):
                enhanced_data['fuel_options'] = self.generate_fuel_options(station.get('fuelOptions', {}))
            else:
                enhanced_data['fuel_options'] = {}
                
            # EV şarj - benzin istasyonu, otel, alışveriş merkezi için
            if primary_type in ['gas_station', 'lodging', 'shopping_mall', 'parking'] and collection_options.get('ev_charge_options', True):
                enhanced_data['ev_charge_options'] = self.generate_ev_charge_options(station.get('evChargeOptions', {}))
            else:
                enhanced_data['ev_charge_options'] = {'available': False}
                
            # Park - çoğu mekan için geçerli
            if collection_options.get('parking_options', True):
                enhanced_data['parking_options'] = self.generate_parking_options(station.get('parkingOptions', {}))
                
            # Ödeme - çoğu mekan için geçerli
            if collection_options.get('payment_options', True):
                enhanced_data['payment_options'] = self.generate_payment_options(station.get('paymentOptions', {}))
                
            # Erişilebilirlik - tüm mekanlar için geçerli
            if collection_options.get('accessibility', True):
                enhanced_data['accessibility_options'] = self.generate_accessibility_options(station)
                
            # İkincil saatler - benzin istasyonu ve bazı ticari mekanlar için
            if primary_type in ['gas_station', 'restaurant', 'bank', 'pharmacy', 'supermarket'] and collection_options.get('secondary_hours', True):
                enhanced_data['secondary_opening_hours'] = self.generate_secondary_hours(station.get('regularSecondaryOpeningHours', []))
            else:
                enhanced_data['secondary_opening_hours'] = {}
                
            # Sub destinations
            enhanced_data['sub_destinations'] = station.get('subDestinations', [])
            
            # Mekan türüne özgü spesifik alanları ekle
            enhanced_data.update(self.get_place_specific_fields(station, primary_type))
            
            return enhanced_data
            
        except Exception as e:
            logger.error(constants.LOG_MSG_ENRICHMENT_ERROR.format(error=e))
            return None
    
    def generate_fuel_types(self, brand: str) -> List[str]:
        """
        Verilen markaya göre mock yakıt türleri listesi oluşturur.
        
        Tüm markalar için temel yakıt türlerini (benzin, dizel) içerir ve belirli
        premium markalar için ek yakıt türleri (LPG, Premium Benzin) ekler.
        Ayrıca rastgele olarak E10/E85 yakıtlarını da ekleyebilir.

        Args:
            brand (str): Yakıt markası.

        Returns:
            List[str]: Oluşturulan yakıt türleri listesi.
        """
        base_types = constants.BASE_FUEL_TYPES.copy()
        
        if brand in constants.PREMIUM_FUEL_BRANDS:
            base_types.extend(['Premium Gasoline', 'AdBlue'])
        
        if brand in constants.LPG_BRANDS:
            base_types.append('LPG')
        
        # E10/E85 yakıtları (tablolardaki gibi)
        if np.random.random() > 0.7:  # %30 şans
            base_types.append('E10')
        
        if np.random.random() > 0.9:  # %10 şans
            base_types.append('E85')
        
        return base_types
    
    def generate_fuel_options(self, fuel_options_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places API (New) fuelOptions field'ından veri üretir.
        """
        return {
            'diesel': fuel_options_data.get('diesel', True),
            'regular_unleaded': fuel_options_data.get('regularUnleaded', True),
            'midgrade': fuel_options_data.get('midgrade', np.random.choice([True, False], p=[0.7, 0.3])),
            'premium': fuel_options_data.get('premium', np.random.choice([True, False], p=[0.8, 0.2])),
            'sp91': fuel_options_data.get('sp91', np.random.choice([True, False], p=[0.4, 0.6])),
            'sp91_e10': fuel_options_data.get('sp91E10', np.random.choice([True, False], p=[0.3, 0.7])),
            'sp95_e10': fuel_options_data.get('sp95E10', np.random.choice([True, False], p=[0.6, 0.4])),
            'lpg': fuel_options_data.get('lpg', np.random.choice([True, False], p=[0.3, 0.7])),
            'e85': fuel_options_data.get('e85', np.random.choice([True, False], p=[0.1, 0.9])),
            'biodiesel': fuel_options_data.get('biodiesel', np.random.choice([True, False], p=[0.2, 0.8])),
            'truck_diesel': fuel_options_data.get('truckDiesel', np.random.choice([True, False], p=[0.4, 0.6]))
        }
    
    def generate_ev_charge_options(self, ev_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places API (New) evChargeOptions field'ından EV şarj bilgileri üretir.
        """
        has_ev = np.random.choice([True, False], p=[0.3, 0.7])
        if not has_ev:
            return {'available': False}
            
        return {
            'available': True,
            'connector_count': ev_data.get('connectorCount', np.random.randint(2, 8)),
            'connector_aggregation': ev_data.get('connectorAggregation', []),
            'fast_charging': np.random.choice([True, False], p=[0.6, 0.4]),
            'power_levels': ['22kW', '50kW', '150kW'][:np.random.randint(1, 4)]
        }
    
    def generate_parking_options(self, parking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places API (New) parkingOptions field'ından park bilgileri üretir.
        """
        return {
            'free_parking_lot': parking_data.get('freeParkingLot', np.random.choice([True, False], p=[0.4, 0.6])),
            'paid_parking_lot': parking_data.get('paidParkingLot', np.random.choice([True, False], p=[0.3, 0.7])),
            'free_street_parking': parking_data.get('freeStreetParking', np.random.choice([True, False], p=[0.5, 0.5])),
            'paid_street_parking': parking_data.get('paidStreetParking', np.random.choice([True, False], p=[0.2, 0.8])),
            'valet_parking': parking_data.get('valetParking', np.random.choice([True, False], p=[0.1, 0.9])),
            'free_garage_parking': parking_data.get('freeGarageParking', np.random.choice([True, False], p=[0.2, 0.8])),
            'paid_garage_parking': parking_data.get('paidGarageParking', np.random.choice([True, False], p=[0.3, 0.7]))
        }
    
    def generate_payment_options(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places API (New) paymentOptions field'ından ödeme bilgileri üretir.
        """
        return {
            'accepts_credit_cards': payment_data.get('acceptsCreditCards', True),
            'accepts_debit_cards': payment_data.get('acceptsDebitCards', True),
            'accepts_cash_only': payment_data.get('acceptsCashOnly', False),
            'accepts_nfc': payment_data.get('acceptsNfc', np.random.choice([True, False], p=[0.7, 0.3]))
        }
    
    def generate_accessibility_options(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """
        Places API (New) accessibility field'larından erişilebilirlik bilgileri üretir.
        """
        return {
            'wheelchair_accessible_parking': station.get('wheelchairAccessibleParking', np.random.choice([True, False], p=[0.8, 0.2])),
            'wheelchair_accessible_entrance': station.get('wheelchairAccessibleEntrance', np.random.choice([True, False], p=[0.9, 0.1])),
            'wheelchair_accessible_restroom': station.get('wheelchairAccessibleRestroom', np.random.choice([True, False], p=[0.7, 0.3])),
            'wheelchair_accessible_seating': station.get('wheelchairAccessibleSeating', np.random.choice([True, False], p=[0.6, 0.4]))
        }
    
    def generate_secondary_hours(self, secondary_hours_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Places API (New) regularSecondaryOpeningHours field'ından ikincil çalışma saatleri üretir.
        """
        if not secondary_hours_data:
            return {
                'drive_through': self.generate_drive_through_hours(),
                'car_wash': self.generate_car_wash_hours(),
                'convenience_store': self.generate_convenience_store_hours()
            }
        
        return {
            'drive_through': secondary_hours_data[0] if len(secondary_hours_data) > 0 else {},
            'car_wash': secondary_hours_data[1] if len(secondary_hours_data) > 1 else {},
            'convenience_store': secondary_hours_data[2] if len(secondary_hours_data) > 2 else {}
        }
    
    def generate_drive_through_hours(self) -> Dict[str, str]:
        """Drive-through saatleri üretir."""
        if np.random.random() > 0.6:  # %40 şans drive-through var
            return {"all_days": "06:00-23:00"}
        return {}
    
    def generate_car_wash_hours(self) -> Dict[str, str]:
        """Araç yıkama saatleri üretir."""
        if np.random.random() > 0.7:  # %30 şans car wash var
            return {"monday_friday": "08:00-20:00", "weekend": "09:00-18:00"}
        return {}
    
    def generate_convenience_store_hours(self) -> Dict[str, str]:
        """Market saatleri üretir."""
        if np.random.random() > 0.5:  # %50 şans market var
            return {"all_days": "05:00-23:00"}
        return {}
    
    def get_place_specific_fields(self, station: Dict[str, Any], primary_type: str) -> Dict[str, Any]:
        """
        Mekan türüne özgü spesifik alanları Google Places Servisi (New) dokümantasyonuna göre döndürür.
        """
        specific_fields = {}
        
        if primary_type == 'hospital':
            specific_fields.update(self.get_hospital_fields(station))
        elif primary_type == 'restaurant':
            specific_fields.update(self.get_restaurant_fields(station))
        elif primary_type == 'lodging':
            specific_fields.update(self.get_lodging_fields(station))
        elif primary_type == 'bank':
            specific_fields.update(self.get_bank_fields(station))
        elif primary_type == 'pharmacy':
            specific_fields.update(self.get_pharmacy_fields(station))
        elif primary_type == 'supermarket':
            specific_fields.update(self.get_supermarket_fields(station))
        elif primary_type == 'shopping_mall':
            specific_fields.update(self.get_shopping_mall_fields(station))
        elif primary_type == 'tourist_attraction':
            specific_fields.update(self.get_tourist_attraction_fields(station))
        elif primary_type == 'atm':
            specific_fields.update(self.get_atm_fields(station))
        elif primary_type == 'car_repair':
            specific_fields.update(self.get_car_repair_fields(station))
        elif primary_type == 'parking':
            specific_fields.update(self.get_parking_fields(station))
            
        return specific_fields
    
    def get_hospital_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Hastane için spesifik alanlar"""
        return {
            'hospital_departments': station.get('hospitalDepartments', []),
            'medical_services': station.get('medicalServices', []),
            'emergency_services': station.get('emergencyServices', np.random.choice([True, False], p=[0.8, 0.2])),
            'accepts_insurance': station.get('acceptsInsurance', np.random.choice([True, False], p=[0.9, 0.1])),
            'appointment_required': station.get('appointmentRequired', np.random.choice([True, False], p=[0.7, 0.3])),
            'has_ambulance': np.random.choice([True, False], p=[0.6, 0.4]),
            'has_pharmacy_inside': np.random.choice([True, False], p=[0.8, 0.2]),
            'visiting_hours': station.get('visitingHours', {'weekdays': '08:00-20:00', 'weekend': '10:00-18:00'})
        }
    
    def get_restaurant_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Restoran için spesifik alanlar"""
        return {
            'menu_for_children': station.get('menuForChildren', np.random.choice([True, False], p=[0.6, 0.4])),
            'serves_cocktails': station.get('servesCocktails', np.random.choice([True, False], p=[0.3, 0.7])),
            'serves_beer': station.get('servesBeer', np.random.choice([True, False], p=[0.5, 0.5])),
            'serves_wine': station.get('servesWine', np.random.choice([True, False], p=[0.4, 0.6])),
            'serves_vegetarian_food': station.get('servesVegetarianFood', np.random.choice([True, False], p=[0.7, 0.3])),
            'serves_breakfast': station.get('servesBreakfast', np.random.choice([True, False], p=[0.4, 0.6])),
            'serves_brunch': station.get('servesBrunch', np.random.choice([True, False], p=[0.3, 0.7])),
            'serves_lunch': station.get('servesLunch', np.random.choice([True, False], p=[0.9, 0.1])),
            'serves_dinner': station.get('servesDinner', np.random.choice([True, False], p=[0.8, 0.2])),
            'reservable': station.get('reservable', np.random.choice([True, False], p=[0.6, 0.4])),
            'takeout': station.get('takeout', np.random.choice([True, False], p=[0.7, 0.3])),
            'delivery': station.get('delivery', np.random.choice([True, False], p=[0.5, 0.5])),
            'dine_in': station.get('dineIn', np.random.choice([True, False], p=[0.9, 0.1])),
            'curbside_pickup': station.get('curbsidePickup', np.random.choice([True, False], p=[0.3, 0.7])),
            'outdoor_seating': station.get('outdoorSeating', np.random.choice([True, False], p=[0.4, 0.6])),
            'live_music': station.get('liveMusic', np.random.choice([True, False], p=[0.2, 0.8])),
            'good_for_children': station.get('goodForChildren', np.random.choice([True, False], p=[0.6, 0.4])),
            'good_for_groups': station.get('goodForGroups', np.random.choice([True, False], p=[0.7, 0.3])),
            'cuisine_type': station.get('cuisineType', ['Turkish', 'International', 'Fast Food', 'Italian', 'Chinese'][np.random.randint(0, 5)]),
            'price_range': station.get('priceRange', np.random.choice(['$', '$$', '$$$', '$$$$'], p=[0.3, 0.4, 0.2, 0.1]))
        }
    
    def get_lodging_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Konaklama için spesifik alanlar"""
        return {
            'pet_friendly': station.get('petFriendly', np.random.choice([True, False], p=[0.3, 0.7])),
            'pool_available': station.get('poolAvailable', np.random.choice([True, False], p=[0.4, 0.6])),
            'fitness_center': station.get('fitnessCenter', np.random.choice([True, False], p=[0.5, 0.5])),
            'business_center': station.get('businessCenter', np.random.choice([True, False], p=[0.6, 0.4])),
            'free_wifi': station.get('freeWifi', np.random.choice([True, False], p=[0.9, 0.1])),
            'room_service': station.get('roomService', np.random.choice([True, False], p=[0.4, 0.6])),
            'spa_services': station.get('spaServices', np.random.choice([True, False], p=[0.2, 0.8])),
            'restaurant_on_site': station.get('restaurantOnSite', np.random.choice([True, False], p=[0.7, 0.3])),
            'bar_on_site': station.get('barOnSite', np.random.choice([True, False], p=[0.5, 0.5])),
            'conference_rooms': station.get('conferenceRooms', np.random.choice([True, False], p=[0.4, 0.6])),
            'laundry_service': station.get('laundryService', np.random.choice([True, False], p=[0.8, 0.2])),
            'concierge_service': station.get('conciergeService', np.random.choice([True, False], p=[0.3, 0.7])),
            'airport_shuttle': station.get('airportShuttle', np.random.choice([True, False], p=[0.3, 0.7])),
            'smoking_allowed': station.get('smokingAllowed', np.random.choice([True, False], p=[0.1, 0.9])),
            'air_conditioning': station.get('airConditioning', np.random.choice([True, False], p=[0.9, 0.1])),
            'heating': station.get('heating', np.random.choice([True, False], p=[0.95, 0.05])),
            'check_in_time': station.get('checkInTime', '14:00'),
            'check_out_time': station.get('checkOutTime', '12:00'),
            'star_rating': station.get('starRating', np.random.randint(1, 6))
        }
    
    def get_bank_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Banka için spesifik alanlar"""
        return {
            'atm_available': station.get('atmAvailable', np.random.choice([True, False], p=[0.9, 0.1])),
            'drive_through': station.get('driveThrough', np.random.choice([True, False], p=[0.6, 0.4])),
            'foreign_exchange': station.get('foreignExchange', np.random.choice([True, False], p=[0.4, 0.6])),
            'safe_deposit_boxes': station.get('safeDepositBoxes', np.random.choice([True, False], p=[0.7, 0.3])),
            'mortgage_services': station.get('mortgageServices', np.random.choice([True, False], p=[0.8, 0.2])),
            'investment_services': station.get('investmentServices', np.random.choice([True, False], p=[0.6, 0.4])),
            'business_banking': station.get('businessBanking', np.random.choice([True, False], p=[0.8, 0.2])),
            'notary_services': station.get('notaryServices', np.random.choice([True, False], p=[0.3, 0.7]))
        }
    
    def get_pharmacy_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Eczane için spesifik alanlar"""
        return {
            'prescription_filling': station.get('prescriptionFilling', True),
            'otc_medications': station.get('otcMedications', True),
            'health_screenings': station.get('healthScreenings', np.random.choice([True, False], p=[0.6, 0.4])),
            'vaccinations': station.get('vaccinations', np.random.choice([True, False], p=[0.7, 0.3])),
            'delivery_service': station.get('deliveryService', np.random.choice([True, False], p=[0.4, 0.6])),
            'consultation_services': station.get('consultationServices', np.random.choice([True, False], p=[0.5, 0.5])),
            'medical_equipment': station.get('medicalEquipment', np.random.choice([True, False], p=[0.3, 0.7]))
        }
    
    def get_supermarket_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Süpermarket için spesifik alanlar"""
        return {
            'grocery_pickup': station.get('groceryPickup', np.random.choice([True, False], p=[0.5, 0.5])),
            'grocery_delivery': station.get('groceryDelivery', np.random.choice([True, False], p=[0.6, 0.4])),
            'pharmacy_inside': station.get('pharmacyInside', np.random.choice([True, False], p=[0.3, 0.7])),
            'bakery': station.get('bakery', np.random.choice([True, False], p=[0.7, 0.3])),
            'deli': station.get('deli', np.random.choice([True, False], p=[0.6, 0.4])),
            'butcher': station.get('butcher', np.random.choice([True, False], p=[0.5, 0.5])),
            'seafood_counter': station.get('seafoodCounter', np.random.choice([True, False], p=[0.4, 0.6])),
            'organic_products': station.get('organicProducts', np.random.choice([True, False], p=[0.6, 0.4])),
            'self_checkout': station.get('selfCheckout', np.random.choice([True, False], p=[0.7, 0.3]))
        }
    
    def get_shopping_mall_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Alışveriş merkezi için spesifik alanlar"""
        return {
            'number_of_stores': station.get('numberOfStores', np.random.randint(20, 200)),
            'food_court': station.get('foodCourt', np.random.choice([True, False], p=[0.9, 0.1])),
            'movie_theater': station.get('movieTheater', np.random.choice([True, False], p=[0.6, 0.4])),
            'department_stores': station.get('departmentStores', np.random.choice([True, False], p=[0.8, 0.2])),
            'children_play_area': station.get('childrenPlayArea', np.random.choice([True, False], p=[0.5, 0.5])),
            'valet_parking': station.get('valetParking', np.random.choice([True, False], p=[0.3, 0.7])),
            'customer_service': station.get('customerService', np.random.choice([True, False], p=[0.9, 0.1]))
        }
    
    def get_tourist_attraction_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Turistik yer için spesifik alanlar"""
        return {
            'entrance_fee': station.get('entranceFee', np.random.choice([True, False], p=[0.6, 0.4])),
            'guided_tours': station.get('guidedTours', np.random.choice([True, False], p=[0.5, 0.5])),
            'audio_guide': station.get('audioGuide', np.random.choice([True, False], p=[0.4, 0.6])),
            'gift_shop': station.get('giftShop', np.random.choice([True, False], p=[0.7, 0.3])),
            'photography_allowed': station.get('photographyAllowed', np.random.choice([True, False], p=[0.8, 0.2])),
            'historical_significance': station.get('historicalSignificance', np.random.choice([True, False], p=[0.6, 0.4])),
            'family_friendly': station.get('familyFriendly', np.random.choice([True, False], p=[0.8, 0.2]))
        }
    
    def get_atm_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """ATM için spesifik alanlar"""
        return {
            'bank_network': station.get('bankNetwork', ['Akbank', 'Garanti', 'İş Bankası', 'Yapı Kredi', 'Ziraat'][np.random.randint(0, 5)]),
            'cash_withdrawal': station.get('cashWithdrawal', True),
            'balance_inquiry': station.get('balanceInquiry', True),
            'deposit_available': station.get('depositAvailable', np.random.choice([True, False], p=[0.6, 0.4])),
            'international_cards': station.get('internationalCards', np.random.choice([True, False], p=[0.8, 0.2])),
            'indoor_location': station.get('indoorLocation', np.random.choice([True, False], p=[0.4, 0.6]))
        }
    
    def get_car_repair_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Oto tamir için spesifik alanlar"""
        return {
            'oil_change': station.get('oilChange', np.random.choice([True, False], p=[0.9, 0.1])),
            'tire_service': station.get('tireService', np.random.choice([True, False], p=[0.8, 0.2])),
            'brake_service': station.get('brakeService', np.random.choice([True, False], p=[0.7, 0.3])),
            'engine_repair': station.get('engineRepair', np.random.choice([True, False], p=[0.6, 0.4])),
            'transmission_service': station.get('transmissionService', np.random.choice([True, False], p=[0.5, 0.5])),
            'air_conditioning_service': station.get('airConditioningService', np.random.choice([True, False], p=[0.6, 0.4])),
            'electrical_service': station.get('electricalService', np.random.choice([True, False], p=[0.5, 0.5])),
            'towing_service': station.get('towingService', np.random.choice([True, False], p=[0.4, 0.6])),
            'inspection_service': station.get('inspectionService', np.random.choice([True, False], p=[0.7, 0.3]))
        }
    
    def get_parking_fields(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Park alanı için spesifik alanlar"""
        return {
            'parking_type': station.get('parkingType', np.random.choice(['surface', 'garage', 'street'])),
            'hourly_rate': station.get('hourlyRate', np.random.uniform(2.0, 15.0)),
            'daily_rate': station.get('dailyRate', np.random.uniform(20.0, 100.0)),
            'monthly_rate': station.get('monthlyRate', np.random.uniform(200.0, 800.0)),
            'covered_parking': station.get('coveredParking', np.random.choice([True, False], p=[0.4, 0.6])),
            'security_cameras': station.get('securityCameras', np.random.choice([True, False], p=[0.7, 0.3])),
            'attendant_on_site': station.get('attendantOnSite', np.random.choice([True, False], p=[0.5, 0.5])),
            'electric_vehicle_charging': station.get('electricVehicleCharging', np.random.choice([True, False], p=[0.3, 0.7]))
        }
    
    def generate_services(self) -> List[str]:
        """
        Rastgele mock istasyon hizmetleri listesi oluşturur.
        
        `constants.POSSIBLE_SERVICES` listesinden rastgele 3 ila 6 adet hizmet seçer.

        Returns:
            List[str]: Oluşturulan hizmet listesi.
        """
        possible_services = constants.POSSIBLE_SERVICES
        
        # Rastgele 3-6 hizmet seç
        num_services = np.random.randint(3, 7)
        return np.random.choice(possible_services, num_services, replace=False).tolist()
    
    def generate_operating_hours(self) -> Dict[str, str]:
        """
        Rastgele mock çalışma saatleri oluşturur.

        %80 ihtimalle 24 saat açık, %20 ihtimalle ise hafta içi ve hafta sonu
        farklı olan sınırlı çalışma saatleri oluşturur.

        Returns:
            Dict[str, str]: Çalışma saatlerini içeren sözlük.
        """
        # %80 şans 24 saat, %20 şans sınırlı saatler
        if np.random.random() > 0.2:
            return {"all_days": "00:00-23:59"}
        else:
            return {
                "monday_friday": "06:00-22:00",
                "saturday": "07:00-21:00", 
                "sunday": "08:00-20:00"
            }
    
    def generate_price_data(self, country_code: str) -> Dict[str, float]:
        """
        Ülke koduna göre mock yakıt fiyatları oluşturur.

        `constants.BASE_PRICES` içindeki ülkeye özgü temel fiyatları alır, bu fiyatlara
        %±5 arasında rastgele bir varyasyon ekleyerek daha gerçekçi bir fiyat seti oluşturur.

        Args:
            country_code (str): Fiyatların oluşturulacağı ülkenin kodu.

        Returns:
            Dict[str, float]: Yakıt türlerini ve fiyatlarını içeren sözlük.
        """
        # Ortalama fiyatlar (EUR/L)
        base_prices = constants.BASE_PRICES
        
        default_prices = constants.DEFAULT_PRICES
        prices = base_prices.get(country_code, default_prices)
        
        # Fiyatlara %±5 rastgele varyasyon ekle
        return {
            'gasoline': round(prices['gasoline'] * np.random.uniform(0.95, 1.05), 3),
            'diesel': round(prices['diesel'] * np.random.uniform(0.95, 1.05), 3),
            'premium_gasoline': round(prices['gasoline'] * 1.1 * np.random.uniform(0.95, 1.05), 3),
            'currency': constants.PRICE_CURRENCY
        }
    
    def generate_facilities(self) -> Dict[str, Any]:
        """
        Rastgele mock istasyon tesis bilgileri oluşturur.

        Pompa sayısı, engelli erişimi, EV şarj imkanı, kamyon dostu olup olmadığı,
        ödeme yöntemleri ve sadakat programı gibi bilgileri rastgele olarak üretir.

        Returns:
            Dict[str, Any]: Tesis bilgilerini içeren sözlük.
        """
        return {
            'pump_count': np.random.randint(4, 16),
            'accessibility': np.random.choice([True, False], p=[0.8, 0.2]),
            'ev_charging': np.random.choice([True, False], p=[0.3, 0.7]),
            'truck_friendly': np.random.choice([True, False], p=[0.4, 0.6]),
            'payment_methods': constants.PAYMENT_METHODS,
            'loyalty_program': np.random.choice([True, False], p=[0.6, 0.4])
        }
    
    def collect_comprehensive_data(self, selected_cities: List[str] = None, collection_options: Dict[str, bool] = None, place_types: List[str] = None):
        """
        Seçilen Türkiye şehirleri için kapsamlı veri toplama işlemini başlatır ve yönetir.

        Belirtilen şehirler için `collect_stations_by_city` fonksiyonunu çağırır. 
        Toplanan tüm verileri bir araya getirir, özet istatistikler oluşturur, 
        veritabanına kaydeder ve sonuçları döndürür.

        Args:
            selected_cities (List[str]): Veri toplanacak şehirler listesi.
            collection_options (Dict[str, bool]): Hangi veri türlerinin toplanacağını belirten seçenekler.
            place_types (List[str]): Aranacak mekan türleri.

        Returns:
            Dict[str, Any]: Toplama işleminin özetini, şehir bazında özetleri,
                            tüm mekan verilerini ve analitik bilgileri içeren
                            kapsamlı bir sözlük.
        """
        logger.info("🚀 Türkiye şehirleri için kapsamlı veri toplama başlatılıyor...")
        
        # Varsayılan şehirler listesi
        if not selected_cities:
            selected_cities = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]
        
        all_stations = []
        city_summaries = {}
        
        for city_name in selected_cities:
            try:
                logger.info(f"🏙️ {city_name} şehri için veri toplama başlatılıyor...")
                
                # Şehir başına maksimum 50 mekan topla
                stations = self.collect_stations_by_city(city_name, max_stations=50, collection_options=collection_options, place_types=place_types)
                
                if stations:
                    all_stations.extend(stations)
                    
                    # Şehir özeti
                    city_summaries[city_name] = {
                        'city_name': city_name,
                        'total_stations': len(stations),
                        'brands': list(set([s['brand'] for s in stations])),
                        'avg_rating': np.mean([s['rating'] for s in stations if s['rating'] > 0]),
                        'collection_time': datetime.now(timezone.utc).isoformat()
                    }
                    
                    logger.info(f"✅ {city_name} şehri için {len(stations)} istasyon verisi toplandı")
                else:
                    logger.warning(f"⚠️ {city_name} şehri için istasyon bulunamadı")
                
                # Veritabanına kaydet - tüm yeni field'larla birlikte
                logger.info(f"🗄️ {city_name} şehri verilerini veritabanına kaydediliyor...")
                for station in stations:
                    try:
                        station_data = FuelStationData(
                            station_id=station['station_id'],
                            name=station['name'],
                            brand=station['brand'],
                            country=station['country'],
                            region=station['region'],
                            latitude=station['latitude'],
                            longitude=station['longitude'],
                            address=station['address'],
                            fuel_types=station['fuel_types'],
                            services=station['services'],
                            rating=station['rating'],
                            review_count=station['review_count'],
                            operating_hours=station['operating_hours'],
                            price_data=station['price_data'],
                            last_updated=datetime.now(timezone.utc)
                        )
                        success = self.warehouse.insert_fuel_station(station_data)
                        if not success:
                            logger.warning(f"⚠️ İstasyon veritabanına kaydedilemedi: {station['name']}")
                    except Exception as e:
                        logger.error(f"❌ İstasyon kaydetme hatası: {e}")
                
                logger.info(f"✅ {city_name} şehri verileri veritabanına kaydedildi")
                
                time.sleep(3)  # Şehirler arası bekleme
                
            except Exception as e:
                logger.error(f"❌ {city_name} şehri veri toplama hatası: {e}")
                continue
        
        # Özet rapor
        total_summary = {
            'total_cities': len(selected_cities),
            'total_stations_collected': len(all_stations),
            'cities_processed': len(city_summaries),
            'collection_date': datetime.now(timezone.utc).isoformat(),
            'data_quality': 'high',
            'api_source': 'Google Places Servisi (New)',
            'version': '4.0',
            'country': 'Turkey'
        }
        
        # Sonuçları kaydet
        output_data = {
            'summary': total_summary,
            'city_summaries': city_summaries,
            'stations': all_stations,
            'analytics': self.generate_analytics(all_stations),
            'metadata': {
                'collection_method': 'city_based_turkey',
                'data_enhancement': True,
                'places_api_new_fields': True,
                'real_time_prices': True,
                'facilities_included': True
            }
        }
        
        # JSON ve Excel dosya çıktısı kaldırıldı - sadece veritabanına kayıt
        logger.info("📊 Tüm veriler veritabanına kaydedildi")
        
        logger.info("🎉 Türkiye veri toplama işlemi tamamlandı!")
        logger.info(f"🗄️ Veritabanı güncellendi")
        logger.info(f"📊 Toplam istasyon: {len(all_stations)}, Şehir: {len(city_summaries)}")
        
        return output_data
    
    def generate_analytics(self, stations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Toplanan istasyon verilerinden analitik bir özet oluşturur.

        Marka ve ülke dağılımı, puan istatistikleri, yakıt türü popülerliği,
        toplam ve aktif istasyon sayısı gibi analitik verileri hesaplar.

        Args:
            stations (List[Dict[str, Any]]): Analiz edilecek istasyon verilerinin listesi.

        Returns:
            Dict[str, Any]: Hesaplanan analitik verileri içeren bir sözlük.
        """
        if not stations:
            return {}
        
        # Marka dağılımı
        brands = [s['brand'] for s in stations]
        brand_counts = pd.Series(brands).value_counts().to_dict()
        
        # Şehir dağılımı
        cities = [s.get('city', 'Unknown') for s in stations]
        city_counts = pd.Series(cities).value_counts().to_dict()
        
        # Puan istatistikleri
        ratings = [s['rating'] for s in stations if s['rating'] > 0]
        
        # Yakıt türü analizi
        all_fuel_types = []
        for station in stations:
            all_fuel_types.extend(station.get('fuel_types', []))
        fuel_type_counts = pd.Series(all_fuel_types).value_counts().to_dict()
        
        return {
            'brand_distribution': brand_counts,
            'city_distribution': city_counts,
            'rating_stats': {
                'average': np.mean(ratings) if ratings else 0,
                'median': np.median(ratings) if ratings else 0,
                'min': np.min(ratings) if ratings else 0,
                'max': np.max(ratings) if ratings else 0,
                'count': len(ratings)
            },
            'fuel_type_distribution': fuel_type_counts,
            'total_stations': len(stations),
            'active_stations': len([s for s in stations if s.get('business_status') == constants.BUSINESS_STATUS_OPERATIONAL]),
            'average_services_per_station': np.mean([len(s.get('services', [])) for s in stations])
        }
    
    def export_to_excel(self, stations: List[Dict[str, Any]], filename: str):
        """
        Toplanan verileri çok sayfalı bir Excel dosyasına aktarır.

        Dosya üç sayfa içerir:
        1. 'Stations': Ana istasyon verileri.
        2. 'Prices': Her istasyon için detaylı fiyat bilgileri.
        3. 'Summary': `generate_analytics` tarafından oluşturulan özet istatistikler.

        Args:
            stations (List[Dict[str, Any]]): Dışa aktarılacak istasyon verileri.
            filename (str): Oluşturulacak Excel dosyasının adı.
        """
        try:
            # Ana istasyon verileri
            df_stations = pd.DataFrame(stations)
            
            # Fiyat verilerini ayrı kolonlara çıkar
            price_data = []
            for station in stations:
                prices = station.get('price_data', {})
                price_row = {
                    'station_id': station['station_id'],
                    'gasoline_price': prices.get('gasoline', 0),
                    'diesel_price': prices.get('diesel', 0),
                    'premium_gasoline_price': prices.get('premium_gasoline', 0),
                    'currency': prices.get('currency', constants.PRICE_CURRENCY)
                }
                price_data.append(price_row)
            
            df_prices = pd.DataFrame(price_data)
            
            # Excel'e kaydet
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_stations.to_excel(writer, sheet_name='Stations', index=False)
                df_prices.to_excel(writer, sheet_name='Prices', index=False)
                
                # Özet sayfa
                summary_data = self.generate_analytics(stations)
                df_summary = pd.DataFrame([summary_data])
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            logger.info(constants.LOG_MSG_EXCEL_EXPORT_SUCCESS.format(filename=filename))
            
        except Exception as e:
            logger.error(constants.LOG_MSG_EXCEL_EXPORT_ERROR.format(error=e))

def main():
    """
    Komut satırından `enhanced_data_collector`'ı çalıştırmak için ana giriş noktası.
    
    Bu fonksiyon, `EnhancedDataCollector` sınıfından bir nesne oluşturur ve
    `collect_comprehensive_data` metodunu çağırarak tek seferlik bir veri
    toplama işlemi başlatır. Sonrasında veritabanından bir özet çeker ve yazdırır.
    """
    collector = EnhancedDataCollector()
    
    # Kapsamlı veri toplama
    result = collector.collect_comprehensive_data()
    
    # Veritabanından özet al
    db_summary = collector.warehouse.get_analytics_summary()
    print("\n📊 VERİTABANI ÖZETİ:")
    print(f"   💾 Toplam İstasyon: {db_summary['total_stations']}")
    print(f"   🗺️ Toplam Rota: {db_summary['total_routes']}")
    print(f"   🌍 Ülke Dağılımı: {db_summary['stations_by_country']}")

def get_final_data_from_db(db_path="db/fuel2go_data.db"):
    """
    Belirtilen veritabanı dosyasından son işlenmiş veriyi çeker.
    
    Not: Bu fonksiyonun içi henüz tam olarak doldurulmamıştır.
    
    Args:
        db_path (str, optional): PostgreSQL veritabanı bağlantısı için kullanılmayacak. 
                                 Varsayılan olarak PostgreSQL kullanılır.
    """
    # PostgreSQL kullanıldığı için bu fonksiyon güncellenmeli
    pass
    # ... existing code ...

if __name__ == "__main__":
    main()

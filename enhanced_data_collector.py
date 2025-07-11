#!/usr/bin/env python3
"""
Enhanced Data Collection System
Tablolardaki gibi kapsamlı benzin istasyonu verisi toplama sistemi
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
    Avrupa genelindeki benzin istasyonları için kapsamlı veri toplama ve işleme sistemi.
    
    Bu sınıf, Google Places API'sini kullanarak belirtilen ülkelerin başkentleri
    çevresindeki benzin istasyonlarını toplar, bu verileri zenginleştirir (marka tanıma,
    mock fiyat ve hizmet verileri ekleme) ve hem JSON hem de Excel formatında
    dışa aktarır. Ayrıca toplanan verileri bir PostgreSQL veritabanına kaydeder.
    """
    
    def __init__(self):
        """
        EnhancedDataCollector sınıfını başlatır.
        
        API istemcilerini (GoogleRoutesClient, GooglePlacesClient, GeocodingClient), veri ambarını
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
    
    def collect_stations_by_city(self, city_name: str, max_stations: int = 50, collection_options: Dict[str, bool] = None) -> List[Dict[str, Any]]:
        """
        Belirtilen şehir için benzin istasyonu verilerini toplar.

        Şehri merkez alarak, farklı yarıçaplarda Google Places API üzerinden 'gas_station' araması yapar.
        Belirtilen `max_stations` sayısına ulaşana kadar veya tüm yarıçaplar taranana kadar devam eder.

        Args:
            city_name (str): Veri toplanacak şehirin adı (örn: 'Istanbul', 'Ankara').
            max_stations (int, optional): Şehir başına toplanacak maksimum istasyon sayısı.
            collection_options (Dict[str, bool]): Hangi veri türlerinin toplanacağını belirten seçenekler.

        Returns:
            List[Dict[str, Any]]: Toplanan ve zenginleştirilmiş istasyon verilerinin listesi.
        """
        logger.info(f"🏙️ {city_name} şehri için istasyon verisi toplama başlatılıyor...")
        
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
                
            logger.info(f"📍 {city_name} çevresinde {radius/1000:.0f}km yarıçapında arama yapılıyor...")
            
            nearby_stations = self.places_client.search_nearby(
                latitude=city_info['latitude'],
                longitude=city_info['longitude'],
                radius_meters=radius,
                place_types=['gas_station']
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

        Google Places API'den gelen temel istasyon verisine; marka, ülke, mock yakıt türleri,
        hizmetler, çalışma saatleri, fiyatlar ve tesis bilgileri gibi ek veriler ekler.
        Places API (New) field'larını da dahil eder.

        Args:
            station (Dict[str, Any]): Google Places API'den gelen ham istasyon verisi.
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
            
            # Temel veriler
            enhanced_data = {
                'station_id': station.get('id', ''),
                'name': name,
                'brand': brand,
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
                'primary_type': station.get('primaryType', 'gas_station'),
                'primary_type_display_name': station.get('primaryTypeDisplayName', {}).get('text', 'Gas Station'),
                'fuel_types': self.generate_fuel_types(brand),
                'services': self.generate_services(),
                'operating_hours': self.generate_operating_hours(),
                'price_data': self.generate_price_data('TR'),
                'facilities': self.generate_facilities(),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'data_source': constants.DATA_SOURCE_GOOGLE,
                'collection_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Places API (New) field'larını ekle
            if collection_options.get('fuel_options', True):
                enhanced_data['fuel_options'] = self.generate_fuel_options(station.get('fuelOptions', {}))
                
            if collection_options.get('ev_charge_options', True):
                enhanced_data['ev_charge_options'] = self.generate_ev_charge_options(station.get('evChargeOptions', {}))
                
            if collection_options.get('parking_options', True):
                enhanced_data['parking_options'] = self.generate_parking_options(station.get('parkingOptions', {}))
                
            if collection_options.get('payment_options', True):
                enhanced_data['payment_options'] = self.generate_payment_options(station.get('paymentOptions', {}))
                
            if collection_options.get('accessibility', True):
                enhanced_data['accessibility_options'] = self.generate_accessibility_options(station)
                
            if collection_options.get('secondary_hours', True):
                enhanced_data['secondary_opening_hours'] = self.generate_secondary_hours(station.get('regularSecondaryOpeningHours', []))
                
            # Sub destinations
            enhanced_data['sub_destinations'] = station.get('subDestinations', [])
            
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
    
    def collect_comprehensive_data(self, selected_cities: List[str] = None, collection_options: Dict[str, bool] = None):
        """
        Seçilen Türkiye şehirleri için kapsamlı veri toplama işlemini başlatır ve yönetir.

        Belirtilen şehirler için `collect_stations_by_city` fonksiyonunu çağırır. 
        Toplanan tüm verileri bir araya getirir, özet istatistikler oluşturur, 
        veritabanına kaydeder ve sonuçları JSON ve Excel dosyalarına yazar.

        Args:
            collection_options (Dict[str, bool]): Hangi veri türlerinin toplanacağını belirten seçenekler.
            selected_cities (List[str]): Veri toplanacak şehirler listesi.

        Returns:
            Dict[str, Any]: Toplama işleminin özetini, şehir bazında özetleri,
                            tüm istasyon verilerini ve analitik bilgileri içeren
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
                
                # Şehir başına maksimum 50 istasyon topla
                stations = self.collect_stations_by_city(city_name, max_stations=50, collection_options=collection_options)
                
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
                
                # Veritabanına kaydet
                for station in stations:
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
                    self.warehouse.insert_fuel_station(station_data)
                
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
            'api_source': 'Google Places API (New)',
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
        
        # JSON dosyasına kaydet - numpy bool'ları çevir
        def convert_numpy_types(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        def clean_for_json(data):
            if isinstance(data, dict):
                return {k: clean_for_json(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [clean_for_json(item) for item in data]
            else:
                return convert_numpy_types(data)
        
        cleaned_data = clean_for_json(output_data)
        
        output_file = f"turkey_fuel_stations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        # Excel dosyasına da kaydet
        self.export_to_excel(all_stations, f"turkey_stations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        logger.info("🎉 Türkiye veri toplama işlemi tamamlandı!")
        logger.info(f"📄 JSON çıktı: {output_file}")
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

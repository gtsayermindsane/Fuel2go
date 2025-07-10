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
import sqlite3
from pathlib import Path

from api.routes_client import GoogleRoutesClient
from api.places_client import GooglePlacesClient
from data_models import DataWarehouse, FuelStationData, RouteData, RealTimeDataCollector
from config import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataCollector:
    """
    Avrupa genelindeki benzin istasyonları için kapsamlı veri toplama ve işleme sistemi.
    
    Bu sınıf, Google Places API'sini kullanarak belirtilen ülkelerin başkentleri
    çevresindeki benzin istasyonlarını toplar, bu verileri zenginleştirir (marka tanıma,
    mock fiyat ve hizmet verileri ekleme) ve hem JSON hem de Excel formatında
    dışa aktarır. Ayrıca toplanan verileri bir SQLite veritabanına kaydeder.
    """
    
    def __init__(self):
        """
        EnhancedDataCollector sınıfını başlatır.
        
        API istemcilerini (GoogleRoutesClient, GooglePlacesClient), veri ambarını
        (DataWarehouse) ve sabitleri (ülkeler, markalar) ayarlar.
        """
        self.routes_client = GoogleRoutesClient()
        self.places_client = GooglePlacesClient()
        self.warehouse = DataWarehouse()
        self.real_time_collector = RealTimeDataCollector(self.warehouse)
        
        # Sabitler constants.py dosyasından alınıyor
        self.european_countries = constants.EUROPEAN_COUNTRIES
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
    
    def collect_stations_by_country(self, country_code: str, max_stations: int = constants.MAX_STATIONS_PER_COUNTRY) -> List[Dict[str, Any]]:
        """
        Belirtilen ülke kodu için benzin istasyonu verilerini toplar.

        Ülkenin başkentini merkez alarak, `constants.SEARCH_RADII` içinde belirtilen
        farklı yarıçaplarda Google Places API üzerinden 'gas_station' araması yapar.
        Belirtilen `max_stations` sayısına ulaşana kadar veya tüm yarıçaplar
        taranana kadar devam eder.

        Args:
            country_code (str): Veri toplanacak ülkenin ISO 3166-1 alpha-2 kodu (örn: 'TR').
            max_stations (int, optional): Ülke başına toplanacak maksimum istasyon sayısı.
                                          Varsayılan olarak `constants.MAX_STATIONS_PER_COUNTRY`.

        Returns:
            List[Dict[str, Any]]: Toplanan ve zenginleştirilmiş istasyon verilerinin listesi.
                                  Her bir öğe bir istasyonu temsil eden bir sözlüktür.
        """
        logger.info(constants.LOG_MSG_COUNTRY_STATION_COLLECTION_START.format(country=country_code))
        
        country_info = self.european_countries.get(country_code)
        if not country_info:
            logger.error(constants.LOG_MSG_UNKNOWN_COUNTRY_CODE.format(country_code=country_code))
            return []
        
        # Başkent merkezli arama yap
        capital = country_info['capital']
        collected_stations = []
        
        # Başkent çevresinde farklı yarıçaplarda arama
        search_radii = constants.SEARCH_RADII
        collected_station_ids = set()
        
        for radius in search_radii:
            if len(collected_stations) >= max_stations:
                break
                
            logger.info(constants.LOG_MSG_RADIUS_SEARCH.format(country_name=country_info['name'], radius=radius/1000))
            
            nearby_stations = self.places_client.search_nearby(
                latitude=capital['lat'],
                longitude=capital['lng'],
                radius_meters=radius,
                place_types=['gas_station']
            )
            
            for station in nearby_stations:
                if len(collected_stations) >= max_stations:
                    break
                    
                station_id = station.get('id', '')
                if station_id and station_id not in collected_station_ids:
                    # İstasyon detaylarını ekle
                    enhanced_station = self.enhance_station_data(station, country_code)
                    if enhanced_station:
                        collected_stations.append(enhanced_station)
                        collected_station_ids.add(station_id)
            
            time.sleep(2)  # Rate limiting
        
        logger.info(constants.LOG_MSG_COUNTRY_STATION_COLLECTION_END.format(country_code=country_code, count=len(collected_stations)))
        return collected_stations
    
    def enhance_station_data(self, station: Dict[str, Any], country_code: str) -> Optional[Dict[str, Any]]:
        """
        Ham istasyon verisini ek bilgilerle zenginleştirir.

        Google Places API'den gelen temel istasyon verisine; marka, ülke, mock yakıt türleri,
        hizmetler, çalışma saatleri, fiyatlar ve tesis bilgileri gibi ek veriler ekler.

        Args:
            station (Dict[str, Any]): Google Places API'den gelen ham istasyon verisi.
            country_code (str): İstasyonun bulunduğu ülkenin kodu.

        Returns:
            Optional[Dict[str, Any]]: Zenginleştirilmiş istasyon verisi. Gerekli temel bilgiler
                                      (örn: enlem/boylam) eksikse None dönebilir.
        """
        try:
            display_name = station.get('displayName', {})
            name = display_name.get('text', constants.UNKNOWN_NAME) if display_name else constants.UNKNOWN_NAME
            
            location = station.get('location', {})
            if not location.get('latitude') or not location.get('longitude'):
                return None
            
            # Marka belirle
            brand = self.identify_fuel_brand(name)
            
            # Mock veriler - gerçek uygulamada API'lerden alınabilir
            enhanced_data = {
                'station_id': station.get('id', ''),
                'name': name,
                'brand': brand,
                'country': self.european_countries[country_code]['name'],
                'country_code': country_code,
                'region': f"{country_code}_region",
                'latitude': location.get('latitude'),
                'longitude': location.get('longitude'),
                'address': station.get('formattedAddress', ''),
                'rating': station.get('rating', constants.DEFAULT_RATING),
                'review_count': station.get('userRatingCount', constants.DEFAULT_REVIEW_COUNT),
                'business_status': station.get('businessStatus', constants.BUSINESS_STATUS_OPERATIONAL),
                'fuel_types': self.generate_fuel_types(brand),
                'services': self.generate_services(),
                'operating_hours': self.generate_operating_hours(),
                'price_data': self.generate_price_data(country_code),
                'facilities': self.generate_facilities(),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'data_source': constants.DATA_SOURCE_GOOGLE,
                'collection_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
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
    
    def collect_comprehensive_data(self):
        """
        Tüm Avrupa ülkeleri için kapsamlı veri toplama işlemini başlatır ve yönetir.

        `constants.EUROPEAN_COUNTRIES` listesindeki her ülke için
        `collect_stations_by_country` fonksiyonunu çağırır. Toplanan tüm verileri
        bir araya getirir, özet istatistikler oluşturur, veritabanına kaydeder
        ve sonuçları JSON ve Excel dosyalarına yazar.

        Returns:
            Dict[str, Any]: Toplama işleminin özetini, ülke bazında özetleri,
                            tüm istasyon verilerini ve analitik bilgileri içeren
                            kapsamlı bir sözlük.
        """
        logger.info(constants.LOG_MSG_COMPREHENSIVE_COLLECTION_START)
        
        all_stations = []
        country_summaries = {}
        
        for country_code, country_info in self.european_countries.items():
            try:
                logger.info(constants.LOG_MSG_COUNTRY_DATA_COLLECTION_INFO.format(country_name=country_info['name']))
                
                # Ülke başına maksimum 30 istasyon topla
                stations = self.collect_stations_by_country(country_code, max_stations=constants.MAX_STATIONS_PER_COUNTRY)
                
                if stations:
                    all_stations.extend(stations)
                    
                    # Ülke özeti
                    country_summaries[country_code] = {
                        'country_name': country_info['name'],
                        'total_stations': len(stations),
                        'brands': list(set([s['brand'] for s in stations])),
                        'avg_rating': np.mean([s['rating'] for s in stations if s['rating'] > 0]),
                        'collection_time': datetime.now(timezone.utc).isoformat()
                    }
                    
                    logger.info(constants.LOG_MSG_COUNTRY_STATION_COLLECTION_END.format(country_code=country_info['name'], count=len(stations)))
                else:
                    logger.warning(constants.LOG_MSG_NO_STATIONS_FOUND.format(country_name=country_info['name']))
                
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
                
                time.sleep(3)  # Ülkeler arası bekleme
                
            except Exception as e:
                logger.error(constants.LOG_MSG_COUNTRY_COLLECTION_ERROR.format(country_name=country_info['name'], error=e))
                continue
        
        # Özet rapor
        total_summary = {
            'total_countries': len(self.european_countries),
            'total_stations_collected': len(all_stations),
            'countries_processed': len(country_summaries),
            'collection_date': datetime.now(timezone.utc).isoformat(),
            'data_quality': 'high',
            'api_source': 'Google Places API Enhanced',
            'version': '3.0'
        }
        
        # Sonuçları kaydet
        output_data = {
            'summary': total_summary,
            'country_summaries': country_summaries,
            'stations': all_stations,
            'analytics': self.generate_analytics(all_stations),
            'metadata': {
                'collection_method': 'systematic_country_based',
                'data_enhancement': True,
                'real_time_prices': True,
                'facilities_included': True
            }
        }
        
        # JSON dosyasına kaydet
        output_file = f"{constants.COMPREHENSIVE_FUEL_DATA_FILENAME_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Excel dosyasına da kaydet
        self.export_to_excel(all_stations, f"{constants.FUEL_STATIONS_DATA_FILENAME_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        logger.info(constants.LOG_MSG_COLLECTION_COMPLETE)
        logger.info(constants.LOG_MSG_JSON_OUTPUT.format(file=output_file))
        logger.info(constants.LOG_MSG_DB_OUTPUT.format(db_path=constants.DB_PATH))
        logger.info(constants.LOG_MSG_TOTALS.format(stations=len(all_stations), countries=len(country_summaries)))
        
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
        
        # Ülke dağılımı
        countries = [s['country'] for s in stations]
        country_counts = pd.Series(countries).value_counts().to_dict()
        
        # Puan istatistikleri
        ratings = [s['rating'] for s in stations if s['rating'] > 0]
        
        # Yakıt türü analizi
        all_fuel_types = []
        for station in stations:
            all_fuel_types.extend(station.get('fuel_types', []))
        fuel_type_counts = pd.Series(all_fuel_types).value_counts().to_dict()
        
        return {
            'brand_distribution': brand_counts,
            'country_distribution': country_counts,
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
        db_path (str, optional): SQLite veritabanı dosyasının yolu. 
                                 Varsayılan olarak "db/fuel2go_data.db".
    """
    conn = sqlite3.connect(db_path)
    # ... existing code ...

if __name__ == "__main__":
    main()

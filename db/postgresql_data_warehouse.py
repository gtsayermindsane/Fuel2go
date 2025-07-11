#!/usr/bin/env python3
"""
PostgreSQL Data Warehouse
SQLite'ı tamamen değiştiren PostgreSQL tabanlı veri ambarı sınıfı
"""

import pandas as pd
import numpy as np
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from db.postgresql_config import postgresql_config
from data_models import FuelStationData, RouteData, TruckServiceData, DriverAmenityData, EmergencyServiceData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLDataWarehouse:
    """
    PostgreSQL tabanlı veri ambarı yönetimi sınıfı.
    
    SQLite DataWarehouse sınıfının tüm işlevlerini PostgreSQL için yeniden implement eder.
    """
    
    def __init__(self):
        """
        PostgreSQLDataWarehouse sınıfını başlatır.
        """
        self.config = postgresql_config
        self.test_connection()
    
    def test_connection(self) -> bool:
        """
        PostgreSQL bağlantısını test eder.
        
        Returns:
            bool: Bağlantı başarılı ise True
        """
        try:
            return self.config.test_connection()
        except Exception as e:
            logger.error(f"PostgreSQL bağlantı testi başarısız: {e}")
            return False
    
    def insert_fuel_station(self, station: FuelStationData) -> bool:
        """
        Veritabanına bir benzin istasyonu kaydı ekler veya mevcut kaydı günceller.
        
        Args:
            station (FuelStationData): Eklenecek istasyon verilerini içeren nesne
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            insert_query = """
            INSERT INTO fuel_stations (
                place_id, name, address, latitude, longitude, fuel_types, 
                amenities, opening_hours, phone_number, website, rating, 
                price_level, business_status, types, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (place_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                fuel_types = EXCLUDED.fuel_types,
                amenities = EXCLUDED.amenities,
                opening_hours = EXCLUDED.opening_hours,
                phone_number = EXCLUDED.phone_number,
                website = EXCLUDED.website,
                rating = EXCLUDED.rating,
                price_level = EXCLUDED.price_level,
                business_status = EXCLUDED.business_status,
                types = EXCLUDED.types,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            data = (
                station.station_id,
                station.name,
                station.address,
                station.latitude,
                station.longitude,
                json.dumps(station.fuel_types),
                json.dumps(station.services),
                json.dumps(station.operating_hours),
                None,  # phone_number
                None,  # website
                station.rating,
                None,  # price_level
                'operational',  # business_status
                json.dumps(['gas_station']),  # types
                datetime.now()
            )
            
            result = self.config.execute_query(insert_query, data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Fuel station ekleme hatası: {e}")
            return False
    
    def insert_route(self, route: RouteData) -> bool:
        """
        Veritabanına bir rota kaydı ekler.
        
        Args:
            route (RouteData): Eklenecek rota verilerini içeren nesne
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            insert_query = """
            INSERT INTO routes (
                origin_latitude, origin_longitude, destination_latitude, destination_longitude,
                origin_address, destination_address, distance_meters, duration_seconds,
                polyline_encoded, route_legs, route_steps, toll_info,
                fuel_consumption_liters, fuel_cost_estimate, carbon_emissions_kg,
                route_type, traffic_info, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
            """
            
            data = (
                route.origin_lat,
                route.origin_lng,
                route.dest_lat,
                route.dest_lng,
                f"Origin: {route.origin_lat}, {route.origin_lng}",
                f"Destination: {route.dest_lat}, {route.dest_lng}",
                int(route.distance_km * 1000),  # Convert to meters
                int(route.duration_minutes * 60),  # Convert to seconds
                "",  # polyline_encoded
                json.dumps([]),  # route_legs
                json.dumps([]),  # route_steps
                json.dumps({}),  # toll_info
                route.fuel_consumption_liters,
                route.cost_analysis.get('fuel_cost', 0),
                route.carbon_emission_kg,
                route.vehicle_type,
                json.dumps(route.traffic_conditions),
                datetime.now()
            )
            
            result = self.config.execute_query(insert_query, data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Route ekleme hatası: {e}")
            return False
    
    def insert_truck_service(self, service: TruckServiceData) -> bool:
        """
        Veritabanına bir kamyon hizmeti kaydı ekler veya mevcut kaydı günceller.
        
        Args:
            service (TruckServiceData): Eklenecek kamyon hizmeti verilerini içeren nesne
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            insert_query = """
            INSERT INTO truck_services (
                place_id, name, address, latitude, longitude, service_type,
                services_offered, truck_parking_available, adblue_available,
                mechanical_services, restaurant_available, shower_facilities,
                wifi_available, truck_washing, fuel_types, opening_hours,
                phone_number, website, rating, business_status, is_24_hours,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (place_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                service_type = EXCLUDED.service_type,
                services_offered = EXCLUDED.services_offered,
                truck_parking_available = EXCLUDED.truck_parking_available,
                adblue_available = EXCLUDED.adblue_available,
                mechanical_services = EXCLUDED.mechanical_services,
                restaurant_available = EXCLUDED.restaurant_available,
                shower_facilities = EXCLUDED.shower_facilities,
                wifi_available = EXCLUDED.wifi_available,
                truck_washing = EXCLUDED.truck_washing,
                fuel_types = EXCLUDED.fuel_types,
                opening_hours = EXCLUDED.opening_hours,
                phone_number = EXCLUDED.phone_number,
                website = EXCLUDED.website,
                rating = EXCLUDED.rating,
                business_status = EXCLUDED.business_status,
                is_24_hours = EXCLUDED.is_24_hours,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            data = (
                service.service_id,
                service.name,
                service.address,
                service.latitude,
                service.longitude,
                service.service_type,
                json.dumps(service.services_offered),
                service.truck_parking_spaces > 0,
                service.has_adblue,
                service.has_truck_repair,
                service.has_restaurant,
                service.has_shower,
                service.has_wifi,
                False,  # truck_washing
                json.dumps(['diesel']),  # fuel_types
                json.dumps(service.operating_hours),
                None,  # phone_number
                None,  # website
                service.rating,
                'operational',  # business_status
                True,  # is_24_hours
                datetime.now()
            )
            
            result = self.config.execute_query(insert_query, data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Truck service ekleme hatası: {e}")
            return False
    
    def insert_driver_amenity(self, amenity: DriverAmenityData) -> bool:
        """
        Veritabanına bir şoför konfor hizmeti kaydı ekler veya mevcut kaydı günceller.
        
        Args:
            amenity (DriverAmenityData): Eklenecek şoför konfor hizmeti verilerini içeren nesne
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            insert_query = """
            INSERT INTO driver_amenities (
                place_id, name, address, latitude, longitude, amenity_type,
                amenity_category, sleep_facilities, food_services, parking_capacity,
                shower_facilities, laundry_facilities, wifi_available,
                entertainment_facilities, pricing_info, opening_hours,
                phone_number, website, rating, business_status, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (place_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                amenity_type = EXCLUDED.amenity_type,
                amenity_category = EXCLUDED.amenity_category,
                sleep_facilities = EXCLUDED.sleep_facilities,
                food_services = EXCLUDED.food_services,
                parking_capacity = EXCLUDED.parking_capacity,
                shower_facilities = EXCLUDED.shower_facilities,
                laundry_facilities = EXCLUDED.laundry_facilities,
                wifi_available = EXCLUDED.wifi_available,
                entertainment_facilities = EXCLUDED.entertainment_facilities,
                pricing_info = EXCLUDED.pricing_info,
                opening_hours = EXCLUDED.opening_hours,
                phone_number = EXCLUDED.phone_number,
                website = EXCLUDED.website,
                rating = EXCLUDED.rating,
                business_status = EXCLUDED.business_status,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            data = (
                amenity.amenity_id,
                amenity.name,
                amenity.address,
                amenity.latitude,
                amenity.longitude,
                amenity.amenity_type,
                'accommodation',  # amenity_category
                amenity.room_count is not None and amenity.room_count > 0,
                json.dumps(amenity.meal_types),
                10,  # parking_capacity
                amenity.has_shower,
                amenity.has_laundry,
                amenity.has_wifi,
                json.dumps(['tv'] if amenity.has_tv else []),
                json.dumps({'range': amenity.price_range}),
                json.dumps({}),  # opening_hours
                None,  # phone_number
                None,  # website
                amenity.rating,
                'operational',  # business_status
                datetime.now()
            )
            
            result = self.config.execute_query(insert_query, data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Driver amenity ekleme hatası: {e}")
            return False
    
    def insert_emergency_service(self, emergency: EmergencyServiceData) -> bool:
        """
        Veritabanına bir acil durum hizmeti kaydı ekler veya mevcut kaydı günceller.
        
        Args:
            emergency (EmergencyServiceData): Eklenecek acil durum hizmeti verilerini içeren nesne
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            insert_query = """
            INSERT INTO emergency_services (
                place_id, name, address, latitude, longitude, service_type,
                emergency_type, is_24_hours, phone_number, emergency_phone,
                website, services_offered, rating, business_status, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (place_id) 
            DO UPDATE SET
                name = EXCLUDED.name,
                address = EXCLUDED.address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                service_type = EXCLUDED.service_type,
                emergency_type = EXCLUDED.emergency_type,
                is_24_hours = EXCLUDED.is_24_hours,
                phone_number = EXCLUDED.phone_number,
                emergency_phone = EXCLUDED.emergency_phone,
                website = EXCLUDED.website,
                services_offered = EXCLUDED.services_offered,
                rating = EXCLUDED.rating,
                business_status = EXCLUDED.business_status,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            data = (
                emergency.emergency_id,
                emergency.name,
                emergency.address,
                emergency.latitude,
                emergency.longitude,
                emergency.service_type,
                emergency.service_type,  # emergency_type
                emergency.is_24h,
                emergency.phone_number,
                emergency.phone_number,  # emergency_phone
                None,  # website
                json.dumps(emergency.emergency_services),
                5.0,  # rating
                'operational',  # business_status
                datetime.now()
            )
            
            result = self.config.execute_query(insert_query, data)
            return result is not None
            
        except Exception as e:
            logger.error(f"Emergency service ekleme hatası: {e}")
            return False
    
    def get_stations_by_country(self, country: str) -> pd.DataFrame:
        """
        Belirtilen ülkedeki tüm benzin istasyonlarını bir pandas DataFrame olarak döndürür.
        
        Args:
            country (str): Sorgulanacak ülkenin adı
            
        Returns:
            pd.DataFrame: Ülkedeki istasyonları içeren DataFrame
        """
        try:
            query = """
            SELECT id, place_id, name, address, latitude, longitude, 
                   fuel_types, amenities, rating, created_at
            FROM fuel_stations
            ORDER BY name;
            """
            
            with self.config.get_connection() as conn:
                df = pd.read_sql_query(query, conn)
                return df
                
        except Exception as e:
            logger.error(f"Stations by country sorgusu hatası: {e}")
            return pd.DataFrame()
    
    def get_routes_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Belirtilen tarih aralığında oluşturulmuş rotaları bir pandas DataFrame olarak döndürür.
        
        Args:
            start_date (str): Başlangıç tarihi (örn: '2023-01-01')
            end_date (str): Bitiş tarihi (örn: '2023-12-31')
            
        Returns:
            pd.DataFrame: Tarih aralığındaki rotaları içeren DataFrame
        """
        try:
            query = """
            SELECT id, origin_latitude, origin_longitude, destination_latitude, destination_longitude,
                   distance_meters, duration_seconds, fuel_consumption_liters, 
                   carbon_emissions_kg, route_type, created_at
            FROM routes
            WHERE created_at >= %s AND created_at <= %s
            ORDER BY created_at DESC;
            """
            
            with self.config.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=(start_date, end_date))
                return df
                
        except Exception as e:
            logger.error(f"Routes by date range sorgusu hatası: {e}")
            return pd.DataFrame()
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Veritabanındaki verilerden genel bir analitik özet oluşturur.
        
        Returns:
            Dict[str, Any]: Analitik özet metriklerini içeren bir sözlük
        """
        try:
            analytics = {}
            
            # Fuel stations count
            count_query = "SELECT COUNT(*) FROM fuel_stations;"
            result = self.config.execute_query(count_query)
            analytics['total_stations'] = result[0]['count'] if result else 0
            
            # Routes count
            count_query = "SELECT COUNT(*) FROM routes;"
            result = self.config.execute_query(count_query)
            analytics['total_routes'] = result[0]['count'] if result else 0
            
            # Average carbon emission
            avg_query = "SELECT AVG(carbon_emissions_kg) FROM routes WHERE carbon_emissions_kg IS NOT NULL;"
            result = self.config.execute_query(avg_query)
            analytics['avg_carbon_emission'] = float(result[0]['avg']) if result and result[0]['avg'] else 0
            
            # Average fuel consumption
            avg_query = "SELECT AVG(fuel_consumption_liters) FROM routes WHERE fuel_consumption_liters IS NOT NULL;"
            result = self.config.execute_query(avg_query)
            analytics['avg_fuel_consumption'] = float(result[0]['avg']) if result and result[0]['avg'] else 0
            
            # Truck services count
            count_query = "SELECT COUNT(*) FROM truck_services;"
            result = self.config.execute_query(count_query)
            analytics['total_truck_services'] = result[0]['count'] if result else 0
            
            # Driver amenities count
            count_query = "SELECT COUNT(*) FROM driver_amenities;"
            result = self.config.execute_query(count_query)
            analytics['total_driver_amenities'] = result[0]['count'] if result else 0
            
            # Emergency services count
            count_query = "SELECT COUNT(*) FROM emergency_services;"
            result = self.config.execute_query(count_query)
            analytics['total_emergency_services'] = result[0]['count'] if result else 0
            
            # Places API (New) field'ları için analizler
            # EV şarj istasyonları
            ev_query = """
            SELECT COUNT(*) FROM fuel_stations 
            WHERE ev_charge_options->>'available' = 'true';
            """
            result = self.config.execute_query(ev_query)
            analytics['ev_charging_stations'] = result[0]['count'] if result else 0
            
            # Erişilebilir istasyonlar
            accessible_query = """
            SELECT COUNT(*) FROM fuel_stations 
            WHERE accessibility_options->>'wheelchair_accessible_entrance' = 'true';
            """
            result = self.config.execute_query(accessible_query)
            analytics['accessible_stations'] = result[0]['count'] if result else 0
            
            # Park imkanı olan istasyonlar
            parking_query = """
            SELECT COUNT(*) FROM fuel_stations 
            WHERE parking_options->>'free_parking_lot' = 'true' 
               OR parking_options->>'paid_parking_lot' = 'true';
            """
            result = self.config.execute_query(parking_query)
            analytics['stations_with_parking'] = result[0]['count'] if result else 0
            
            # Şehir dağılımı
            city_query = """
            SELECT country, COUNT(*) as count
            FROM fuel_stations
            GROUP BY country
            ORDER BY count DESC;
            """
            result = self.config.execute_query(city_query)
            analytics['city_distribution'] = {row['country']: row['count'] for row in result} if result else {}
            
            # Marka dağılımı
            brand_query = """
            SELECT 
                CASE 
                    WHEN name ILIKE '%shell%' THEN 'Shell'
                    WHEN name ILIKE '%bp%' THEN 'BP'
                    WHEN name ILIKE '%total%' THEN 'Total'
                    WHEN name ILIKE '%opet%' THEN 'Opet'
                    WHEN name ILIKE '%petrol ofisi%' OR name ILIKE '%po%' THEN 'Petrol Ofisi'
                    WHEN name ILIKE '%türkiye petrolleri%' OR name ILIKE '%tp%' THEN 'TP'
                    ELSE 'Diğer'
                END as brand,
                COUNT(*) as count
            FROM fuel_stations
            GROUP BY 1
            ORDER BY count DESC;
            """
            result = self.config.execute_query(brand_query)
            analytics['brand_distribution'] = {row['brand']: row['count'] for row in result} if result else {}
            
            # EV şarj türleri dağılımı
            ev_dist_query = """
            SELECT 
                CASE 
                    WHEN ev_charge_options->>'fast_charging' = 'true' THEN 'Hızlı Şarj'
                    WHEN ev_charge_options->>'available' = 'true' THEN 'Normal Şarj'
                    ELSE 'Şarj Yok'
                END as ev_type,
                COUNT(*) as count
            FROM fuel_stations
            WHERE ev_charge_options IS NOT NULL
            GROUP BY 1;
            """
            result = self.config.execute_query(ev_dist_query)
            analytics['ev_charging_distribution'] = {row['ev_type']: row['count'] for row in result} if result else {}
            
            # Ödeme yöntemleri dağılımı
            payment_query = """
            SELECT 
                'Kredi Kartı' as payment_type,
                COUNT(*) as count
            FROM fuel_stations 
            WHERE payment_options->>'accepts_credit_cards' = 'true'
            UNION ALL
            SELECT 
                'NFC Ödeme' as payment_type,
                COUNT(*) as count
            FROM fuel_stations 
            WHERE payment_options->>'accepts_nfc' = 'true';
            """
            result = self.config.execute_query(payment_query)
            analytics['payment_methods_distribution'] = {row['payment_type']: row['count'] for row in result} if result else {}
            
            # Services by type
            services_query = """
            SELECT service_type, COUNT(*) as count
            FROM truck_services
            GROUP BY service_type
            ORDER BY count DESC;
            """
            result = self.config.execute_query(services_query)
            analytics['services_by_type'] = {row['service_type']: row['count'] for row in result} if result else {}
            
            analytics['last_updated'] = datetime.now().isoformat()
            
            return analytics
            
        except Exception as e:
            logger.error(f"Analytics summary hatası: {e}")
            return {
                'total_stations': 0,
                'total_routes': 0,
                'avg_carbon_emission': 0,
                'avg_fuel_consumption': 0,
                'total_truck_services': 0,
                'total_driver_amenities': 0,
                'total_emergency_services': 0,
                'ev_charging_stations': 0,
                'accessible_stations': 0,
                'stations_with_parking': 0,
                'city_distribution': {},
                'brand_distribution': {},
                'ev_charging_distribution': {},
                'payment_methods_distribution': {},
                'services_by_type': {},
                'last_updated': datetime.now().isoformat()
            }
    
    def get_truck_services_by_type(self, service_type: str, limit: int = 50) -> pd.DataFrame:
        """
        Belirtilen türdeki kamyon hizmetlerini döndürür.
        
        Args:
            service_type (str): Hizmet türü (truck_stop, gas_station, etc.)
            limit (int): Maksimum sonuç sayısı
            
        Returns:
            pd.DataFrame: Hizmet listesi
        """
        try:
            query = """
            SELECT place_id, name, address, latitude, longitude, service_type,
                   adblue_available, mechanical_services, restaurant_available,
                   shower_facilities, wifi_available, rating, created_at
            FROM truck_services
            WHERE service_type = %s
            ORDER BY rating DESC NULLS LAST
            LIMIT %s;
            """
            
            with self.config.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=(service_type, limit))
                return df
                
        except Exception as e:
            logger.error(f"Truck services by type sorgusu hatası: {e}")
            return pd.DataFrame()
    
    def get_services_near_location(self, latitude: float, longitude: float, 
                                 radius_km: float = 50, service_type: str = None) -> pd.DataFrame:
        """
        Belirtilen konum yakınındaki hizmetleri döndürür.
        
        Args:
            latitude (float): Enlem
            longitude (float): Boylam
            radius_km (float): Arama yarıçapı (km)
            service_type (str, optional): Hizmet türü filtresi
            
        Returns:
            pd.DataFrame: Yakındaki hizmetler listesi
        """
        try:
            # Basit coğrafi mesafe hesaplama (Haversine yaklaşık)
            base_query = """
            SELECT place_id, name, address, latitude, longitude, service_type,
                   adblue_available, mechanical_services, restaurant_available,
                   shower_facilities, wifi_available, rating,
                   (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                   cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * 
                   sin(radians(latitude)))) * 1000 as distance_meters
            FROM truck_services
            WHERE (6371 * acos(cos(radians(%s)) * cos(radians(latitude)) * 
                   cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * 
                   sin(radians(latitude)))) <= %s
            """
            
            params = [latitude, longitude, latitude, latitude, longitude, latitude, radius_km]
            
            if service_type:
                base_query += " AND service_type = %s"
                params.append(service_type)
            
            base_query += " ORDER BY distance_meters ASC LIMIT 100;"
            
            with self.config.get_connection() as conn:
                df = pd.read_sql_query(base_query, conn, params=params)
                return df
                
        except Exception as e:
            logger.error(f"Services near location sorgusu hatası: {e}")
            return pd.DataFrame()
    
    def cleanup_old_data(self, days_old: int = 30) -> bool:
        """
        Eski verileri temizler.
        
        Args:
            days_old (int): Kaç gün önceki veriler silinecek
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            cleanup_queries = [
                f"DELETE FROM routes WHERE created_at < NOW() - INTERVAL '{days_old} days';",
                f"DELETE FROM route_calculations WHERE created_at < NOW() - INTERVAL '{days_old} days';",
                f"DELETE FROM analytics WHERE timestamp < NOW() - INTERVAL '{days_old} days';"
            ]
            
            for query in cleanup_queries:
                self.config.execute_query(query)
            
            logger.info(f"Eski veriler temizlendi: {days_old} gün öncesi")
            return True
            
        except Exception as e:
            logger.error(f"Veri temizleme hatası: {e}")
            return False
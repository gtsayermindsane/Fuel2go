#!/usr/bin/env python3
"""
PostgreSQL Tablo Oluşturma Scriptleri
Fuel2go uygulaması için gerekli tüm tabloları oluşturur
"""

import logging
from datetime import datetime
from db.postgresql_config import postgresql_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TableCreator:
    """
    PostgreSQL tabloları oluşturma ve yönetme sınıfı.
    """
    
    def __init__(self):
        """
        TableCreator sınıfını başlatır.
        """
        self.config = postgresql_config
        
    def create_all_tables(self) -> bool:
        """
        Tüm tabloları oluşturur.
        
        Returns:
            bool: Tüm tablolar başarıyla oluşturulursa True
        """
        tables_to_create = [
            self.create_fuel_stations_table,
            self.create_routes_table,
            self.create_truck_services_table,
            self.create_driver_amenities_table,
            self.create_emergency_services_table,
            self.create_route_calculations_table,
            self.create_driver_stops_table,
            self.create_analytics_table
        ]
        
        logger.info("PostgreSQL tabloları oluşturuluyor...")
        
        for create_function in tables_to_create:
            try:
                if create_function():
                    logger.info(f"✅ {create_function.__name__} başarılı")
                else:
                    logger.error(f"❌ {create_function.__name__} başarısız")
                    return False
            except Exception as e:
                logger.error(f"❌ {create_function.__name__} hatası: {e}")
                return False
        
        logger.info("🎉 Tüm tablolar başarıyla oluşturuldu!")
        return True
    
    def create_fuel_stations_table(self) -> bool:
        """
        Yakıt istasyonları tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS fuel_stations (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            fuel_types JSONB,
            amenities JSONB,
            opening_hours JSONB,
            phone_number VARCHAR(50),
            website VARCHAR(255),
            rating DECIMAL(3, 2),
            price_level INTEGER,
            business_status VARCHAR(50),
            types JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_fuel_stations_location 
        ON fuel_stations USING GIST (
            ll_to_earth(latitude, longitude)
        );
        
        CREATE INDEX IF NOT EXISTS idx_fuel_stations_place_id 
        ON fuel_stations (place_id);
        
        CREATE INDEX IF NOT EXISTS idx_fuel_stations_name 
        ON fuel_stations (name);
        """
        
        try:
            # PostGIS extension olmadığı için basit indeks kullanıyoruz
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS fuel_stations (
                id SERIAL PRIMARY KEY,
                place_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                address TEXT,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                fuel_types JSONB,
                amenities JSONB,
                opening_hours JSONB,
                phone_number VARCHAR(50),
                website VARCHAR(255),
                rating DECIMAL(3, 2),
                price_level INTEGER,
                business_status VARCHAR(50),
                types JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_fuel_stations_lat_lng 
            ON fuel_stations (latitude, longitude);
            
            CREATE INDEX IF NOT EXISTS idx_fuel_stations_place_id 
            ON fuel_stations (place_id);
            
            CREATE INDEX IF NOT EXISTS idx_fuel_stations_name 
            ON fuel_stations (name);
            """
            
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Fuel stations tablosu oluşturma hatası: {e}")
            return False
    
    def create_routes_table(self) -> bool:
        """
        Rotalar tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS routes (
            id SERIAL PRIMARY KEY,
            origin_latitude DECIMAL(10, 8) NOT NULL,
            origin_longitude DECIMAL(11, 8) NOT NULL,
            destination_latitude DECIMAL(10, 8) NOT NULL,
            destination_longitude DECIMAL(11, 8) NOT NULL,
            origin_address TEXT,
            destination_address TEXT,
            distance_meters INTEGER,
            duration_seconds INTEGER,
            polyline_encoded TEXT,
            polyline_decoded JSONB,
            route_legs JSONB,
            route_steps JSONB,
            route_instructions JSONB,
            toll_info JSONB,
            fuel_consumption_liters DECIMAL(8, 2),
            fuel_cost_estimate DECIMAL(10, 2),
            carbon_emissions_kg DECIMAL(8, 2),
            route_type VARCHAR(50),
            traffic_info JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_routes_origin 
        ON routes (origin_latitude, origin_longitude);
        
        CREATE INDEX IF NOT EXISTS idx_routes_destination 
        ON routes (destination_latitude, destination_longitude);
        
        CREATE INDEX IF NOT EXISTS idx_routes_created_at 
        ON routes (created_at);
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Routes tablosu oluşturma hatası: {e}")
            return False
    
    def create_truck_services_table(self) -> bool:
        """
        Kamyon servisleri tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS truck_services (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            service_type VARCHAR(100) NOT NULL,
            services_offered JSONB,
            truck_parking_available BOOLEAN DEFAULT FALSE,
            adblue_available BOOLEAN DEFAULT FALSE,
            mechanical_services BOOLEAN DEFAULT FALSE,
            restaurant_available BOOLEAN DEFAULT FALSE,
            shower_facilities BOOLEAN DEFAULT FALSE,
            wifi_available BOOLEAN DEFAULT FALSE,
            truck_washing BOOLEAN DEFAULT FALSE,
            fuel_types JSONB,
            opening_hours JSONB,
            phone_number VARCHAR(50),
            website VARCHAR(255),
            rating DECIMAL(3, 2),
            price_level INTEGER,
            business_status VARCHAR(50),
            is_24_hours BOOLEAN DEFAULT FALSE,
            truck_accessibility_info JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_truck_services_location 
        ON truck_services (latitude, longitude);
        
        CREATE INDEX IF NOT EXISTS idx_truck_services_type 
        ON truck_services (service_type);
        
        CREATE INDEX IF NOT EXISTS idx_truck_services_adblue 
        ON truck_services (adblue_available) WHERE adblue_available = TRUE;
        
        CREATE INDEX IF NOT EXISTS idx_truck_services_24h 
        ON truck_services (is_24_hours) WHERE is_24_hours = TRUE;
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Truck services tablosu oluşturma hatası: {e}")
            return False
    
    def create_driver_amenities_table(self) -> bool:
        """
        Şoför olanakları tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS driver_amenities (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            amenity_type VARCHAR(100) NOT NULL,
            amenity_category VARCHAR(100),
            sleep_facilities BOOLEAN DEFAULT FALSE,
            rest_area_type VARCHAR(50),
            food_services JSONB,
            accommodation_type VARCHAR(50),
            parking_capacity INTEGER,
            security_features JSONB,
            shower_facilities BOOLEAN DEFAULT FALSE,
            laundry_facilities BOOLEAN DEFAULT FALSE,
            wifi_available BOOLEAN DEFAULT FALSE,
            entertainment_facilities JSONB,
            accessibility_features JSONB,
            pricing_info JSONB,
            opening_hours JSONB,
            phone_number VARCHAR(50),
            website VARCHAR(255),
            rating DECIMAL(3, 2),
            price_level INTEGER,
            business_status VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_driver_amenities_location 
        ON driver_amenities (latitude, longitude);
        
        CREATE INDEX IF NOT EXISTS idx_driver_amenities_type 
        ON driver_amenities (amenity_type);
        
        CREATE INDEX IF NOT EXISTS idx_driver_amenities_sleep 
        ON driver_amenities (sleep_facilities) WHERE sleep_facilities = TRUE;
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Driver amenities tablosu oluşturma hatası: {e}")
            return False
    
    def create_emergency_services_table(self) -> bool:
        """
        Acil durum servisleri tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS emergency_services (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            service_type VARCHAR(100) NOT NULL,
            emergency_type VARCHAR(100),
            is_24_hours BOOLEAN DEFAULT FALSE,
            phone_number VARCHAR(50),
            emergency_phone VARCHAR(50),
            website VARCHAR(255),
            services_offered JSONB,
            equipment_available JSONB,
            specializations JSONB,
            response_time_minutes INTEGER,
            coverage_area_km INTEGER,
            rating DECIMAL(3, 2),
            business_status VARCHAR(50),
            opening_hours JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_emergency_services_location 
        ON emergency_services (latitude, longitude);
        
        CREATE INDEX IF NOT EXISTS idx_emergency_services_type 
        ON emergency_services (service_type);
        
        CREATE INDEX IF NOT EXISTS idx_emergency_services_24h 
        ON emergency_services (is_24_hours) WHERE is_24_hours = TRUE;
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Emergency services tablosu oluşturma hatası: {e}")
            return False
    
    def create_route_calculations_table(self) -> bool:
        """
        Rota hesaplamaları tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS route_calculations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255),
            route_id INTEGER REFERENCES routes(id),
            calculation_type VARCHAR(100),
            input_parameters JSONB,
            results JSONB,
            fuel_consumption_liters DECIMAL(8, 2),
            fuel_cost_total DECIMAL(10, 2),
            carbon_emissions_kg DECIMAL(8, 2),
            alternative_routes JSONB,
            optimization_criteria VARCHAR(100),
            weather_conditions JSONB,
            traffic_conditions JSONB,
            vehicle_specifications JSONB,
            calculation_duration_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_route_calculations_session 
        ON route_calculations (session_id);
        
        CREATE INDEX IF NOT EXISTS idx_route_calculations_route 
        ON route_calculations (route_id);
        
        CREATE INDEX IF NOT EXISTS idx_route_calculations_created_at 
        ON route_calculations (created_at);
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Route calculations tablosu oluşturma hatası: {e}")
            return False
    
    def create_driver_stops_table(self) -> bool:
        """
        Şoför mola planları tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS driver_stops (
            id SERIAL PRIMARY KEY,
            route_id INTEGER REFERENCES routes(id),
            stop_sequence INTEGER NOT NULL,
            stop_latitude DECIMAL(10, 8) NOT NULL,
            stop_longitude DECIMAL(11, 8) NOT NULL,
            stop_address TEXT,
            distance_from_start_km DECIMAL(8, 2),
            estimated_arrival_time TIMESTAMP,
            stop_duration_minutes INTEGER,
            stop_type VARCHAR(100),
            services_available JSONB,
            regulatory_compliance JSONB,
            reason_for_stop VARCHAR(255),
            alternative_stops JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_driver_stops_route 
        ON driver_stops (route_id);
        
        CREATE INDEX IF NOT EXISTS idx_driver_stops_location 
        ON driver_stops (stop_latitude, stop_longitude);
        
        CREATE INDEX IF NOT EXISTS idx_driver_stops_sequence 
        ON driver_stops (route_id, stop_sequence);
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Driver stops tablosu oluşturma hatası: {e}")
            return False
    
    def create_analytics_table(self) -> bool:
        """
        Analitik verileri tablosunu oluşturur.
        
        Returns:
            bool: Başarılı ise True
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS analytics (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            event_category VARCHAR(100),
            user_session_id VARCHAR(255),
            route_id INTEGER REFERENCES routes(id),
            event_data JSONB,
            location_data JSONB,
            performance_metrics JSONB,
            user_interaction_data JSONB,
            api_usage_data JSONB,
            error_information JSONB,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_analytics_event_type 
        ON analytics (event_type);
        
        CREATE INDEX IF NOT EXISTS idx_analytics_timestamp 
        ON analytics (timestamp);
        
        CREATE INDEX IF NOT EXISTS idx_analytics_session 
        ON analytics (user_session_id);
        
        CREATE INDEX IF NOT EXISTS idx_analytics_route 
        ON analytics (route_id);
        """
        
        try:
            self.config.execute_query(create_table_sql)
            return True
        except Exception as e:
            logger.error(f"Analytics tablosu oluşturma hatası: {e}")
            return False
    
    def drop_all_tables(self) -> bool:
        """
        Tüm tabloları siler (dikkatli kullanın!).
        
        Returns:
            bool: Başarılı ise True
        """
        tables_to_drop = [
            'analytics',
            'driver_stops',
            'route_calculations',
            'emergency_services',
            'driver_amenities',
            'truck_services',
            'routes',
            'fuel_stations'
        ]
        
        logger.warning("⚠️ Tüm tablolar silinecek!")
        
        for table in tables_to_drop:
            try:
                self.config.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE;")
                logger.info(f"✅ {table} tablosu silindi")
            except Exception as e:
                logger.error(f"❌ {table} tablosu silinirken hata: {e}")
                return False
        
        return True
    
    def get_database_info(self) -> dict:
        """
        Veritabanı bilgilerini getirir.
        
        Returns:
            dict: Veritabanı bilgileri
        """
        try:
            tables_query = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """
            
            tables = self.config.execute_query(tables_query)
            
            total_size_query = """
            SELECT pg_size_pretty(pg_database_size(current_database())) as database_size;
            """
            
            size_info = self.config.execute_query(total_size_query)
            
            return {
                'tables': tables,
                'database_size': size_info[0]['database_size'] if size_info else 'N/A',
                'table_count': len(tables) if tables else 0
            }
            
        except Exception as e:
            logger.error(f"Veritabanı bilgileri alınırken hata: {e}")
            return {}

def main():
    """
    Ana çalıştırma fonksiyonu.
    """
    logger.info("🚀 Fuel2go PostgreSQL Tablo Oluşturucu")
    logger.info("=" * 50)
    
    creator = TableCreator()
    
    # Bağlantı testi
    logger.info("🔧 PostgreSQL bağlantısı test ediliyor...")
    if not creator.config.test_connection():
        logger.error("❌ PostgreSQL bağlantısı başarısız!")
        return False
    
    logger.info("✅ PostgreSQL bağlantısı başarılı!")
    
    # Tabloları oluştur
    if creator.create_all_tables():
        logger.info("🎉 Tüm tablolar başarıyla oluşturuldu!")
        
        # Veritabanı bilgilerini göster
        db_info = creator.get_database_info()
        if db_info:
            logger.info(f"📊 Veritabanı İstatistikleri:")
            logger.info(f"   - Tablo sayısı: {db_info['table_count']}")
            logger.info(f"   - Veritabanı boyutu: {db_info['database_size']}")
            logger.info(f"   - Oluşturulan tablolar:")
            for table in db_info['tables']:
                logger.info(f"     ✅ {table['table_name']}")
        
        return True
    else:
        logger.error("❌ Tablolar oluşturulurken hata!")
        return False

if __name__ == "__main__":
    main()
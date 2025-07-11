#!/usr/bin/env python3
"""
Uygulama genelinde kullanılacak sabit (constant) değerler.
Bu dosya, "magic string" ve "magic number" kullanımını önleyerek
kodun okunabilirliğini ve bakımını kolaylaştırmayı amaçlar.
"""

# Streamlit Arayüz Sabitleri
APP_TITLE = "Fuel2go - Akıllı Rota ve Veri Yönetimi"
APP_ICON = "🚗"
APP_LAYOUT = "wide"
APP_INITIAL_SIDEBAR_STATE = "expanded"

# Başlık ve Alt Başlıklar
HEADER_TITLE = "🚗 Fuel2go - Advanced Data Platform"
HEADER_SUBTITLE = "Akıllı Rota Optimizasyonu ve Kapsamlı Veri Yönetimi"
HEADER_TEXT = "Türkiye Geneli Mekan Bilgi Servisi"

# Sidebar
SIDEBAR_HEADER = "🎛️ Kontrol Paneli"
SIDEBAR_SUBHEADER_SYSTEM_STATUS = "📊 Sistem Durumu"
SIDEBAR_SUBHEADER_ROUTE_SETTINGS = "📍 Rota Ayarları"
API_STATUS_ACTIVE = "✅ Servis Aktif"
API_STATUS_INACTIVE = "❌ Servis İnaktif"
DB_STATUS_ACTIVE = "✅ Veritabanı Aktif"
DB_STATUS_INACTIVE = "❌ Veritabanı Hatası"

# Rota Ayarları
DEFAULT_ORIGIN_LAT = 41.0082
DEFAULT_ORIGIN_LNG = 28.9784
DEFAULT_DEST_LAT = 39.9334
DEFAULT_DEST_LNG = 32.8597
TRAVEL_MODES = ["DRIVE", "WALK", "BICYCLE", "TRANSIT"]
ROUTING_PREFERENCES = ["TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL", "FUEL_EFFICIENT"]
VEHICLE_TYPES = ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"]

# Ana Sekmeler
TAB_TITLES = [
    "🚗 Rota Hesaplama",
    "📊 Veri Toplama",
    "🔍 Analiz",
    "📤 Export"
]

# Veri Toplama Paneli
DATA_COLLECTION_HEADER = "📊 Kapsamlı Veri Toplama Merkezi"
DATA_COLLECTION_CARD_TITLE = "🇹🇷 Türkiye Geneli Mekan Verisi"
DATA_COLLECTION_CARD_TEXT = "Türkiye şehirlerinden kapsamlı mekan verisi toplama sistemi"
DATA_COLLECTION_BUTTON_TEXT = "🚀 Veri Toplama Başlat"
DB_SUMMARY_BUTTON_TEXT = "📈 Veritabanı Özet"

# Veri Durumu Paneli
CURRENT_DATA_STATUS_HEADER = "📊 Mevcut Veri Durumu"
STATION_DISTRIBUTION_HEADER = "🌍 Ülke Bazında İstasyon Dağılımı"
EMISSION_ANALYSIS_HEADER = "🚗 Araç Tipi Bazında Ortalama Emisyon"

# Detaylı Analiz Paneli
DETAILED_ANALYSIS_HEADER = "🔍 Detaylı İstasyon Analizi"
FILTERED_RESULTS_HEADER = "📋 Filtrelenmiş Sonuçlar"
STATION_MAP_HEADER = "🗺️ İstasyon Haritası"

# Harita Ayarları
BRAND_COLORS = {
    'Shell': 'red',
    'BP': 'green',
    'Total': 'blue',
    'Petrol Ofisi': 'orange',
    'Opet': 'purple',
    'Other': 'gray'
}

# Veri Export Paneli
EXPORT_HEADER = "📤 Veri Dışa Aktarma"
EXCEL_EXPORT_HEADER = "📊 Excel Export"
JSON_EXPORT_HEADER = "🗃️ JSON Export"
DOWNLOAD_EXCEL_BUTTON = "Excel Dosyası İndir"
DOWNLOAD_JSON_BUTTON = "JSON Dosyası İndir"

# Dosya Adları ve Yolları
DB_PATH = "db/fuel2go_data.db"
STATIONS_JSON_PATH = "db/fuel_stations_data.json"
EXPORT_EXCEL_FILENAME_PREFIX = "fuel2go_export_"
EXPORT_JSON_FILENAME_PREFIX = "fuel2go_summary_"

# Hata Mesajları
ERROR_API_CLIENT_INIT = "Servis istemcisi başlatılamadı"
ERROR_DB_SUMMARY = "Özet alınamadı"
ERROR_DATA_COLLECTION = "Veri toplama hatası"
ERROR_DATA_STATUS = "Veri durumu gösterilemedi"
ERROR_ANALYSIS = "Analiz hatası"
ERROR_MAP_DISPLAY = "Harita görüntülenemiyor"
ERROR_EXCEL_EXPORT = "Excel export hatası"
ERROR_JSON_EXPORT = "JSON export hatası"
ERROR_ROUTE_COMPUTATION = "Rota hesaplama hatası"
ERROR_API_CLIENT_NOT_AVAILABLE = "Servis istemcisi mevcut değil"

# Bilgi Mesajları
INFO_NO_STATION_DATA = "📄 Henüz istasyon verisi yok. Veri toplama işlemini başlatın."
WARNING_NO_FILTERED_STATIONS = "⚠️ Filtreye uygun istasyon bulunamadı."
INFO_NO_STATIONS_TO_DISPLAY = "Gösterilecek istasyon yok"

# Footer
FOOTER_TEXT = "🌱 <strong>Fuel2go</strong> - Gelişmiş Veri Platformu"
FOOTER_SUBTEXT = "Türkiye Geneli Mekan Bilgi Servisi Veritabanı"

# Enhanced Data Collector Sabitleri
EUROPEAN_COUNTRIES = {
    'TR': {'name': 'Turkey', 'capital': {'lat': 39.9334, 'lng': 32.8597}},
    'DE': {'name': 'Germany', 'capital': {'lat': 52.5200, 'lng': 13.4050}},
    'FR': {'name': 'France', 'capital': {'lat': 48.8566, 'lng': 2.3522}},
    'ES': {'name': 'Spain', 'capital': {'lat': 40.4168, 'lng': -3.7038}},
    'IT': {'name': 'Italy', 'capital': {'lat': 41.9028, 'lng': 12.4964}},
    'UK': {'name': 'United Kingdom', 'capital': {'lat': 51.5074, 'lng': -0.1278}},
    'PL': {'name': 'Poland', 'capital': {'lat': 52.2297, 'lng': 21.0122}},
    'NL': {'name': 'Netherlands', 'capital': {'lat': 52.3676, 'lng': 4.9041}},
    'BE': {'name': 'Belgium', 'capital': {'lat': 50.8503, 'lng': 4.3517}},
    'AT': {'name': 'Austria', 'capital': {'lat': 48.2082, 'lng': 16.3738}},
    'CH': {'name': 'Switzerland', 'capital': {'lat': 46.9481, 'lng': 7.4474}},
    'CZ': {'name': 'Czech Republic', 'capital': {'lat': 50.0755, 'lng': 14.4378}},
    'DK': {'name': 'Denmark', 'capital': {'lat': 55.6761, 'lng': 12.5683}},
    'SE': {'name': 'Sweden', 'capital': {'lat': 59.3293, 'lng': 18.0686}},
    'NO': {'name': 'Norway', 'capital': {'lat': 59.9139, 'lng': 10.7522}},
    'FI': {'name': 'Finland', 'capital': {'lat': 60.1699, 'lng': 24.9384}}
}

FUEL_BRANDS = {
    'Shell': ['shell', 'Shell'],
    'BP': ['bp', 'BP'],
    'Total': ['total', 'Total', 'TotalEnergies'],
    'Esso': ['esso', 'Esso'],
    'Petrol Ofisi': ['petrol ofisi', 'po', 'Petrol Ofisi'],
    'Opet': ['opet', 'Opet'],
    'Lukoil': ['lukoil', 'Lukoil'],
    'OMV': ['omv', 'OMV'],
    'Aral': ['aral', 'Aral'],
    'Q8': ['q8', 'Q8'],
    'Other': []
}

SEARCH_RADII = [5000, 10000, 25000, 50000]  # Metre cinsinden
MAX_STATIONS_PER_COUNTRY = 30
DEFAULT_RATING = 0.0
DEFAULT_REVIEW_COUNT = 0
BUSINESS_STATUS_OPERATIONAL = 'OPERATIONAL'
DATA_SOURCE_GOOGLE = 'Google Places Servisi'
UNKNOWN_BRAND = 'Other'
UNKNOWN_NAME = 'Unknown'

# Mock Data Generation
BASE_FUEL_TYPES = ['Gasoline', 'Diesel']
PREMIUM_FUEL_BRANDS = ['Shell', 'BP', 'Total']
LPG_BRANDS = ['Shell', 'Total']
POSSIBLE_SERVICES = [
    'Car Wash', 'Shop', 'ATM', 'Parking', 'Toilet',
    'Cafe', 'Restaurant', 'WiFi', 'Air Pump', 'Vacuum'
]
PAYMENT_METHODS = ['Card', 'Cash', 'Mobile']
BASE_PRICES = {
    'TR': {'gasoline': 1.2, 'diesel': 1.1},
    'DE': {'gasoline': 1.6, 'diesel': 1.4},
    'FR': {'gasoline': 1.7, 'diesel': 1.5},
    'ES': {'gasoline': 1.5, 'diesel': 1.3},
    'IT': {'gasoline': 1.8, 'diesel': 1.6},
    'UK': {'gasoline': 1.9, 'diesel': 1.7},
    'PL': {'gasoline': 1.3, 'diesel': 1.2},
    'NL': {'gasoline': 2.0, 'diesel': 1.7}
}
DEFAULT_PRICES = {'gasoline': 1.5, 'diesel': 1.4}
PRICE_CURRENCY = 'EUR'

# Log ve Rapor Mesajları
LOG_MSG_COUNTRY_STATION_COLLECTION_START = "🌍 {country} ülkesi için istasyon toplama başlıyor..."
LOG_MSG_UNKNOWN_COUNTRY_CODE = "❌ Bilinmeyen ülke kodu: {country_code}"
LOG_MSG_RADIUS_SEARCH = "📍 {country_name} başkenti çevresinde {radius}km yarıçapta arama..."
LOG_MSG_COUNTRY_STATION_COLLECTION_END = "✅ {country_code} için {count} istasyon toplandı"
LOG_MSG_ENRICHMENT_ERROR = "❌ İstasyon verisi zenginleştirme hatası: {error}"
LOG_MSG_COMPREHENSIVE_COLLECTION_START = "🚀 Kapsamlı Türkiye mekan verisi toplama başlıyor..."
LOG_MSG_COUNTRY_DATA_COLLECTION_INFO = "🌍 {country_name} için veri toplama..."
LOG_MSG_NO_STATIONS_FOUND = "⚠️ {country_name}: Hiç istasyon bulunamadı"
LOG_MSG_COUNTRY_COLLECTION_ERROR = "❌ {country_name} veri toplama hatası: {error}"
LOG_MSG_COLLECTION_COMPLETE = "📊 TOPLAMA TAMAMLANDI!"
LOG_MSG_JSON_OUTPUT = "   📁 JSON: {file}"
LOG_MSG_DB_OUTPUT = "   🗃️  Database: {db_path}"
LOG_MSG_TOTALS = "   📈 Toplam: {stations} istasyon, {countries} ülke"
LOG_MSG_EXCEL_EXPORT_SUCCESS = "📊 Excel dosyası kaydedildi: {filename}"
LOG_MSG_EXCEL_EXPORT_ERROR = "❌ Excel export hatası: {error}"
COMPREHENSIVE_FUEL_DATA_FILENAME_PREFIX = "comprehensive_fuel_data_"
FUEL_STATIONS_DATA_FILENAME_PREFIX = "fuel_stations_data_"

# Data Collector Sabitleri
EARTH_RADIUS_KM = 6371.0
ROUTES_TO_COLLECT = [
    # Türkiye içi rotalar
    {
        'id': 'istanbul_ankara',
        'name': 'İstanbul → Ankara',
        'origin': {'latitude': 41.0082, 'longitude': 28.9784},
        'destination': {'latitude': 39.9334, 'longitude': 32.8597}
    },
    {
        'id': 'istanbul_izmir',
        'name': 'İstanbul → İzmir',
        'origin': {'latitude': 41.0082, 'longitude': 28.9784},
        'destination': {'latitude': 38.4192, 'longitude': 27.1287}
    },
    {
        'id': 'ankara_izmir',
        'name': 'Ankara → İzmir',
        'origin': {'latitude': 39.9334, 'longitude': 32.8597},
        'destination': {'latitude': 38.4192, 'longitude': 27.1287}
    },
    # Avrupa rotaları - E100 kategorisi
    {
        'id': 'berlin_munich',
        'name': 'Berlin → Munich',
        'origin': {'latitude': 52.5200, 'longitude': 13.4050},
        'destination': {'latitude': 48.1351, 'longitude': 11.5820}
    },
    {
        'id': 'paris_lyon',
        'name': 'Paris → Lyon',
        'origin': {'latitude': 48.8566, 'longitude': 2.3522},
        'destination': {'latitude': 45.7640, 'longitude': 4.8357}
    },
    {
        'id': 'madrid_barcelona',
        'name': 'Madrid → Barcelona',
        'origin': {'latitude': 40.4168, 'longitude': -3.7038},
        'destination': {'latitude': 41.3851, 'longitude': 2.1734}
    },
    {
        'id': 'rome_milan',
        'name': 'Rome → Milan',
        'origin': {'latitude': 41.9028, 'longitude': 12.4964},
        'destination': {'latitude': 45.4642, 'longitude': 9.1900}
    }
]
STATION_SEARCH_INTERVAL_KM = 50
STATION_SEARCH_RADIUS_METERS = 5000
TRAVEL_MODE_DRIVE = 'DRIVE'
ROUTING_PREFERENCE_TRAFFIC = 'TRAFFIC_AWARE'
LOG_MSG_ROUTE_STATION_SEARCH = "🛣️ Rota üzerinde istasyon aranıyor: {point}"
LOG_MSG_ROUTE_STATIONS_FOUND = "⛽️ Rota boyunca {count} potansiyel istasyon bulundu."
LOG_MSG_COMPUTING_ROUTE = "📍 {route_name} rotası hesaplanıyor..."
LOG_MSG_ROUTE_NOT_FOUND = "❌ {route_name} için rota bulunamadı."
LOG_MSG_ROUTE_DATA_COLLECTED = "✅ {route_name}: {distance}km, {duration}dk, {stations} istasyon bulundu."
LOG_MSG_ROUTE_GENERAL_ERROR = "❌ {route_name} genel hatası: {error}"
LOG_MSG_NEW_DATA_COLLECTION_START = "🚀 Yeni veri toplama (istasyonlarla birlikte) başlıyor..."
LOG_MSG_DATA_SAVED = "💾 Veriler {file} dosyasına kaydedildi"
LOG_MSG_SUMMARY = "📊 Özet: {routes} rota, {stations} toplam istasyon."
LOG_MSG_CONTINUOUS_COLLECTION_START = "🔄 Sürekli veri toplama başladı (her {interval} dakika)"
LOG_MSG_WAITING = "⏰ {interval} dakika bekleniyor..."
LOG_MSG_STOPPED = "⏹️ Veri toplama durduruldu"
LOG_MSG_UNEXPECTED_ERROR = "❌ Beklenmeyen hata: {error}"
METADATA_API_SOURCE = 'Google Places Servisi'
METADATA_DATA_QUALITY = 'real_time'
METADATA_VERSION = '2.0'

# Data Models Sabitleri
# Veritabanı Tablo Adları
TABLE_FUEL_STATIONS = "fuel_stations"
TABLE_ROUTES = "routes"
TABLE_TRAFFIC_DATA = "traffic_data"
TABLE_CARBON_EMISSIONS = "carbon_emissions"
TABLE_TRUCK_SERVICES = "truck_services"
TABLE_DRIVER_AMENITIES = "driver_amenities"
TABLE_EMERGENCY_SERVICES = "emergency_services"

# Veritabanı Şemaları (CREATE TABLE sorguları)
CREATE_TABLE_FUEL_STATIONS = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_FUEL_STATIONS} (
        station_id TEXT PRIMARY KEY,
        name TEXT,
        brand TEXT,
        country TEXT,
        region TEXT,
        latitude REAL,
        longitude REAL,
        address TEXT,
        fuel_types TEXT,
        services TEXT,
        rating REAL,
        review_count INTEGER,
        operating_hours TEXT,
        price_data TEXT,
        last_updated TEXT
    )
'''

CREATE_TABLE_ROUTES = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_ROUTES} (
        route_id TEXT PRIMARY KEY,
        origin_lat REAL,
        origin_lng REAL,
        dest_lat REAL,
        dest_lng REAL,
        distance_km REAL,
        duration_minutes REAL,
        traffic_delay_minutes REAL,
        fuel_consumption_liters REAL,
        carbon_emission_kg REAL,
        weather_conditions TEXT,
        traffic_conditions TEXT,
        road_conditions TEXT,
        vehicle_type TEXT,
        fuel_stations_en_route TEXT,
        cost_analysis TEXT,
        created_at TEXT
    )
'''

CREATE_TABLE_TRAFFIC_DATA = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_TRAFFIC_DATA} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id TEXT,
        timestamp TEXT,
        traffic_level TEXT,
        average_speed REAL,
        congestion_factor REAL,
        incidents TEXT,
        weather_impact REAL,
        FOREIGN KEY (route_id) REFERENCES {TABLE_ROUTES} (route_id)
    )
'''

CREATE_TABLE_CARBON_EMISSIONS = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_CARBON_EMISSIONS} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id TEXT,
        vehicle_type TEXT,
        emission_factor REAL,
        total_emission_kg REAL,
        emission_per_km REAL,
        fuel_type TEXT,
        calculation_method TEXT,
        timestamp TEXT,
        FOREIGN KEY (route_id) REFERENCES {TABLE_ROUTES} (route_id)
    )
'''

CREATE_TABLE_TRUCK_SERVICES = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_TRUCK_SERVICES} (
        service_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        service_type TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        truck_parking_spaces INTEGER,
        has_adblue BOOLEAN,
        has_truck_repair BOOLEAN,
        has_shower BOOLEAN,
        has_restaurant BOOLEAN,
        has_wifi BOOLEAN,
        operating_hours TEXT,
        payment_methods TEXT,
        services_offered TEXT,
        rating REAL,
        last_updated TEXT
    )
'''

CREATE_TABLE_DRIVER_AMENITIES = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_DRIVER_AMENITIES} (
        amenity_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        amenity_type TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        has_parking BOOLEAN,
        has_shower BOOLEAN,
        has_laundry BOOLEAN,
        has_wifi BOOLEAN,
        has_tv BOOLEAN,
        room_count INTEGER,
        price_range TEXT,
        meal_types TEXT,
        driver_discount BOOLEAN,
        rating REAL,
        review_count INTEGER,
        last_updated TEXT
    )
'''

CREATE_TABLE_EMERGENCY_SERVICES = f'''
    CREATE TABLE IF NOT EXISTS {TABLE_EMERGENCY_SERVICES} (
        emergency_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        service_type TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        phone_number TEXT,
        is_24h BOOLEAN,
        emergency_services TEXT,
        vehicle_assistance BOOLEAN,
        language_support TEXT,
        last_updated TEXT
    )
'''

# SQL Sorguları
SQL_INSERT_OR_REPLACE = "INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
SQL_SELECT_STATIONS_BY_COUNTRY = f"SELECT * FROM {TABLE_FUEL_STATIONS} WHERE country = ?"
SQL_SELECT_ROUTES_BY_DATE = f"SELECT * FROM {TABLE_ROUTES} WHERE created_at BETWEEN ? AND ?"
SQL_COUNT_FUEL_STATIONS = f"SELECT COUNT(*) FROM {TABLE_FUEL_STATIONS}"
SQL_COUNT_ROUTES = f"SELECT COUNT(*) FROM {TABLE_ROUTES}"
SQL_AVG_CARBON_EMISSION = f"SELECT AVG(carbon_emission_kg) FROM {TABLE_ROUTES}"
SQL_AVG_FUEL_CONSUMPTION = f"SELECT AVG(fuel_consumption_liters) FROM {TABLE_ROUTES}"
SQL_STATIONS_BY_COUNTRY_GROUP = f"SELECT country, COUNT(*) FROM {TABLE_FUEL_STATIONS} GROUP BY country"
SQL_EMISSIONS_BY_VEHICLE_GROUP = f"SELECT vehicle_type, AVG(carbon_emission_kg) FROM {TABLE_ROUTES} GROUP BY vehicle_type"


# RealTimeDataCollector Sabitleri (Mock Data)
TRAFFIC_LEVELS = ["low", "moderate", "high", "severe"]
FUEL_CONSUMPTION_RATES = {
    "gasoline_car": 7.5,
    "diesel_car": 6.2,
    "electric_car": 0.0,  # kWh/100km olarak 20 kWh
    "hybrid_car": 4.8
}
DEFAULT_FUEL_CONSUMPTION_RATE = 7.5
CARBON_EMISSION_FACTORS_IPCC = {
    "gasoline_car": 2.31,  # kg CO2/L benzin
    "diesel_car": 2.68,    # kg CO2/L dizel
    "electric_car": 0.067, # kg CO2/kWh (elektrik karışımına bağlı)
    "hybrid_car": 2.31     # Benzin bazlı hibrit
}
DEFAULT_EMISSION_FACTOR = 2.31
TRAFFIC_FACTORS = {
    "low": 1.0,
    "moderate": 1.2,
    "high": 1.5,
    "severe": 2.0
}
DEFAULT_TRAFFIC_FACTOR = 1.0
MOCK_FUEL_PRICES_TL = {
    "gasoline_car": 25.5,
    "diesel_car": 24.8,
    "electric_car": 2.5,
    "hybrid_car": 25.5
}
DEFAULT_MOCK_FUEL_PRICE = 25.5
MOCK_TOLL_COST_PER_KM = 0.15
DEFAULT_VEHICLE_TYPE = "gasoline_car" 
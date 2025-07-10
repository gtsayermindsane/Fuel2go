#!/usr/bin/env python3
"""
Fuel2go Data Models
Veri modelleri ve veri toplama sistemi
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import sqlite3
from pathlib import Path

@dataclass
class FuelStationData:
    """Benzin istasyonu veri modeli"""
    station_id: str
    name: str
    brand: str
    country: str
    region: str
    latitude: float
    longitude: float
    address: str
    fuel_types: List[str]
    services: List[str]
    rating: float
    review_count: int
    operating_hours: Dict[str, str]
    price_data: Dict[str, float]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'station_id': self.station_id,
            'name': self.name,
            'brand': self.brand,
            'country': self.country,
            'region': self.region,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'fuel_types': ','.join(self.fuel_types),
            'services': ','.join(self.services),
            'rating': self.rating,
            'review_count': self.review_count,
            'operating_hours': json.dumps(self.operating_hours),
            'price_data': json.dumps(self.price_data),
            'last_updated': self.last_updated.isoformat()
        }

@dataclass
class RouteData:
    """Rota veri modeli"""
    route_id: str
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    distance_km: float
    duration_minutes: float
    traffic_delay_minutes: float
    fuel_consumption_liters: float
    carbon_emission_kg: float
    weather_conditions: Dict[str, Any]
    traffic_conditions: Dict[str, Any]
    road_conditions: Dict[str, Any]
    vehicle_type: str
    fuel_stations_en_route: List[str]
    cost_analysis: Dict[str, float]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'route_id': self.route_id,
            'origin_lat': self.origin_lat,
            'origin_lng': self.origin_lng,
            'dest_lat': self.dest_lat,
            'dest_lng': self.dest_lng,
            'distance_km': self.distance_km,
            'duration_minutes': self.duration_minutes,
            'traffic_delay_minutes': self.traffic_delay_minutes,
            'fuel_consumption_liters': self.fuel_consumption_liters,
            'carbon_emission_kg': self.carbon_emission_kg,
            'weather_conditions': json.dumps(self.weather_conditions),
            'traffic_conditions': json.dumps(self.traffic_conditions),
            'road_conditions': json.dumps(self.road_conditions),
            'vehicle_type': self.vehicle_type,
            'fuel_stations_en_route': ','.join(self.fuel_stations_en_route),
            'cost_analysis': json.dumps(self.cost_analysis),
            'created_at': self.created_at.isoformat()
        }

class DataWarehouse:
    """Veri ambarı sınıfı - SQLite tabanlı"""
    
    def __init__(self, db_path: str = "fuel2go_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Veritabanı tablolarını oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fuel stations tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fuel_stations (
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
        ''')
        
        # Routes tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routes (
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
        ''')
        
        # Traffic data tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS traffic_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT,
                timestamp TEXT,
                traffic_level TEXT,
                average_speed REAL,
                congestion_factor REAL,
                incidents TEXT,
                weather_impact REAL,
                FOREIGN KEY (route_id) REFERENCES routes (route_id)
            )
        ''')
        
        # Carbon emissions tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carbon_emissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT,
                vehicle_type TEXT,
                emission_factor REAL,
                total_emission_kg REAL,
                emission_per_km REAL,
                fuel_type TEXT,
                calculation_method TEXT,
                timestamp TEXT,
                FOREIGN KEY (route_id) REFERENCES routes (route_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def insert_fuel_station(self, station: FuelStationData):
        """Benzin istasyonu verisi ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = station.to_dict()
        placeholders = ', '.join(['?' for _ in data])
        columns = ', '.join(data.keys())
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO fuel_stations ({columns})
            VALUES ({placeholders})
        ''', list(data.values()))
        
        conn.commit()
        conn.close()
    
    def insert_route(self, route: RouteData):
        """Rota verisi ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = route.to_dict()
        placeholders = ', '.join(['?' for _ in data])
        columns = ', '.join(data.keys())
        
        cursor.execute(f'''
            INSERT OR REPLACE INTO routes ({columns})
            VALUES ({placeholders})
        ''', list(data.values()))
        
        conn.commit()
        conn.close()
    
    def get_stations_by_country(self, country: str) -> pd.DataFrame:
        """Ülkeye göre istasyonları getir"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM fuel_stations WHERE country = ?",
            conn, params=[country]
        )
        conn.close()
        return df
    
    def get_routes_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Tarih aralığına göre rotaları getir"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            "SELECT * FROM routes WHERE created_at BETWEEN ? AND ?",
            conn, params=[start_date, end_date]
        )
        conn.close()
        return df
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Analitik özet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Temel istatistikler
        cursor.execute("SELECT COUNT(*) FROM fuel_stations")
        total_stations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM routes")
        total_routes = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(carbon_emission_kg) FROM routes")
        avg_carbon = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(fuel_consumption_liters) FROM routes")
        avg_fuel = cursor.fetchone()[0] or 0
        
        # Ülke bazında istasyon sayıları
        cursor.execute("SELECT country, COUNT(*) FROM fuel_stations GROUP BY country")
        country_stats = dict(cursor.fetchall())
        
        # Araç tipi bazında emisyon ortalamaları
        cursor.execute("SELECT vehicle_type, AVG(carbon_emission_kg) FROM routes GROUP BY vehicle_type")
        vehicle_emissions = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_stations": total_stations,
            "total_routes": total_routes,
            "avg_carbon_emission": avg_carbon,
            "avg_fuel_consumption": avg_fuel,
            "stations_by_country": country_stats,
            "emissions_by_vehicle": vehicle_emissions,
            "last_updated": datetime.now().isoformat()
        }

class RealTimeDataCollector:
    """Gerçek zamanlı veri toplama sistemi"""
    
    def __init__(self, warehouse: DataWarehouse):
        self.warehouse = warehouse
        self.weather_api_key = None  # Meteoroloji API anahtarı
        self.traffic_api_key = None  # Trafik API anahtarı
    
    def collect_weather_data(self, lat: float, lng: float) -> Dict[str, Any]:
        """Hava durumu verisi topla"""
        # OpenWeatherMap veya benzeri API kullanılabilir
        # Şimdilik mock data
        return {
            "temperature": np.random.normal(20, 10),
            "humidity": np.random.normal(60, 20),
            "wind_speed": np.random.normal(10, 5),
            "precipitation": np.random.exponential(2),
            "visibility": np.random.normal(10, 3),
            "pressure": np.random.normal(1013, 20)
        }
    
    def collect_traffic_data(self, route_polyline: str) -> Dict[str, Any]:
        """Trafik verisi topla"""
        # Google Traffic API veya Mapbox Traffic API kullanılabilir
        # Şimdilik mock data
        return {
            "traffic_level": np.random.choice(["low", "moderate", "high", "severe"]),
            "average_speed": np.random.normal(60, 20),
            "congestion_factor": np.random.uniform(1.0, 3.0),
            "incidents": [],
            "construction_zones": np.random.randint(0, 5)
        }
    
    def calculate_fuel_consumption(self, distance_km: float, vehicle_type: str, 
                                 traffic_factor: float = 1.0) -> float:
        """Yakıt tüketimi hesapla"""
        # Araç tipi bazında yakıt tüketimi (L/100km)
        consumption_rates = {
            "gasoline_car": 7.5,
            "diesel_car": 6.2,
            "electric_car": 0.0,  # kWh/100km olarak 20 kWh
            "hybrid_car": 4.8
        }
        
        base_consumption = consumption_rates.get(vehicle_type, 7.5)
        return (distance_km / 100) * base_consumption * traffic_factor
    
    def calculate_carbon_emission_ipcc(self, fuel_consumption: float, 
                                     vehicle_type: str) -> float:
        """IPCC yöntemleriyle karbon emisyon hesaplama"""
        # IPCC 2006 rehberi emission factors (kg CO2/L)
        emission_factors = {
            "gasoline_car": 2.31,  # kg CO2/L benzin
            "diesel_car": 2.68,    # kg CO2/L dizel
            "electric_car": 0.067, # kg CO2/kWh (elektrik karışımına bağlı)
            "hybrid_car": 2.31     # Benzin bazlı hibrit
        }
        
        factor = emission_factors.get(vehicle_type, 2.31)
        return fuel_consumption * factor
    
    def collect_comprehensive_route_data(self, origin: Dict[str, float], 
                                       destination: Dict[str, float],
                                       vehicle_type: str = "gasoline_car") -> RouteData:
        """Kapsamlı rota verisi topla"""
        
        # Google Routes API'dan temel rota bilgisi
        # (Mevcut GoogleRoutesClient kullanılabilir)
        
        # Mock data for demonstration
        distance_km = np.random.uniform(50, 500)
        base_duration = distance_km / np.random.uniform(50, 100)
        
        # Hava durumu verisi
        weather = self.collect_weather_data(origin["latitude"], origin["longitude"])
        
        # Trafik verisi
        traffic = self.collect_traffic_data("mock_polyline")
        
        # Trafik faktörü
        traffic_factor = {
            "low": 1.0,
            "moderate": 1.2,
            "high": 1.5,
            "severe": 2.0
        }.get(traffic["traffic_level"], 1.0)
        
        # Yakıt tüketimi
        fuel_consumption = self.calculate_fuel_consumption(
            distance_km, vehicle_type, traffic_factor
        )
        
        # Karbon emisyonu
        carbon_emission = self.calculate_carbon_emission_ipcc(
            fuel_consumption, vehicle_type
        )
        
        # Maliyet analizi
        fuel_prices = {
            "gasoline_car": 25.5,  # TL/L
            "diesel_car": 24.8,
            "electric_car": 2.5,   # TL/kWh
            "hybrid_car": 25.5
        }
        
        fuel_cost = fuel_consumption * fuel_prices.get(vehicle_type, 25.5)
        
        cost_analysis = {
            "fuel_cost": fuel_cost,
            "toll_cost": distance_km * 0.15,  # Ortalama köprü ücreti
            "total_cost": fuel_cost + (distance_km * 0.15)
        }
        
        return RouteData(
            route_id=f"route_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            origin_lat=origin["latitude"],
            origin_lng=origin["longitude"],
            dest_lat=destination["latitude"],
            dest_lng=destination["longitude"],
            distance_km=distance_km,
            duration_minutes=base_duration * 60,
            traffic_delay_minutes=(traffic_factor - 1) * base_duration * 60,
            fuel_consumption_liters=fuel_consumption,
            carbon_emission_kg=carbon_emission,
            weather_conditions=weather,
            traffic_conditions=traffic,
            road_conditions={"quality": "good", "construction": 0},
            vehicle_type=vehicle_type,
            fuel_stations_en_route=[],
            cost_analysis=cost_analysis,
            created_at=datetime.now()
        )

class FuelDB:
    def __init__(self, db_path: str = "db/fuel2go_data.db"):
        self.db_path = db_path
        self.conn = None

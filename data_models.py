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
from config import constants

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
    
    def __init__(self, db_path: str = constants.DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Veritabanı tablolarını oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tablolar constants dosyasından gelen sorgularla oluşturuluyor
        cursor.execute(constants.CREATE_TABLE_FUEL_STATIONS)
        cursor.execute(constants.CREATE_TABLE_ROUTES)
        cursor.execute(constants.CREATE_TABLE_TRAFFIC_DATA)
        cursor.execute(constants.CREATE_TABLE_CARBON_EMISSIONS)
        
        conn.commit()
        conn.close()
    
    def insert_fuel_station(self, station: FuelStationData):
        """Benzin istasyonu verisi ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = station.to_dict()
        placeholders = ', '.join(['?' for _ in data])
        columns = ', '.join(data.keys())
        
        query = constants.SQL_INSERT_OR_REPLACE.format(
            table=constants.TABLE_FUEL_STATIONS,
            columns=columns,
            placeholders=placeholders
        )
        cursor.execute(query, list(data.values()))
        
        conn.commit()
        conn.close()
    
    def insert_route(self, route: RouteData):
        """Rota verisi ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        data = route.to_dict()
        placeholders = ', '.join(['?' for _ in data])
        columns = ', '.join(data.keys())
        
        query = constants.SQL_INSERT_OR_REPLACE.format(
            table=constants.TABLE_ROUTES,
            columns=columns,
            placeholders=placeholders
        )
        cursor.execute(query, list(data.values()))
        
        conn.commit()
        conn.close()
    
    def get_stations_by_country(self, country: str) -> pd.DataFrame:
        """Ülkeye göre istasyonları getir"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            constants.SQL_SELECT_STATIONS_BY_COUNTRY,
            conn, params=[country]
        )
        conn.close()
        return df
    
    def get_routes_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Tarih aralığına göre rotaları getir"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(
            constants.SQL_SELECT_ROUTES_BY_DATE,
            conn, params=[start_date, end_date]
        )
        conn.close()
        return df
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Analitik özet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Temel istatistikler
        cursor.execute(constants.SQL_COUNT_FUEL_STATIONS)
        total_stations = cursor.fetchone()[0]
        
        cursor.execute(constants.SQL_COUNT_ROUTES)
        total_routes = cursor.fetchone()[0]
        
        cursor.execute(constants.SQL_AVG_CARBON_EMISSION)
        avg_carbon = cursor.fetchone()[0] or 0
        
        cursor.execute(constants.SQL_AVG_FUEL_CONSUMPTION)
        avg_fuel = cursor.fetchone()[0] or 0
        
        # Ülke bazında istasyon sayıları
        cursor.execute(constants.SQL_STATIONS_BY_COUNTRY_GROUP)
        country_stats = dict(cursor.fetchall())
        
        # Araç tipi bazında emisyon ortalamaları
        cursor.execute(constants.SQL_EMISSIONS_BY_VEHICLE_GROUP)
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
            "traffic_level": np.random.choice(constants.TRAFFIC_LEVELS),
            "average_speed": np.random.normal(60, 20),
            "congestion_factor": np.random.uniform(1.0, 3.0),
            "incidents": [],
            "construction_zones": np.random.randint(0, 5)
        }
    
    def calculate_fuel_consumption(self, distance_km: float, vehicle_type: str, 
                                 traffic_factor: float = 1.0) -> float:
        """Yakıt tüketimi hesapla"""
        # Araç tipi bazında yakıt tüketimi (L/100km)
        consumption_rates = constants.FUEL_CONSUMPTION_RATES
        
        base_consumption = consumption_rates.get(vehicle_type, constants.DEFAULT_FUEL_CONSUMPTION_RATE)
        return (distance_km / 100) * base_consumption * traffic_factor
    
    def calculate_carbon_emission_ipcc(self, fuel_consumption: float, 
                                     vehicle_type: str) -> float:
        """IPCC yöntemleriyle karbon emisyon hesaplama"""
        # IPCC 2006 rehberi emission factors (kg CO2/L)
        emission_factors = constants.CARBON_EMISSION_FACTORS_IPCC
        
        factor = emission_factors.get(vehicle_type, constants.DEFAULT_EMISSION_FACTOR)
        return fuel_consumption * factor
    
    def collect_comprehensive_route_data(self, origin: Dict[str, float], 
                                       destination: Dict[str, float],
                                       vehicle_type: str = constants.DEFAULT_VEHICLE_TYPE) -> RouteData:
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
        traffic_factor = constants.TRAFFIC_FACTORS.get(
            traffic["traffic_level"], constants.DEFAULT_TRAFFIC_FACTOR
        )
        
        # Yakıt tüketimi
        fuel_consumption = self.calculate_fuel_consumption(
            distance_km, vehicle_type, traffic_factor
        )
        
        # Karbon emisyonu
        carbon_emission = self.calculate_carbon_emission_ipcc(
            fuel_consumption, vehicle_type
        )
        
        # Maliyet analizi
        fuel_prices = constants.MOCK_FUEL_PRICES_TL
        
        fuel_cost = fuel_consumption * fuel_prices.get(vehicle_type, constants.DEFAULT_MOCK_FUEL_PRICE)
        
        toll_cost = distance_km * constants.MOCK_TOLL_COST_PER_KM
        
        cost_analysis = {
            "fuel_cost": fuel_cost,
            "toll_cost": toll_cost,
            "total_cost": fuel_cost + toll_cost
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
    def __init__(self, db_path: str = constants.DB_PATH):
        self.db_path = db_path
        self.conn = None

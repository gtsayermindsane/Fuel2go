#!/usr/bin/env python3
"""
Driver Assistant Module
Şoförlere yönelik rota analizi ve servis bulma özellikleri
"""

import math
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import numpy as np

from api.routes_client import GoogleRoutesClient
from api.places_client import GooglePlacesClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DriverAssistant:
    """
    Şoförlere yönelik rota analizi ve servis bulma sistemi.
    
    Bu sınıf, Google Routes ve Places API'lerini birleştirerek şoförler için
    rota üzerinde benzin istasyonları, dinlenme alanları, restoranlar ve
    diğer önemli servisleri bulmayı sağlar.
    """
    
    def __init__(self):
        """
        DriverAssistant sınıfını başlatır.
        
        Routes ve Places API istemcilerini oluşturur.
        """
        self.routes_client = GoogleRoutesClient()
        self.places_client = GooglePlacesClient()
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        İki nokta arasındaki mesafeyi haversine formülüyle hesaplar.
        
        Args:
            lat1, lon1: İlk noktanın koordinatları
            lat2, lon2: İkinci noktanın koordinatları
            
        Returns:
            float: Kilometre cinsinden mesafe
        """
        R = 6371  # Dünya yarıçapı (km)
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def interpolate_route_points(self, route_response: Dict[str, Any], 
                               interval_km: float = 50) -> List[Dict[str, float]]:
        """
        Rota üzerinde belirli mesafe aralıklarında noktalar oluşturur.
        
        Args:
            route_response: Google Routes API'den gelen rota yanıtı
            interval_km: Aralık mesafesi (kilometre)
            
        Returns:
            List[Dict[str, float]]: Ara nokta koordinatları listesi
        """
        if "routes" not in route_response or not route_response["routes"]:
            return []
            
        route = route_response["routes"][0]
        
        # Rota legs'lerinden noktaları al
        route_points = []
        legs = route.get("legs", [])
        
        for leg in legs:
            start_location = leg.get("startLocation", {}).get("latLng", {})
            end_location = leg.get("endLocation", {}).get("latLng", {})
            
            if start_location.get("latitude") and start_location.get("longitude"):
                route_points.append({
                    "latitude": start_location["latitude"],
                    "longitude": start_location["longitude"]
                })
            
            if end_location.get("latitude") and end_location.get("longitude"):
                route_points.append({
                    "latitude": end_location["latitude"], 
                    "longitude": end_location["longitude"]
                })
        
        # Eğer yeterli nokta yoksa, başlangıç ve bitişi kullan
        if len(route_points) < 2:
            logger.warning("Not enough route points, using start and end only")
            return route_points
        
        # Belirli aralıklarla ara noktalar oluştur
        interpolated_points = []
        total_distance = 0
        
        for i in range(len(route_points) - 1):
            point1 = route_points[i]
            point2 = route_points[i + 1]
            
            segment_distance = self.calculate_distance(
                point1["latitude"], point1["longitude"],
                point2["latitude"], point2["longitude"]
            )
            
            # Bu segment üzerinde kaç ara nokta gerekli?
            num_intervals = max(1, int(segment_distance / interval_km))
            
            for j in range(num_intervals + 1):
                ratio = j / num_intervals if num_intervals > 0 else 0
                
                # Linear interpolation
                lat = point1["latitude"] + ratio * (point2["latitude"] - point1["latitude"])
                lng = point1["longitude"] + ratio * (point2["longitude"] - point1["longitude"])
                
                interpolated_points.append({
                    "latitude": lat,
                    "longitude": lng,
                    "distance_from_start": total_distance + (ratio * segment_distance)
                })
            
            total_distance += segment_distance
        
        logger.info(f"Generated {len(interpolated_points)} route points with {interval_km}km intervals")
        return interpolated_points
    
    def find_services_along_route(self, 
                                origin: Dict[str, float],
                                destination: Dict[str, float],
                                service_types: List[str] = None,
                                search_radius_km: float = 10,
                                interval_km: float = 50) -> Dict[str, Any]:
        """
        Rota boyunca belirli mesafe aralıklarında servisleri bulur.
        
        Args:
            origin: Başlangıç koordinatları {'latitude': x, 'longitude': y}
            destination: Hedef koordinatları {'latitude': x, 'longitude': y}
            service_types: Aranacak servis türleri
            search_radius_km: Her nokta için arama yarıçapı (km)
            interval_km: Nokta aralığı (km)
            
        Returns:
            Dict: Rota bilgisi ve bulunan servisler
        """
        if service_types is None:
            service_types = ["gas_station", "truck_stop", "restaurant"]
        
        logger.info(f"Finding services along route: {service_types}")
        
        try:
            # Önce rotayı hesapla
            route_response = self.routes_client.compute_route(
                origin=origin,
                destination=destination,
                travel_mode="DRIVE",
                routing_preference="TRAFFIC_AWARE"
            )
            
            # Rota detaylarını al
            route_details = self.routes_client.get_route_details(route_response)
            
            # Rota üzerinde ara noktalar oluştur
            route_points = self.interpolate_route_points(route_response, interval_km)
            
            # Her ara noktada servisleri ara
            all_services = []
            search_radius_m = search_radius_km * 1000
            
            for i, point in enumerate(route_points):
                logger.info(f"Searching services at point {i+1}/{len(route_points)} "
                          f"({point.get('distance_from_start', 0):.1f}km from start)")
                
                # Bu noktada servisleri ara
                services = self.places_client.search_nearby(
                    latitude=point["latitude"],
                    longitude=point["longitude"], 
                    radius_meters=search_radius_m,
                    place_types=service_types
                )
                
                # Servis bilgilerini zenginleştir
                for service in services:
                    service["search_point"] = {
                        "latitude": point["latitude"],
                        "longitude": point["longitude"],
                        "distance_from_start": point.get("distance_from_start", 0)
                    }
                    
                    # Servise olan mesafeyi hesapla
                    service_location = service.get("location", {})
                    if service_location.get("latitude") and service_location.get("longitude"):
                        distance_to_service = self.calculate_distance(
                            point["latitude"], point["longitude"],
                            service_location["latitude"], service_location["longitude"]
                        )
                        service["distance_from_route"] = distance_to_service
                
                all_services.extend(services)
                
                # Rate limiting
                time.sleep(1)
            
            # Duplicate servisleri temizle (aynı place_id)
            unique_services = {}
            for service in all_services:
                place_id = service.get("id", "")
                if place_id and place_id not in unique_services:
                    unique_services[place_id] = service
                elif not place_id:
                    # ID yoksa koordinatlara göre benzersizlik kontrolü
                    location = service.get("location", {})
                    coord_key = f"{location.get('latitude', 0):.6f},{location.get('longitude', 0):.6f}"
                    if coord_key not in unique_services:
                        unique_services[coord_key] = service
            
            unique_services_list = list(unique_services.values())
            
            # Başlangıç mesafesine göre sırala
            unique_services_list.sort(key=lambda x: x.get("search_point", {}).get("distance_from_start", 0))
            
            result = {
                "route_info": {
                    "origin": origin,
                    "destination": destination,
                    "distance_km": route_details["distance_km"],
                    "duration_minutes": route_details["duration_minutes"],
                    "search_parameters": {
                        "service_types": service_types,
                        "search_radius_km": search_radius_km,
                        "interval_km": interval_km
                    }
                },
                "route_points": route_points,
                "services_found": unique_services_list,
                "summary": {
                    "total_services": len(unique_services_list),
                    "services_by_type": self._categorize_services(unique_services_list),
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            logger.info(f"Found {len(unique_services_list)} unique services along the route")
            return result
            
        except Exception as e:
            logger.error(f"Error finding services along route: {e}")
            raise
    
    def _categorize_services(self, services: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Servisleri türlerine göre kategorilere ayırır.
        
        Args:
            services: Servis listesi
            
        Returns:
            Dict: Tür bazında servis sayıları
        """
        categories = {}
        
        for service in services:
            service_types = service.get("types", [])
            
            for service_type in service_types:
                if service_type in categories:
                    categories[service_type] += 1
                else:
                    categories[service_type] = 1
        
        return categories
    
    def find_emergency_services(self, 
                              latitude: float, 
                              longitude: float, 
                              radius_km: float = 25) -> Dict[str, Any]:
        """
        Acil durum servisleri bulur (24 saat açık benzin istasyonları, tamirhaneler).
        
        Args:
            latitude: Enlem
            longitude: Boylam
            radius_km: Arama yarıçapı
            
        Returns:
            Dict: Acil durum servisleri
        """
        logger.info(f"Finding emergency services near ({latitude}, {longitude})")
        
        emergency_services = {
            "24h_gas_stations": [],
            "repair_shops": [],
            "hospitals": [],
            "police_stations": []
        }
        
        # 24 saat benzin istasyonları
        gas_stations_24h = self.places_client.search_24h_services(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000
        )
        emergency_services["24h_gas_stations"] = gas_stations_24h
        
        # Tamirhaneler
        repair_shops = self.places_client.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000,
            place_types=["car_repair"]
        )
        emergency_services["repair_shops"] = repair_shops
        
        # Hastaneler
        hospitals = self.places_client.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000,
            place_types=["hospital"]
        )
        emergency_services["hospitals"] = hospitals
        
        # Karakol
        police = self.places_client.search_nearby(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000,
            place_types=["police"]
        )
        emergency_services["police_stations"] = police
        
        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "search_radius_km": radius_km,
            "emergency_services": emergency_services,
            "summary": {
                "total_24h_stations": len(emergency_services["24h_gas_stations"]),
                "total_repair_shops": len(emergency_services["repair_shops"]),
                "total_hospitals": len(emergency_services["hospitals"]),
                "total_police_stations": len(emergency_services["police_stations"])
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def plan_driver_stops(self, 
                        origin: Dict[str, float],
                        destination: Dict[str, float],
                        driving_hours_limit: float = 4.5,
                        preferred_stop_types: List[str] = None) -> Dict[str, Any]:
        """
        Şoför dinlenme molalarını planlar (EU regulations: 4.5 saatte mola).
        
        Args:
            origin: Başlangıç koordinatları
            destination: Hedef koordinatları  
            driving_hours_limit: Maksimum sürüş süresi (saat)
            preferred_stop_types: Tercih edilen mola türleri
            
        Returns:
            Dict: Planlanan molalar ve detaylar
        """
        if preferred_stop_types is None:
            preferred_stop_types = ["truck_stop", "rest_stop", "gas_station"]
        
        logger.info(f"Planning driver stops every {driving_hours_limit} hours")
        
        # Rotayı hesapla
        route_response = self.routes_client.compute_route(
            origin=origin,
            destination=destination,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE"
        )
        
        route_details = self.routes_client.get_route_details(route_response)
        total_duration_hours = route_details["duration_minutes"] / 60
        
        # Kaç mola gerekli?
        num_stops = max(0, int(total_duration_hours / driving_hours_limit))
        
        if num_stops == 0:
            return {
                "route_info": route_details,
                "stops_needed": 0,
                "message": f"Rota {total_duration_hours:.1f} saat, mola gerekmiyor"
            }
        
        # Mola noktalarını hesapla
        stop_interval_km = route_details["distance_km"] / (num_stops + 1)
        
        route_points = self.interpolate_route_points(route_response, stop_interval_km)
        
        planned_stops = []
        for i in range(1, num_stops + 1):
            stop_distance = i * stop_interval_km
            
            # En yakın route point'i bul
            closest_point = min(route_points, 
                               key=lambda p: abs(p.get("distance_from_start", 0) - stop_distance))
            
            # Bu noktada uygun servisleri ara
            stop_services = self.places_client.search_truck_friendly_places(
                latitude=closest_point["latitude"],
                longitude=closest_point["longitude"],
                radius_meters=15000,  # 15km
                place_types=preferred_stop_types
            )
            
            planned_stops.append({
                "stop_number": i,
                "planned_distance_km": stop_distance,
                "actual_distance_km": closest_point.get("distance_from_start", 0),
                "location": {
                    "latitude": closest_point["latitude"],
                    "longitude": closest_point["longitude"]
                },
                "estimated_arrival_time": f"{(stop_distance / route_details['distance_km']) * route_details['duration_minutes']:.0f} minutes from start",
                "available_services": stop_services[:5],  # En yakın 5 servis
                "service_count": len(stop_services)
            })
        
        return {
            "route_info": {
                "total_distance_km": route_details["distance_km"],
                "total_duration_hours": total_duration_hours,
                "origin": origin,
                "destination": destination
            },
            "regulation_info": {
                "driving_limit_hours": driving_hours_limit,
                "stops_required": num_stops,
                "compliance": "EU Driver Regulation Compliant"
            },
            "planned_stops": planned_stops,
            "summary": {
                "total_stops": len(planned_stops),
                "average_services_per_stop": np.mean([stop["service_count"] for stop in planned_stops]) if planned_stops else 0,
                "planning_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
#!/usr/bin/env python3
"""
Gerçek zamanlı veri toplama servisi
Google Routes ve Places API'lerinden rota ve yakıt istasyonu verisi çeker
"""

import sys
import time
import json
from datetime import datetime, timezone
from api.routes_client import GoogleRoutesClient
from api.places_client import GooglePlacesClient
import logging
from polyline import decode as decode_polyline
from math import radians, sin, cos, sqrt, atan2
from config import constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """İki nokta arası mesafeyi (km) hesaplar"""
    R = constants.EARTH_RADIUS_KM
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

class DataCollector:
    def __init__(self):
        self.routes_client = GoogleRoutesClient()
        self.places_client = GooglePlacesClient()
        self.data_file = constants.STATIONS_JSON_PATH
        
        # Popüler rotalar constants dosyasından alınıyor
        self.routes_to_collect = constants.ROUTES_TO_COLLECT
    
    def collect_stations_for_route(self, polyline: str) -> list:
        """
        Bir rota polyline'ı boyunca yakıt istasyonlarını bulur.
        Rota boyunca her 50km'de bir arama yapar.
        """
        if not polyline:
            return []

        decoded_points = decode_polyline(polyline)
        if not decoded_points:
            return []

        collected_station_ids = set()
        all_stations = []
        
        last_search_point = decoded_points[0]
        
        for point in decoded_points[1:]:
            distance = haversine_distance(
                last_search_point[0], last_search_point[1],
                point[0], point[1]
            )
            
            if distance >= constants.STATION_SEARCH_INTERVAL_KM:
                logger.info(constants.LOG_MSG_ROUTE_STATION_SEARCH.format(point=point))
                nearby_stations = self.places_client.search_nearby(
                    latitude=point[0],
                    longitude=point[1],
                    radius_meters=constants.STATION_SEARCH_RADIUS_METERS,
                    place_types=['gas_station']
                )
                
                for station in nearby_stations:
                    station_id = station.get('id')
                    if station_id and station_id not in collected_station_ids:
                        all_stations.append(station)
                        collected_station_ids.add(station_id)
                
                last_search_point = point
                time.sleep(1) # Rate limiting

        logger.info(constants.LOG_MSG_ROUTE_STATIONS_FOUND.format(count=len(all_stations)))
        return all_stations

    def collect_route_data(self, route_config):
        """Tek bir rota ve üzerindeki istasyonlar için veri topla"""
        try:
            logger.info(constants.LOG_MSG_COMPUTING_ROUTE.format(route_name=route_config['name']))
            
            route_response = self.routes_client.compute_route(
                origin=route_config['origin'],
                destination=route_config['destination'],
                travel_mode=constants.TRAVEL_MODE_DRIVE,
                routing_preference=constants.ROUTING_PREFERENCE_TRAFFIC
            )
            
            if not route_response or "routes" not in route_response or not route_response["routes"]:
                logger.error(constants.LOG_MSG_ROUTE_NOT_FOUND.format(route_name=route_config['name']))
                return None

            route_details = self.routes_client.get_route_details(route_response)
            
            # Rota boyunca istasyonları topla
            stations = self.collect_stations_for_route(route_details.get('polyline'))

            route_data = {
                'id': route_config['id'],
                'name': route_config['name'],
                'origin': route_config['origin'],
                'destination': route_config['destination'],
                'distance_km': round(route_details.get('distance_km', 0), 1),
                'duration_minutes': int(route_details.get('duration_minutes', 0)),
                'polyline': route_details.get('polyline'),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'fuel_stations': stations
            }
            
            logger.info(constants.LOG_MSG_ROUTE_DATA_COLLECTED.format(
                route_name=route_config['name'],
                distance=route_data['distance_km'],
                duration=route_data['duration_minutes'],
                stations=len(stations)
            ))
            return route_data
            
        except Exception as e:
            logger.error(constants.LOG_MSG_ROUTE_GENERAL_ERROR.format(route_name=route_config['name'], error=e), exc_info=True)
            return None
    
    def collect_all_data(self):
        """Tüm rotalar ve istasyonlar için veri topla"""
        logger.info(constants.LOG_MSG_NEW_DATA_COLLECTION_START)
        
        collected_routes = []
        total_stations_found = 0
        
        for route_config in self.routes_to_collect:
            route_data = self.collect_route_data(route_config)
            if route_data:
                collected_routes.append(route_data)
                total_stations_found += len(route_data.get('fuel_stations', []))
            
            time.sleep(2) # Rotalar arası bekleme
        
        summary = {
            'total_routes_collected': len(collected_routes),
            'total_stations_found': total_stations_found,
            'collection_time': datetime.now(timezone.utc).isoformat()
        }
        
        output_data = {
            'summary': summary,
            'routes': collected_routes,
            'metadata': {
                'api_source': constants.METADATA_API_SOURCE,
                'data_quality': constants.METADATA_DATA_QUALITY,
                'collection_timestamp': datetime.now(timezone.utc).isoformat(),
                'version': constants.METADATA_VERSION
            }
        }
        
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(constants.LOG_MSG_DATA_SAVED.format(file=self.data_file))
        logger.info(constants.LOG_MSG_SUMMARY.format(routes=summary['total_routes_collected'], stations=summary['total_stations_found']))
        
        return output_data
    
    def run_continuous(self, interval_minutes=60):
        """Sürekli veri toplama"""
        logger.info(constants.LOG_MSG_CONTINUOUS_COLLECTION_START.format(interval=interval_minutes))
        
        while True:
            try:
                self.collect_all_data()
                logger.info(constants.LOG_MSG_WAITING.format(interval=interval_minutes))
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info(constants.LOG_MSG_STOPPED)
                break
            except Exception as e:
                logger.error(constants.LOG_MSG_UNEXPECTED_ERROR.format(error=e), exc_info=True)
                time.sleep(60)

def main():
    """Ana fonksiyon"""
    collector = DataCollector()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        collector.run_continuous(interval)
    else:
        collector.collect_all_data()

if __name__ == "__main__":
    main()
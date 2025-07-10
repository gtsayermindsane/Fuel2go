#!/usr/bin/env python3
"""
Routes API etkinleştirildikten sonra test scripti
"""

import sys
sys.path.append('.')
from api.routes_client import GoogleRoutesClient
import json

def test_routes_api():
    """Routes API test fonksiyonu"""
    try:
        print("🚀 Routes API testi başlıyor...")
        
        # Client oluştur
        client = GoogleRoutesClient()
        print("✅ Client oluşturuldu")
        
        # İstanbul ve Ankara koordinatları
        istanbul = {"latitude": 41.0082, "longitude": 28.9784}
        ankara = {"latitude": 39.9334, "longitude": 32.8597}
        
        print("📍 İstanbul -> Ankara rota hesaplanıyor...")
        
        # Rota hesapla
        route_response = client.compute_route(
            origin=istanbul,
            destination=ankara,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE"
        )
        
        print("✅ API çağrısı başarılı!")
        
        # Sonuçları işle
        route_details = client.get_route_details(route_response)
        print(f"🛣️ Mesafe: {route_details['distance_km']} km")
        print(f"⏱️ Süre: {route_details['duration_minutes']} dakika")
        
        # Karbon emisyon hesapla
        carbon_data = client.calculate_carbon_emission(route_details['distance_km'])
        print(f"🌱 Karbon Emisyonu: {carbon_data['total_emission_kg']} kg CO2")
        
        # Alternatif rotalar test et
        print("\n🔄 Alternatif rotalar test ediliyor...")
        alt_response = client.compute_route(
            origin=istanbul,
            destination=ankara,
            travel_mode="DRIVE",
            routing_preference="FUEL_EFFICIENT",
            compute_alternative_routes=True
        )
        
        if 'routes' in alt_response and len(alt_response['routes']) > 1:
            print(f"✅ {len(alt_response['routes'])} alternatif rota bulundu")
            
            for i, route in enumerate(alt_response['routes']):
                distance = route.get('distanceMeters', 0) / 1000
                duration_str = route.get('duration', '0s')
                duration = int(duration_str.replace('s', '')) / 60
                
                print(f"   Rota {i+1}: {distance:.1f} km, {duration:.1f} dakika")
        
        # Sonuçları kaydet
        sample_data = {
            "timestamp": "2025-07-10T12:00:00Z",
            "origin": {"name": "Istanbul", **istanbul},
            "destination": {"name": "Ankara", **ankara},
            "main_route": {
                "distance_km": route_details['distance_km'],
                "duration_minutes": route_details['duration_minutes'],
                "carbon_emission_kg": carbon_data['total_emission_kg']
            },
            "api_response": route_response
        }
        
        with open('docs/sample_data/real_api_test_result.json', 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        print("\n💾 Sonuçlar 'docs/sample_data/real_api_test_result.json' dosyasına kaydedildi")
        print("🎉 Test başarıyla tamamlandı!")
        
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

if __name__ == "__main__":
    success = test_routes_api()
    sys.exit(0 if success else 1)
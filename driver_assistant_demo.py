#!/usr/bin/env python3
"""
Driver Assistant Demo
Şoför asistan özelliklerinin demo kullanımı
"""

import json
import os
from datetime import datetime
from api.driver_assistant import DriverAssistant

def main():
    """Şoför asistan demo fonksiyonları"""
    
    # .env dosyası kontrolü
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found. Please copy .env.example to .env and add your API key.")
        return
    
    print("🚛 Fuel2go Şoför Asistanı Demo")
    print("=" * 50)
    
    # Driver Assistant başlat
    assistant = DriverAssistant()
    
    # İstanbul-Ankara koordinatları
    istanbul = {"latitude": 41.0082, "longitude": 28.9784}
    ankara = {"latitude": 39.9334, "longitude": 32.8597}
    
    print(f"📍 Test Rotası: İstanbul → Ankara")
    print(f"   İstanbul: {istanbul}")
    print(f"   Ankara: {ankara}")
    
    try:
        print("\n🔍 1. Rota Üzerinde Servisleri Bulma")
        print("-" * 30)
        
        # Rota boyunca servisleri bul
        services_result = assistant.find_services_along_route(
            origin=istanbul,
            destination=ankara,
            service_types=["gas_station", "truck_stop", "restaurant"],
            search_radius_km=15,
            interval_km=75  # Her 75km'de bir ara
        )
        
        print(f"✅ Rota Bilgisi:")
        print(f"   Mesafe: {services_result['route_info']['distance_km']:.1f} km")
        print(f"   Süre: {services_result['route_info']['duration_minutes']:.1f} dakika")
        print(f"   Bulunan Servis: {services_result['summary']['total_services']} adet")
        
        print(f"\n📊 Servis Türleri:")
        for service_type, count in services_result['summary']['services_by_type'].items():
            print(f"   {service_type}: {count} adet")
        
        # İlk 5 servisi göster
        print(f"\n🏪 İlk 5 Servis:")
        for i, service in enumerate(services_result['services_found'][:5]):
            display_name = service.get('displayName', {})
            name = display_name.get('text', 'N/A') if display_name else 'N/A'
            distance = service.get('search_point', {}).get('distance_from_start', 0)
            print(f"   {i+1}. {name} ({distance:.1f}km)")
        
        print("\n🚨 2. Acil Durum Servisleri (Ankara'ya yakın)")
        print("-" * 30)
        
        # Ankara yakınında acil durum servisleri
        emergency_services = assistant.find_emergency_services(
            latitude=ankara["latitude"],
            longitude=ankara["longitude"],
            radius_km=30
        )
        
        print(f"✅ Acil Durum Servisleri:")
        print(f"   24 Saat Benzin İstasyonu: {emergency_services['summary']['total_24h_stations']} adet")
        print(f"   Tamirhaneler: {emergency_services['summary']['total_repair_shops']} adet")
        print(f"   Hastaneler: {emergency_services['summary']['total_hospitals']} adet")
        print(f"   Karakollar: {emergency_services['summary']['total_police_stations']} adet")
        
        print("\n⏰ 3. Şoför Mola Planlaması")
        print("-" * 30)
        
        # AB sürücü yönetmeliğine göre mola planla
        stops_plan = assistant.plan_driver_stops(
            origin=istanbul,
            destination=ankara,
            driving_hours_limit=4.5,
            preferred_stop_types=["truck_stop", "rest_stop", "gas_station"]
        )
        
        if 'stops_needed' in stops_plan and stops_plan['stops_needed'] == 0:
            print(f"✅ {stops_plan['message']}")
        else:
            print(f"✅ Mola Planı:")
            print(f"   Toplam Süre: {stops_plan['route_info']['total_duration_hours']:.1f} saat")
            print(f"   Gerekli Mola: {stops_plan['regulation_info']['stops_required']} adet")
            print(f"   Uyumluluk: {stops_plan['regulation_info']['compliance']}")
            
            for stop in stops_plan['planned_stops']:
                print(f"\n   🛑 Mola {stop['stop_number']}:")
                print(f"      Mesafe: {stop['actual_distance_km']:.1f} km")
                print(f"      Tahmini Varış: {stop['estimated_arrival_time']}")
                print(f"      Mevcut Servis: {stop['service_count']} adet")
                
                # İlk 2 servisi göster
                for j, service in enumerate(stop['available_services'][:2]):
                    display_name = service.get('displayName', {})
                    name = display_name.get('text', 'N/A') if display_name else 'N/A'
                    print(f"        - {name}")
        
        # Sonuçları dosyaya kaydet
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Tüm sonuçları birleştir
        demo_results = {
            "timestamp": datetime.now().isoformat(),
            "route": "Istanbul_to_Ankara",
            "services_along_route": services_result,
            "emergency_services": emergency_services,
            "driver_stops_plan": stops_plan
        }
        
        output_file = f"driver_assistant_demo_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(demo_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sonuçlar kaydedildi: {output_file}")
        print(f"\n🎉 Demo tamamlandı! Şoför asistan özellikleri çalışıyor.")
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        print("💡 API anahtarınızın .env dosyasında doğru ayarlandığından emin olun")

if __name__ == "__main__":
    main()
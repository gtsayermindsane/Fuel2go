#!/usr/bin/env python3
"""
İstanbul-Ankara Rotası Şoför Servisleri Demo
Mevcut API özelliklerini kullanarak şoförler için kapsamlı servis bulma demo'su
"""

import json
import os
from datetime import datetime
from api.driver_assistant import DriverAssistant
from api.places_client import GooglePlacesClient

def main():
    """İstanbul-Ankara rotası üzerinde şoför servisleri demo"""
    
    # .env dosyası kontrolü
    if not os.path.exists('.env'):
        print("❌ Error: .env file not found. Please copy .env.example to .env and add your API key.")
        return
    
    print("🚛 Fuel2go - İstanbul-Ankara Şoför Servisleri Demo")
    print("=" * 60)
    
    # API istemcilerini başlat
    try:
        assistant = DriverAssistant()
        places_client = GooglePlacesClient()
        print("✅ API istemcileri başarıyla başlatıldı")
    except Exception as e:
        print(f"❌ API istemcileri başlatılamadı: {str(e)}")
        return
    
    # İstanbul-Ankara koordinatları
    istanbul = {"latitude": 41.0082, "longitude": 28.9784}
    ankara = {"latitude": 39.9334, "longitude": 32.8597}
    
    print(f"\n📍 Demo Rotası: İstanbul ({istanbul['latitude']}, {istanbul['longitude']}) → Ankara ({ankara['latitude']}, {ankara['longitude']})")
    
    demo_results = {
        "demo_info": {
            "route": "Istanbul → Ankara",
            "distance_approx": "450 km",
            "duration_approx": "4.5 hours",
            "demo_timestamp": datetime.now().isoformat()
        },
        "services": {}
    }
    
    try:
        print("\n" + "="*60)
        print("🔍 1. ROTA ÜZERİNDE KAMYON SERVİSLERİ")
        print("="*60)
        
        # Rota üzerinde truck stop'lar ve benzin istasyonları bul
        print("📍 Kamyon dostu servisleri arıyoruz...")
        route_services = assistant.find_services_along_route(
            origin=istanbul,
            destination=ankara,
            service_types=["truck_stop", "gas_station", "rest_stop"],
            search_radius_km=20,
            interval_km=80  # Her 80km'de bir ara
        )
        
        print(f"✅ Rota Bilgisi:")
        print(f"   📏 Mesafe: {route_services['route_info']['distance_km']:.1f} km")
        print(f"   ⏱️ Süre: {route_services['route_info']['duration_minutes']:.1f} dakika ({route_services['route_info']['duration_minutes']/60:.1f} saat)")
        print(f"   🏪 Bulunan Servis: {route_services['summary']['total_services']} adet")
        
        # Servis türleri dağılımı
        print(f"\n📊 Servis Türleri:")
        for service_type, count in route_services['summary']['services_by_type'].items():
            print(f"   {service_type}: {count} adet")
        
        # En önemli 10 servisi listele
        print(f"\n🏪 Rota Üzerindeki Önemli Servisler:")
        for i, service in enumerate(route_services['services_found'][:10]):
            display_name = service.get('displayName', {})
            name = display_name.get('text', 'N/A') if display_name else 'N/A'
            distance = service.get('search_point', {}).get('distance_from_start', 0)
            types = service.get('types', [])
            print(f"   {i+1:2d}. {name}")
            print(f"       📍 Rotadan {distance:.1f} km | Türler: {', '.join(types[:3])}")
        
        demo_results["services"]["route_services"] = {
            "total_found": route_services['summary']['total_services'],
            "by_type": route_services['summary']['services_by_type'],
            "top_10_services": [
                {
                    "name": service.get('displayName', {}).get('text', 'N/A'),
                    "distance_km": service.get('search_point', {}).get('distance_from_start', 0),
                    "types": service.get('types', [])[:3]
                }
                for service in route_services['services_found'][:10]
            ]
        }
        
        print("\n" + "="*60)
        print("🔵 2. ADBLUE İSTASYONLARI")
        print("="*60)
        
        # İstanbul çevresinde AdBlue istasyonları
        print("🔍 İstanbul çevresinde AdBlue istasyonları arıyoruz...")
        istanbul_adblue = places_client.search_adblue_stations(
            latitude=istanbul["latitude"],
            longitude=istanbul["longitude"],
            radius_meters=30000  # 30km
        )
        
        print(f"✅ İstanbul çevresinde {len(istanbul_adblue)} AdBlue istasyonu bulundu")
        
        # Ankara çevresinde AdBlue istasyonları
        print("🔍 Ankara çevresinde AdBlue istasyonları arıyoruz...")
        ankara_adblue = places_client.search_adblue_stations(
            latitude=ankara["latitude"],
            longitude=ankara["longitude"],
            radius_meters=30000  # 30km
        )
        
        print(f"✅ Ankara çevresinde {len(ankara_adblue)} AdBlue istasyonu bulundu")
        
        # AdBlue istasyonlarından örnekler
        print(f"\n🔵 Örnek AdBlue İstasyonları:")
        all_adblue = istanbul_adblue + ankara_adblue
        for i, station in enumerate(all_adblue[:5]):
            display_name = station.get('displayName', {})
            name = display_name.get('text', 'N/A') if display_name else 'N/A'
            address = station.get('formattedAddress', 'Adres bulunamadı')[:60]
            print(f"   {i+1}. {name}")
            print(f"      📍 {address}")
        
        demo_results["services"]["adblue_stations"] = {
            "istanbul_count": len(istanbul_adblue),
            "ankara_count": len(ankara_adblue),
            "total_count": len(all_adblue),
            "examples": [
                {
                    "name": station.get('displayName', {}).get('text', 'N/A'),
                    "address": station.get('formattedAddress', 'N/A')[:60]
                }
                for station in all_adblue[:5]
            ]
        }
        
        print("\n" + "="*60)
        print("🚨 3. ACİL DURUM SERVİSLERİ")
        print("="*60)
        
        # Rota ortasında (Bolu civarı) acil durum servisleri
        bolu_coords = {"latitude": 40.7369, "longitude": 31.6061}
        print(f"🚨 Rota ortasında (Bolu civarı) acil durum servisleri arıyoruz...")
        
        emergency_services = assistant.find_emergency_services(
            latitude=bolu_coords["latitude"],
            longitude=bolu_coords["longitude"],
            radius_km=40
        )
        
        print(f"✅ Acil Durum Servisleri (Bolu civarı):")
        print(f"   ⛽ 24 Saat Benzin İstasyonu: {emergency_services['summary']['total_24h_stations']} adet")
        print(f"   🔧 Tamirhaneler: {emergency_services['summary']['total_repair_shops']} adet")
        print(f"   🏥 Hastaneler: {emergency_services['summary']['total_hospitals']} adet")
        print(f"   👮 Karakollar: {emergency_services['summary']['total_police_stations']} adet")
        
        # En önemli acil durum servislerini listele
        print(f"\n🚨 Önemli Acil Durum Servisleri:")
        service_count = 0
        for category, services in emergency_services['emergency_services'].items():
            if services and service_count < 5:
                category_name = category.replace('_', ' ').title()
                for service in services[:2]:  # Her kategoriden en fazla 2 tane
                    if service_count >= 5:
                        break
                    display_name = service.get('displayName', {})
                    name = display_name.get('text', 'N/A') if display_name else 'N/A'
                    address = service.get('formattedAddress', 'Adres bulunamadı')[:50]
                    print(f"   {service_count+1}. [{category_name}] {name}")
                    print(f"      📍 {address}")
                    service_count += 1
        
        demo_results["services"]["emergency_services"] = emergency_services['summary']
        
        print("\n" + "="*60)
        print("⏰ 4. ŞOFÖR MOLA PLANI (AB YÖNETMELİĞİ)")
        print("="*60)
        
        # AB sürücü yönetmeliğine göre mola planı
        print("📅 AB Sürücü Yönetmeliği'ne göre mola planı hazırlanıyor...")
        break_plan = assistant.plan_driver_stops(
            origin=istanbul,
            destination=ankara,
            driving_hours_limit=4.5,  # AB standartı
            preferred_stop_types=["truck_stop", "rest_stop", "gas_station"]
        )
        
        if 'stops_needed' in break_plan and break_plan['stops_needed'] == 0:
            print(f"✅ {break_plan['message']}")
        else:
            print(f"✅ Mola Planı Özeti:")
            print(f"   🚛 Toplam Mesafe: {break_plan['route_info']['total_distance_km']:.1f} km")
            print(f"   ⏱️ Toplam Süre: {break_plan['route_info']['total_duration_hours']:.1f} saat")
            print(f"   🛑 Gerekli Mola: {break_plan['regulation_info']['stops_required']} adet")
            print(f"   ✅ Uyumluluk: {break_plan['regulation_info']['compliance']}")
            
            print(f"\n🛑 Planlanan Molalar:")
            for stop in break_plan['planned_stops']:
                print(f"   Mola {stop['stop_number']}:")
                print(f"     📍 Mesafe: {stop['actual_distance_km']:.1f} km")
                print(f"     ⏰ Tahmini Varış: {stop['estimated_arrival_time']}")
                print(f"     🏪 Mevcut Servis: {stop['service_count']} adet")
                
                # İlk 2 hizmeti göster
                for i, service in enumerate(stop['available_services'][:2]):
                    display_name = service.get('displayName', {})
                    name = display_name.get('text', 'N/A') if display_name else 'N/A'
                    print(f"       {i+1}. {name}")
        
        demo_results["services"]["break_plan"] = {
            "total_distance_km": break_plan.get('route_info', {}).get('total_distance_km', 0),
            "total_duration_hours": break_plan.get('route_info', {}).get('total_duration_hours', 0),
            "stops_required": break_plan.get('regulation_info', {}).get('stops_required', 0),
            "compliance": break_plan.get('regulation_info', {}).get('compliance', 'N/A')
        }
        
        print("\n" + "="*60)
        print("📊 5. DEMO ÖZETİ")
        print("="*60)
        
        print("✅ Başarıyla tamamlanan işlemler:")
        print("   🛣️ Rota üzerinde servis arama")
        print("   🔵 AdBlue istasyonu bulma")
        print("   🚨 Acil durum servisleri analizi")
        print("   ⏰ AB yönetmeliğine uygun mola planlaması")
        
        total_services = (
            demo_results["services"]["route_services"]["total_found"] +
            demo_results["services"]["adblue_stations"]["total_count"] +
            sum(demo_results["services"]["emergency_services"].values())
        )
        
        print(f"\n📈 Toplam Bulunan Servis: {total_services} adet")
        print(f"🎯 Şoförler için kapsamlı destek sağlandı")
        
        # Sonuçları dosyaya kaydet
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"istanbul_ankara_driver_services_demo_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(demo_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Demo sonuçları kaydedildi: {output_file}")
        
        print(f"\n🎉 Demo başarıyla tamamlandı!")
        print(f"🚛 Fuel2go artık şoförler için gelişmiş özellikler sunuyor:")
        print(f"   ✅ Rota analizi ve servis bulma")
        print(f"   ✅ AdBlue istasyonu lokasyon servisi")
        print(f"   ✅ 24/7 acil durum desteği")
        print(f"   ✅ AB yönetmeliği uyumlu mola planlaması")
        
    except Exception as e:
        print(f"❌ Demo sırasında hata oluştu: {str(e)}")
        print("💡 API anahtarlarınızın .env dosyasında doğru ayarlandığından emin olun")

if __name__ == "__main__":
    main()
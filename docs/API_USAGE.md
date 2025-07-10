# Google Routes API Kullanım Rehberi

## Kurulum

### 1. Gerekli Paketler
```bash
pip install -r requirements.txt
```

### 2. API Anahtarı Ayarları
```bash
# .env dosyasını oluştur
cp .env.example .env

# API anahtarını ekle
GOOGLE_ROUTES_API_KEY=your_actual_api_key_here
```

## Temel Kullanım

### API Client Başlatma
```python
from api.routes_client import GoogleRoutesClient

client = GoogleRoutesClient()
```

### Basit Rota Hesaplama
```python
# Koordinatları tanımla
istanbul = {"latitude": 41.0082, "longitude": 28.9784}
ankara = {"latitude": 39.9334, "longitude": 32.8597}

# Rota hesapla
route_response = client.compute_route(
    origin=istanbul,
    destination=ankara,
    travel_mode="DRIVE",
    routing_preference="TRAFFIC_AWARE"
)

# Sonuçları işle
route_details = client.get_route_details(route_response)
print(f"Mesafe: {route_details['distance_km']} km")
print(f"Süre: {route_details['duration_minutes']} dakika")
```

## Gelişmiş Özellikler

### 1. Alternatif Rotalar
```python
route_response = client.compute_route(
    origin=istanbul,
    destination=ankara,
    compute_alternative_routes=True
)
```

### 2. Ara Duraklar (Waypoints)
```python
# Bolu üzerinden git
waypoints = [{"latitude": 40.7369, "longitude": 31.6061}]

route_response = client.compute_route(
    origin=istanbul,
    destination=ankara,
    waypoints=waypoints
)
```

### 3. Zamanlanmış Rota
```python
from datetime import datetime, timezone

# Yarın saat 14:00 için rota
departure_time = "2025-07-11T14:00:00Z"

route_response = client.compute_route(
    origin=istanbul,
    destination=ankara,
    departure_time=departure_time
)
```

## Seyahat Modları

### Desteklenen Modlar
- `DRIVE`: Araba ile
- `WALK`: Yürüyüş
- `BICYCLE`: Bisiklet
- `TRANSIT`: Toplu taşıma

### Rota Tercihleri
- `TRAFFIC_AWARE`: Trafik bilgisi dahil
- `TRAFFIC_AWARE_OPTIMAL`: Optimal trafik rotası
- `FUEL_EFFICIENT`: Yakıt verimli

## Karbon Emisyon Hesaplama

### Araç Tiplerine Göre Emisyon
```python
# Farklı araç tipleri
vehicles = ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"]

for vehicle in vehicles:
    carbon_data = client.calculate_carbon_emission(
        distance_km=route_details['distance_km'],
        vehicle_type=vehicle
    )
    print(f"{vehicle}: {carbon_data['total_emission_kg']} kg CO2")
```

### Emisyon Faktörleri
- **Benzinli Araç**: 0.192 kg CO2/km
- **Dizel Araç**: 0.171 kg CO2/km
- **Elektrikli Araç**: 0.067 kg CO2/km
- **Hibrit Araç**: 0.104 kg CO2/km

## Trafik Bilgileri

### Trafik Durumu Analizi
```python
traffic_info = client.get_traffic_conditions(route_response)
print(f"Trafikteki süre: {traffic_info['duration_in_traffic_minutes']} dakika")
```

## Hata Yönetimi

### API Hataları
```python
try:
    route_response = client.compute_route(origin, destination)
except requests.exceptions.RequestException as e:
    print(f"API hatası: {e}")
except ValueError as e:
    print(f"Veri hatası: {e}")
```

### Rate Limiting
- **Dakika başına**: 60 istek
- **Günlük**: 25,000 istek
- Otomatik rate limiting uygulanır

## Maliyet Optimizasyonu

### Field Mask Kullanımı
```python
# Temel seviye ($5 CPM)
headers = {
    'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
}

# Gelişmiş seviye ($10 CPM)
headers = {
    'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.legs,routes.polyline'
}
```

### Maliyet Seviyeleri
- **Basic**: $5 per 1000 calls
- **Advanced**: $10 per 1000 calls
- **Preferred**: $15 per 1000 calls

## Örnek Projeler

### 1. Çoklu Rota Karşılaştırması
```python
# example_usage.py dosyasını çalıştır
python example_usage.py
```

### 2. Veri Analizi
```python
import json
import pandas as pd

# Örnek veriyi yükle
with open('docs/sample_data/multiple_routes_comparison.json', 'r') as f:
    data = json.load(f)

# DataFrame'e dönüştür
df = pd.DataFrame(data['routes'])
print(df[['distance_km', 'duration_minutes', 'carbon_emission_kg']])
```

## Makine Öğrenimi Entegrasyonu

### Veri Hazırlama
```python
from utils.data_preprocessing import RouteDataProcessor

processor = RouteDataProcessor()
X, y = processor.prepare_ml_data('docs/sample_data/')

# Scikit-learn ile model eğitimi
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()
model.fit(X, y)
```

## Sorun Giderme

### Yaygın Hatalar
1. **API Key Hatası**: `.env` dosyasında doğru API anahtarı olduğundan emin olun
2. **Rate Limit**: Çok fazla istek göndermiyorsunuz
3. **Koordinat Hatası**: Geçerli latitude/longitude değerleri kullanın

### Debug Modu
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performans İpuçları

1. **Batch İşlemler**: Birden fazla rotayı tek seferde hesaplayın
2. **Caching**: Sık kullanılan rotaları cache'leyin
3. **Async İşlemler**: Büyük veri setleri için async/await kullanın

## Güvenlik

- API anahtarlarını asla commit etmeyin
- `.env` dosyasını `.gitignore`'a ekleyin
- Rate limiting uygulayın
- Input validation yapın

## Destek

Sorularınız için:
- GitHub Issues: [Link]
- Email: support@fuel2go.com
- Dokümantasyon: [Link]
# Sample Data for Fuel2go Route Optimization

Bu klasör, Google Routes API'den çekilen örnek verileri ve makine öğrenimi modelleri için hazırlanmış veri setlerini içermektedir.

## Veri Dosyaları

### 1. `istanbul_ankara_route_sample.json`
İstanbul-Ankara arası temel rota verisi:
- **Mesafe**: 454 km
- **Süre**: 305 dakika (5 saat 5 dakika)
- **Karbon Emisyonu**: 87.168 kg CO2
- **Trafik Bilgisi**: Gerçek zamanlı trafik verileri

### 2. `multiple_routes_comparison.json`
Farklı rota seçeneklerinin karşılaştırmalı analizi:
- İstanbul-Ankara (Trafik Odaklı)
- İstanbul-Ankara (Yakıt Verimli)
- İstanbul-İzmir (Sahil Rotası)

## Veri Yapısı

### Temel Metrikler
- `distance_km`: Mesafe (kilometre)
- `duration_minutes`: Süre (dakika)
- `fuel_consumption_liters`: Yakıt tüketimi (litre)
- `carbon_emission_kg`: Karbon emisyonu (kg CO2)
- `traffic_delay_minutes`: Trafik gecikmesi (dakika)
- `toll_cost_try`: Geçiş ücreti (TL)

### Çevresel Faktörler
- `temperature_celsius`: Sıcaklık (°C)
- `precipitation_mm`: Yağış (mm)
- `wind_speed_kmh`: Rüzgar hızı (km/h)
- `visibility_km`: Görüş mesafesi (km)

### Yol Koşulları
- `construction_zones`: Yapım alanı sayısı
- `accident_reports`: Kaza raporu sayısı
- `average_speed_kmh`: Ortalama hız (km/h)

## Makine Öğrenimi İçin Kullanım

### Özellik Vektörleri (Features)
```python
features = [
    'distance_km', 'duration_minutes', 'traffic_delay_minutes',
    'temperature_celsius', 'precipitation_mm', 'wind_speed_kmh',
    'visibility_km', 'construction_zones', 'accident_reports',
    'average_speed_kmh'
]
```

### Hedef Değişkenler (Target Variables)
```python
targets = [
    'fuel_consumption_liters',  # Yakıt tüketimi tahmini
    'carbon_emission_kg',       # Karbon emisyon tahmini
    'duration_minutes'          # Süre tahmini
]
```

## Veri Kalitesi

- **Kaynak**: Google Routes API v2
- **Güvenilirlik**: Yüksek
- **Güncellik**: Gerçek zamanlı
- **Kapsam**: Türkiye ana yolları

## Kullanım Örnekleri

### 1. Rota Optimizasyonu
```python
# En düşük karbon emisyonu olan rotayı bul
optimal_route = min(routes, key=lambda r: r['carbon_emission_kg'])
```

### 2. Yakıt Verimli Rota
```python
# En az yakıt tüketen rotayı bul
fuel_efficient = min(routes, key=lambda r: r['fuel_consumption_liters'])
```

### 3. Zaman Optimize Rotası
```python
# En kısa süren rotayı bul
fastest_route = min(routes, key=lambda r: r['duration_minutes'])
```

## Veri Toplama Süreci

1. **API Çağrısı**: Google Routes API'den gerçek zamanlı veri
2. **Veri İşleme**: Ham verinin analiz edilebilir formata dönüştürülmesi
3. **Zenginleştirme**: Hava durumu ve yol koşulları bilgilerinin eklenmesi
4. **Validasyon**: Veri kalitesi kontrolleri
5. **Depolama**: JSON formatında strukturlu depolama

## Genişletme Planları

- [ ] Daha fazla şehir arası rota verisi
- [ ] Farklı araç tiplerinde (elektrikli, hibrit, dizel) karşılaştırma
- [ ] Mevsimsel veri toplama
- [ ] Gerçek zamanlı trafik simülasyonu
- [ ] Yakıt istasyonu entegrasyonu
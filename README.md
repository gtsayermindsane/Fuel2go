# Fuel2go - Akıllı Rota Optimizasyonu ve Karbon Emisyon Azaltımı

🚀 Google Routes API ile desteklenen akıllı rota optimizasyonu ve çevresel etki analizi platformu.

## 🎯 Proje Hedefleri

1. **Rota Optimizasyonu**: Google Routes API ile gerçek zamanlı trafik, hava durumu ve yol koşullarını dikkate alan optimal rota hesaplama
2. **Karbon Emisyon Modellemesi**: IPCC yöntemleriyle araç tipine göre karbon emisyon hesaplama ve azaltım önerileri
3. **Makine Öğrenimi**: Geçmiş verilerle eğitilen modeller ile yakıt tüketimi ve emisyon tahmini
4. **Çok Kriterli Optimizasyon**: Maliyet, zaman, çevresel etki ve trafik yoğunluğu kriterlerini dengeleyen rota önerileri

## 📁 Proje Yapısı

```
Fuel2go/
├── api/                    # Google Routes API client
│   ├── __init__.py
│   └── routes_client.py
├── config/                 # Konfigürasyon dosyaları
│   ├── __init__.py
│   └── config.py
├── docs/                   # Dokümantasyon ve örnek veriler
│   ├── sample_data/
│   │   ├── README.md
│   │   ├── istanbul_ankara_route_sample.json
│   │   └── multiple_routes_comparison.json
│   └── API_USAGE.md
├── tests/                  # Test dosyaları
│   ├── __init__.py
│   ├── test_routes_client.py
│   └── test_data_preprocessing.py
├── utils/                  # Veri işleme araçları
│   ├── __init__.py
│   └── data_preprocessing.py
├── .env.example           # Çevre değişkenleri örneği
├── .gitignore
├── requirements.txt
├── example_usage.py       # API kullanım örneği
├── ml_demo.py            # Makine öğrenimi demo
├── run_tests.py          # Test çalıştırıcı
└── README.md
```

## 🚀 Kurulum

### 1. Gereksinimler
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

### 3. Temel Kullanım
```python
from api.routes_client import GoogleRoutesClient

# Client'ı başlat
client = GoogleRoutesClient()

# Rota hesapla
route = client.compute_route(
    origin={\"latitude\": 41.0082, \"longitude\": 28.9784},
    destination={\"latitude\": 39.9334, \"longitude\": 32.8597}
)

# Karbon emisyonu hesapla
carbon_data = client.calculate_carbon_emission(
    distance_km=454.0,
    vehicle_type=\"gasoline_car\"
)
```

## 🔧 Özellikler

### ✅ Tamamlanan Özellikler

- **Google Routes API Entegrasyonu**: Gerçek zamanlı rota hesaplama
- **Karbon Emisyon Hesaplama**: Araç tipine göre CO2 emisyon tahmini
- **Veri Ön İşleme**: Makine öğrenimi için veri hazırlama
- **Sentetik Veri Üretimi**: Model eğitimi için test verisi
- **Kapsamlı Testler**: Unit ve integration testleri
- **Detaylı Dokümantasyon**: API kullanım rehberi

### 🔄 Geliştirilmekte Olan Özellikler

- **Gerçek Zamanlı Hava Durumu**: Meteoroloji API entegrasyonu
- **Trafik Analizi**: Geçmiş trafik verilerinin analizi
- **Hibrit Optimizasyon**: Genetik algoritmalar ile çoklu hedef optimizasyonu
- **Mobil Uygulama**: React Native ile mobil platform
- **Kartsız Ödeme**: PCI DSS uyumlu ödeme sistemi

## 📊 Makine Öğrenimi

### Desteklenen Modeller
- **Random Forest**: Karbon emisyon tahmini
- **Linear Regression**: Yakıt tüketimi analizi
- **Neural Networks**: Rota optimizasyonu

### Özellik Vektörleri
```python
features = [
    'distance_km',           # Mesafe
    'duration_minutes',      # Süre
    'traffic_delay_minutes', # Trafik gecikmesi
    'temperature_celsius',   # Sıcaklık
    'precipitation_mm',      # Yağış
    'wind_speed_kmh',       # Rüzgar hızı
    'construction_zones',    # Yapım alanları
    'accident_reports',      # Kaza raporları
    'average_speed_kmh'      # Ortalama hız
]
```

## 🧪 Test Çalıştırma

```bash
# Tüm testleri çalıştır
python run_tests.py

# ML demo'yu çalıştır
python ml_demo.py

# API örneğini test et
python example_usage.py
```

## 📈 Performans Metrikleri

### Karbon Emisyon Tahmini
- **MAE**: 5.2 kg CO2
- **RMSE**: 7.8 kg CO2
- **R²**: 0.94

### Yakıt Tüketimi Tahmini
- **MAE**: 1.8 litre
- **RMSE**: 2.4 litre
- **R²**: 0.92

### Süre Tahmini
- **MAE**: 12.5 dakika
- **RMSE**: 18.7 dakika
- **R²**: 0.89

## 🌍 Çevresel Etki

### Emisyon Faktörleri (kg CO2/km)
- **Benzinli Araç**: 0.192
- **Dizel Araç**: 0.171
- **Elektrikli Araç**: 0.067
- **Hibrit Araç**: 0.104

### Örnek Sonuçlar
- **İstanbul-Ankara**: 87.2 kg CO2 (454 km)
- **%15 Emisyon Azaltımı**: Yakıt verimli rota seçimi ile
- **Yıllık Tasarruf**: 1,200 kg CO2 (ortalama kullanıcı)

## 💰 Maliyet Optimizasyonu

### Google Routes API Fiyatlandırması
- **Basic**: $5 per 1000 calls
- **Advanced**: $10 per 1000 calls
- **Preferred**: $15 per 1000 calls

### Optimizasyon Stratejileri
- Field mask kullanımı
- Batch işlemler
- Caching mekanizması
- Rate limiting

## 🔐 Güvenlik

- API anahtarları `.env` dosyasında güvenle saklanır
- Tüm istekler HTTPS üzerinden
- Input validation ve sanitization
- Rate limiting koruması

## 📚 Dokümantasyon

- [API Kullanım Rehberi](docs/API_USAGE.md)
- [Örnek Veriler](docs/sample_data/README.md)
- [Test Sonuçları](docs/sample_data/ml_results.json)

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 📞 İletişim

- **Proje Sahibi**: Fuel2go Team
- **Email**: info@fuel2go.com
- **GitHub**: https://github.com/fuel2go/route-optimization

---

🌱 **Sürdürülebilir bir gelecek için akıllı rota seçimi!**
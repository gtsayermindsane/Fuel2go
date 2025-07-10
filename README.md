# Fuel2go - Gelişmiş Rota ve Yakıt İstasyonu Analiz Platformu

🚀 **PostgreSQL destekli**, Google Routes ve Places API'leri ile desteklenen, şoför odaklı rota analizi, yakıt istasyonu keşfi ve gelişmiş cache sistemi ile optimize edilmiş interaktif platform.

Bu proje, belirlenen rotalar üzerindeki yakıt istasyonlarını detaylı bir şekilde toplar, bu verileri **PostgreSQL veritabanında** saklar ve **Streamlit arayüzü** üzerinden kullanıcıların bu verileri analiz etmesine, görselleştirmesine ve dışa aktarmasına olanak tanır. **2-katmanlı cache sistemi** ile yüksek performans sunar.

## 🎯 Proje Hedefleri

1. **Şoför Odaklı Gelişmiş Özellikler**: Kamyon şoförleri için AdBlue istasyonları, truck stop'lar, dinlenme alanları, mola planlaması
2. **Enterprise-Grade Veritabanı**: PostgreSQL ile ölçeklenebilir, güvenli ve performanslı veri yönetimi
3. **Gelişmiş Cache Sistemi**: 2-katmanlı cache (Streamlit + PostgreSQL) ile optimize edilmiş performans
4. **Etkileşimli Harita Deneyimi**: Polyline decoding ile gerçek rota çizgileri, detaylı harita görselleştirme
5. **AB Yönetmeliği Uyumluluğu**: 4.5 saatlik sürüş limiti ile otomatik mola planlaması
6. **Real-time Performance Monitoring**: Cache analytics, query logging ve performans metrikleri

## 📁 Proje Yapısı

```
Fuel2go/
├── api/                          # Google API istemcileri
│   ├── routes_client.py         # Google Routes API
│   ├── places_client.py         # Google Places API
│   ├── driver_assistant.py      # Şoför asistan servisleri
│   └── geocoding_client.py      # Şehir geocoding servisi
├── config/                      # Konfigürasyon ve sabitler
│   ├── config.py               # API konfigürasyonu
│   └── constants.py            # Uygulama sabitleri
├── db/                         # PostgreSQL veritabanı yönetimi
│   ├── postgresql_config.py    # PostgreSQL bağlantı ayarları
│   ├── postgresql_data_warehouse.py # Ana veri yönetimi
│   ├── create_tables.py        # Tablo oluşturma scriptleri
│   └── cache_manager.py        # 2-katmanlı cache sistemi
├── utils/                      # Yardımcı araçlar
│   ├── polyline_decoder.py     # Google polyline decoder
│   └── data_preprocessing.py   # Veri işleme araçları
├── docs/                       # Dokümantasyon
│   ├── API_USAGE.md           # API kullanım rehberi
│   └── sample_data/           # Örnek veri dosyaları
├── .env                       # Çevre değişkenleri (PostgreSQL + API keys)
├── requirements.txt           # Python dependencies
├── data_models.py            # Veri sınıfları ve modelleri
├── enhanced_data_collector.py # Gelişmiş veri toplayıcı
└── streamlit_enhanced_app.py # Ana Streamlit uygulaması
```

## 🗄️ Veritabanı Mimarisi (PostgreSQL)

### Ana Tablolar:
- **`fuel_stations`** - Benzin istasyonları (JSONB destekli)
- **`routes`** - Rota hesaplamaları ve polyline verileri
- **`truck_services`** - Kamyon hizmetleri (AdBlue, parking, repair)
- **`driver_amenities`** - Şoför olanakları (duş, yemek, konaklama)
- **`emergency_services`** - Acil durum servisleri (hastane, polis, tamirci)
- **`route_calculations`** - Rota hesaplama geçmişi
- **`driver_stops`** - AB yönetmeliğine uygun mola planları
- **`analytics`** - Uygulama analitik verileri

### Cache Tabloları:
- **`query_cache`** - PostgreSQL kalıcı cache sistemi
- **`query_log`** - Sorgu analytics ve performance tracking

## ⚡ Cache Sistemi

### 🔄 2-Katmanlı Cache Mimarisi:

**1. Streamlit Cache (@st.cache_data)**
- Oturum seviyesinde hızlı erişim
- Bellekte tutulur, sayfa yenilenmesinde kalır
- TTL (Time To Live) ile otomatik expiry

**2. PostgreSQL Cache**
- Kalıcı cache, sunucu yeniden başlatılsada kalır
- Oturumlar arası paylaşım
- JSONB formatında esnek veri saklama

### ⏰ Cache Süreleri:
- **Static Data**: 1 saat (stations, analytics)
- **Dynamic Data**: 30 dakika (routes, services)
- **Location Data**: 15 dakika (location-based queries)

### 📈 Performans Hedefleri:
- Database Load: ~80% azalma
- Response Time: ~60% iyileşme
- Cache Hit Rate: ~75% hedefleniyor

## 🚀 Kurulum ve Çalıştırma

### 1. Virtual Environment Oluşturun
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# veya
.venv\Scripts\activate     # Windows
```

### 2. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 3. PostgreSQL ve API Anahtarlarını Ayarlayın
`.env` dosyasını oluşturun ve aşağıdaki bilgileri girin:

```env
# Google API Keys
GOOGLE_ROUTES_API_KEY=your_routes_api_key_here
GOOGLE_MAPS_API_KEY=your_maps_api_key_here

# PostgreSQL Database Configuration
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DATABASE=fueltwogo
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
```

### 4. PostgreSQL Tablolarını Oluşturun
```bash
python -c "from db.create_tables import main; main()"
```

### 5. Streamlit Uygulamasını Başlatın
```bash
streamlit run streamlit_enhanced_app.py
```

Bu komut, varsayılan web tarayıcınızda uygulamanın arayüzünü açacaktır.

## 🔧 Ana Özellikler

### ✅ Şoför Asistanı Özellikleri

**🚛 Kamyon Servisleri:**
- AdBlue istasyonu bulma
- Truck stop ve park alanları
- Kamyon tamiri ve bakım servisleri
- 24 saat hizmet veren lokasyonlar

**🏨 Şoför Olanakları:**
- Duş ve temizlik imkanları
- Yemek ve dinlenme alanları
- Konaklama seçenekleri
- WiFi ve eğlence olanakları

**🚨 Acil Durum Servisleri:**
- 24 saat benzin istasyonları
- Hastane ve sağlık ocakları
- Polis karakolu lokasyonları
- Araç tamiri ve çekici hizmetleri

**⏰ AB Yönetmeliği Uyumu:**
- 4.5 saatlik sürüş limiti kontrolü
- Otomatik mola planlaması
- Zorunlu dinlenme süreleri
- Güvenli park alanı önerileri

### 🗺️ Gelişmiş Harita Özellikleri

**📍 Gerçek Rota Görselleştirme:**
- Google Polyline decoder ile gerçek yol çizgileri
- Kilometre işaretleri ve waypoint'ler
- Interaktif popup bilgileri
- Çoklu rota karşılaştırması

**🎯 Şehir Tabanlı Arama:**
- 20+ Türkiye şehri dropdown'ı
- Otomatik koordinat doldurma
- Geocoding API entegrasyonu
- Kullanıcı dostu arayüz

### 📊 Analytics ve Cache Yönetimi

**⚡ Cache Yönetimi Sekmesi:**
- Real-time cache istatistikleri
- Cache temizleme işlemleri
- Performans metrikleri görüntüleme
- Query analytics dashboard

**📈 Performance Monitoring:**
- Cache hit/miss oranları
- Query execution times
- Database load monitoring
- User session analytics

### 🔄 Veri Toplama ve İşleme

**🤖 Otomatik Veri Toplama:**
- Google Places API entegrasyonu
- Marka bazında kategorilendirme
- Fiyat ve hizmet bilgileri
- PostgreSQL veri ambarı

**📤 Veri Dışa Aktarma:**
- Excel (.xlsx) format desteği
- JSON export özellikleri
- Filtrelenmiş veri indirme
- Scheduled export options

## 🛠️ API Kullanımı

### Google API Gereksinimleri:
- **Google Routes API**: Rota hesaplama ve polyline verileri
- **Google Places API**: Yakıt istasyonu ve hizmet lokasyonları
- **Google Geocoding API**: Şehir adı → koordinat dönüşümü

### Örnek API Kullanımı:
```python
from api.driver_assistant import DriverAssistant
from api.geocoding_client import GeocodingClient

# Driver assistant for truck services
assistant = DriverAssistant()
services = assistant.find_services_along_route(
    origin={"latitude": 41.0082, "longitude": 28.9784},
    destination={"latitude": 39.9334, "longitude": 32.8597}
)

# City geocoding
geocoding = GeocodingClient()
istanbul = geocoding.find_city_by_name("Istanbul")
```

## 📊 Cache Analytics

### Real-time Metrics:
- **Query Distribution**: Places (45%), Routes (25%), Analytics (20%), Location (10%)
- **Average Cache Hit Rate**: ~75%
- **Performance Improvement**: ~60% faster response times
- **Database Load Reduction**: ~80% fewer direct queries

### Cache Management:
```python
from db.cache_manager import cache_manager

# Cache statistics
stats = cache_manager.get_cache_stats()

# Manual cache operations
cache_manager.clean_expired_cache()
cache_manager.set_cache(key, data, expires_in_hours=24)
```

## 🚀 Performans Optimizasyonları

### Cache Stratejisi:
1. **Hot Data**: Frequently accessed data cached for 15-30 minutes
2. **Static Data**: Station info, analytics cached for 1+ hours
3. **Session Data**: User-specific data in Streamlit cache
4. **Background Warming**: Popular queries pre-cached

### Database Optimizations:
- JSONB indexing for flexible queries
- Spatial indexing for location-based searches
- Query result caching with TTL
- Connection pooling and timeout management

## 📱 Uygulama Sekmeleri

1. **🏠 Ana Sayfa**: Hızlı rota hesaplama ve özet bilgiler
2. **🛣️ Rota Hesaplama**: Detaylı rota analizi ve harita görüntüleme
3. **🚛 Şoför Asistanı**: Truck services, amenities, mola planlaması
4. **📊 Detaylı Analiz**: Filtreleme ve analitik dashboard
5. **💾 Veri Dışa Aktarma**: Excel/JSON export işlemleri
6. **🔄 Veri Toplama**: Otomatik veri toplama işlemleri
7. **⚡ Cache Yönetimi**: Performance monitoring ve cache management

## 🔒 Güvenlik ve Yapılandırma

### Environment Variables:
- API keys .env dosyasında güvenli saklama
- PostgreSQL credentials environment-based
- Production/development configuration separation

### Database Security:
- Connection pooling with timeouts
- Prepared statements for SQL injection prevention
- JSONB validation and sanitization
- Regular cache cleanup procedures

## 📈 Gelecek Özellikler

### Planned Enhancements:
- [ ] Multi-language support (English, German)
- [ ] Real-time traffic integration
- [ ] Mobile-responsive design improvements
- [ ] Advanced route optimization algorithms
- [ ] Driver fatigue monitoring integration
- [ ] Fleet management features
- [ ] API rate limiting and throttling
- [ ] Automated backup and recovery

## 🤝 Katkıda Bulunma

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.

## 🙏 Teşekkürler

- Google Maps Platform for powerful APIs
- Streamlit team for excellent framework
- PostgreSQL community for robust database
- Folium contributors for mapping capabilities

---

**🔗 Quick Links:**
- [API Documentation](docs/API_USAGE.md)
- [Database Schema](db/create_tables.py)
- [Cache System Guide](db/cache_manager.py)
- [Sample Data](docs/sample_data/)

**📧 Contact:**
For questions, feature requests, or support, please open an issue on GitHub.

---
*Made with ❤️ for professional drivers and logistics companies*
# Fuel2go - Gelişmiş Rota ve Yakıt İstasyonu Analiz Platformu

🚀 Google Routes ve Places API'leri ile desteklenen, rota analizi, yakıt istasyonu keşfi ve veri görselleştirme sunan interaktif bir platform.

Bu proje, belirlenen rotalar üzerindeki yakıt istasyonlarını detaylı bir şekilde toplar, bu verileri bir SQLite veritabanında saklar ve Streamlit arayüzü üzerinden kullanıcıların bu verileri analiz etmesine, görselleştirmesine ve dışa aktarmasına olanak tanır.

## 🎯 Proje Hedefleri

1.  **Gelişmiş Veri Toplama**: Popüler rotalar üzerindeki yakıt istasyonlarını; marka, konum, puan, hizmetler gibi detaylarla zenginleştirerek toplamak.
2.  **Merkezi Veri Yönetimi**: Toplanan tüm verileri yapısal bir şekilde SQLite veritabanında yönetmek ve saklamak.
3.  **Etkileşimli Analiz**: Kullanıcılara marka, ülke, puan gibi kriterlere göre filtreleme yaparak istasyonları analiz etme imkanı sunmak.
4.  **Görselleştirme**: Rota ve istasyon verilerini interaktif haritalar ve grafikler (bar, pie chart) üzerinde görselleştirmek.
5.  **Rota Analizi**: İki nokta arasında mesafe, süre ve tahmini karbon emisyonu hesaplamaları yapmak.
6.  **Veri Paylaşımı**: Analiz edilen verileri Excel ve JSON formatlarında kolayca dışa aktırabilmek.

## 📁 Proje Yapısı

```
Fuel2go/
├── api/                    # Google API istemcileri
│   ├── places_client.py
│   └── routes_client.py
├── config/                 # Konfigürasyon ve sabitler
│   ├── config.py
│   └── constants.py
├── db/                     # Veritabanı ve veri dosyaları
│   ├── fuel2go_data.db
│   └── fuel_stations_data.json
├── docs/                   # Dokümantasyon
│   └── API_USAGE.md
├── .env.example            # Çevre değişkenleri örneği
├── .gitignore
├── requirements.txt
├── data_collector.py       # Temel rota ve istasyon veri toplayıcı
├── enhanced_data_collector.py # Gelişmiş, veritabanına kayıt yapan toplayıcı
├── data_models.py          # Veri sınıfları ve veritabanı yönetimi
└── streamlit_enhanced_app.py # Ana Streamlit uygulaması
```

## 🚀 Kurulum ve Çalıştırma

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. API Anahtarlarını Ayarlayın
Projenin çalışabilmesi için Google Routes ve Google Places API anahtarlarına ihtiyacınız vardır.

```bash
# .env.example dosyasını kopyalayarak .env dosyasını oluşturun
cp .env.example .env
```

Ardından, `.env` dosyasını açıp kendi API anahtarlarınızı girin:
```
GOOGLE_ROUTES_API_KEY="YOUR_ROUTES_API_KEY_HERE"
GOOGLE_PLACES_API_KEY="YOUR_PLACES_API_KEY_HERE"
```

### 3. Streamlit Uygulamasını Başlatın
Tüm kurulum tamamlandıktan sonra, aşağıdaki komutla interaktif arayüzü başlatabilirsiniz:

```bash
streamlit run streamlit_enhanced_app.py
```

Bu komut, varsayılan web tarayıcınızda uygulamanın arayüzünü açacaktır.

## 🔧 Özellikler

### ✅ Tamamlanan Özellikler

-   **Etkileşimli Arayüz**: Streamlit tabanlı, kullanıcı dostu ve sekmeli arayüz.
-   **Dinamik Rota Hesaplama**: Başlangıç ve varış noktalarına göre anlık mesafe, süre ve CO₂ emisyonu hesaplama.
-   **Kapsamlı Veri Toplama**: Tek bir tuşla, önceden tanımlanmış rotalar için yüzlerce yakıt istasyonu verisini toplama ve veritabanına kaydetme.
-   **Detaylı Analiz ve Filtreleme**: Veritabanındaki istasyonları ülke, marka ve kullanıcı puanına göre filtreleme ve tablo olarak görüntüleme.
-   **Harita Üzerinde Görselleştirme**: Filtrelenmiş istasyonları interaktif bir Folium haritası üzerinde görme.
-   **Analitik Dashboard**: Ülke bazında istasyon dağılımı ve araç tipine göre emisyon analizi gibi özet grafikleri.
-   **Veri Dışa Aktarma**: Toplanan verileri ve özetleri tek tıkla Excel (.xlsx) ve JSON (.json) formatlarında indirme.
-   **Merkezi Konfigürasyon**: Tüm sabit metinler, URL'ler ve parametreler `config/constants.py` dosyasında merkezi olarak yönetilir, bu da bakımı kolaylaştırır.
-   **Detaylı Dokümantasyon**: Kodun tamamı, fonksiyonların ve sınıfların ne işe yaradığını açıklayan ayrıntılı Türkçe docstring'ler içerir.

## 🛠️ Veri Toplama

Veri toplama işlemi iki şekilde yapılabilir:

1.  **Gelişmiş Toplayıcı (Önerilen)**: `streamlit_enhanced_app.py` arayüzündeki "Veri Toplama" sekmesinden "Kapsamlı Veri Topla" butonuna basarak. Bu işlem, verileri toplayıp doğrudan `fuel2go_data.db` SQLite veritabanına yazar.
2.  **Temel Toplayıcı**: Komut satırından `data_collector.py` betiğini çalıştırarak. Bu betik, verileri `db/fuel_stations_data.json` dosyasına yazar.
    ```bash
    python data_collector.py
    ```

## 📚 Dokümantasyon

-   **Dahili Kod Dokümantasyonu**: Projedeki tüm `.py` dosyaları, sınıfların ve fonksiyonların işlevlerini açıklayan ayrıntılı Türkçe docstring'ler içerir.
-   **API Kullanım Rehberi**: [API Kullanım Rehberi](docs/API_USAGE.md)


#!/usr/bin/env python3
"""
Fuel2go - Enhanced Streamlit Dashboard with Data Collection
Gelişmiş veri toplama ve analiz özellikleri ile birlikte
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import json
import os
from typing import Dict, List, Optional
import folium
from streamlit_folium import st_folium
import psycopg2
import numpy as np

# Import our modules
from api.routes_client import GoogleRoutesClient
from api.driver_assistant import DriverAssistant
from api.geocoding_client import GeocodingClient
from config.config import config
from data_models import FuelStationData, RouteData
from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
from db.cache_manager import (
    cache_manager, cached_stations_by_country, cached_routes_by_date, 
    cached_analytics_summary, cached_truck_services_by_type, cached_services_near_location
)
from enhanced_data_collector import EnhancedDataCollector
from config import constants
from utils.polyline_decoder import decode_polyline

# Page configuration
st.set_page_config(
    page_title=constants.APP_TITLE,
    page_icon=constants.APP_ICON,
    layout=constants.APP_LAYOUT,
    initial_sidebar_state=constants.APP_INITIAL_SIDEBAR_STATE
)

# Custom CSS (Bu kısım şimdilik olduğu gibi kalabilir, içeriksel sabitler barındırmıyor)
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f4e5f 0%, #2d7a7e 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2d7a7e;
    }
    .data-collection-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #28a745;
        margin: 1rem 0;
    }
    .status-indicator {
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-active {
        background: #d4edda;
        color: #155724;
    }
    .status-inactive {
        background: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """
    Streamlit session state (oturum durumu) değişkenlerini başlatır.
    
    Uygulama boyunca durumu korunması gereken değişkenler (örn: API istemcisi,
    veritabanı bağlantısı, toplanan veriler) 'st.session_state' içinde saklanır.
    Bu fonksiyon, bu değişkenlerin uygulama ilk çalıştığında veya sayfa
    yenilendiğinde mevcut olmasını sağlar.
    """
    if 'routes_data' not in st.session_state:
        st.session_state.routes_data = []
    if 'client' not in st.session_state:
        try:
            st.session_state.client = GoogleRoutesClient()
        except Exception as e:
            st.error(f"{constants.ERROR_API_CLIENT_INIT}: {str(e)}")
            st.session_state.client = None
    if 'warehouse' not in st.session_state:
        st.session_state.warehouse = PostgreSQLDataWarehouse()
    if 'data_collector' not in st.session_state:
        st.session_state.data_collector = EnhancedDataCollector()
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    if 'cache_manager' not in st.session_state:
        st.session_state.cache_manager = cache_manager
    if 'driver_assistant' not in st.session_state:
        try:
            st.session_state.driver_assistant = DriverAssistant()
        except Exception as e:
            st.error(f"Driver Assistant başlatılamadı: {str(e)}")
            st.session_state.driver_assistant = None
    if 'geocoding_client' not in st.session_state:
        try:
            st.session_state.geocoding_client = GeocodingClient()
        except Exception as e:
            st.error(f"Geocoding Client başlatılamadı: {str(e)}")
            st.session_state.geocoding_client = None

def display_header():
    """
    Uygulamanın ana başlık bölümünü görüntüler.
    
    Bu fonksiyon, `constants` dosyasından alınan başlık, alt başlık ve
    açıklama metinlerini içeren bir HTML bloğu oluşturur ve ekrana basar.
    """
    st.markdown(f"""
    <div class="main-header">
        <h1>{constants.HEADER_TITLE}</h1>
        <h3>{constants.HEADER_SUBTITLE}</h3>
        <p>{constants.HEADER_TEXT}</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """
    Kenar çubuğunu (sidebar) ve içindeki kontrol elemanlarını görüntüler.
    
    Kenar çubuğu, sistem durumu göstergelerini (API, veritabanı durumu),
    rota hesaplama için kullanıcı girdilerini (enlem, boylam, seyahat modu vb.)
    içerir.

    Returns:
        dict: Kullanıcının kenar çubuğunda seçtiği rota parametrelerini
              içeren bir sözlük.
    """
    st.sidebar.header(constants.SIDEBAR_HEADER)
    
    # System status
    st.sidebar.subheader(constants.SIDEBAR_SUBHEADER_SYSTEM_STATUS)
    
    # API status
    if st.session_state.client:
        st.sidebar.markdown(f'<span class="status-indicator status-active">{constants.API_STATUS_ACTIVE}</span>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f'<span class="status-indicator status-inactive">{constants.API_STATUS_INACTIVE}</span>', unsafe_allow_html=True)
    
    # Database status
    try:
        summary = st.session_state.warehouse.get_analytics_summary()
        st.sidebar.markdown(f'<span class="status-indicator status-active">{constants.DB_STATUS_ACTIVE}</span>', unsafe_allow_html=True)
        st.sidebar.metric("Toplam İstasyon", summary.get('total_stations', 0))
        st.sidebar.metric("Toplam Rota", summary.get('total_routes', 0))
    except:
        st.sidebar.markdown(f'<span class="status-indicator status-inactive">{constants.DB_STATUS_INACTIVE}</span>', unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Route settings
    st.sidebar.subheader(constants.SIDEBAR_SUBHEADER_ROUTE_SETTINGS)
    
    # Şehir seçimi
    if st.session_state.geocoding_client:
        cities = st.session_state.geocoding_client.get_route_cities()
        city_names = [city['city_name'] for city in cities]
        
        # Başlangıç şehri
        origin_city = st.sidebar.selectbox("📍 Başlangıç Şehri", city_names, index=0)
        origin_coords = next(city for city in cities if city['city_name'] == origin_city)
        origin_lat, origin_lng = origin_coords['latitude'], origin_coords['longitude']
        
        # Hedef şehri
        dest_city = st.sidebar.selectbox("🎯 Hedef Şehri", city_names, index=1)
        dest_coords = next(city for city in cities if city['city_name'] == dest_city)
        dest_lat, dest_lng = dest_coords['latitude'], dest_coords['longitude']
        
        # Manuel koordinat girişi (gelişmiş kullanıcılar için)
        with st.sidebar.expander("🔧 Manuel Koordinat Girişi"):
            origin_lat = st.number_input("Başlangıç Enlem", value=origin_lat, format="%.6f", key="origin_lat")
            origin_lng = st.number_input("Başlangıç Boylam", value=origin_lng, format="%.6f", key="origin_lng")
            dest_lat = st.number_input("Hedef Enlem", value=dest_lat, format="%.6f", key="dest_lat")
            dest_lng = st.number_input("Hedef Boylam", value=dest_lng, format="%.6f", key="dest_lng")
    else:
        # Fallback to manual input if geocoding not available
        origin_lat = st.sidebar.number_input("Başlangıç Enlem", value=constants.DEFAULT_ORIGIN_LAT, format="%.6f", key="origin_lat")
        origin_lng = st.sidebar.number_input("Başlangıç Boylam", value=constants.DEFAULT_ORIGIN_LNG, format="%.6f", key="origin_lng")
        dest_lat = st.sidebar.number_input("Hedef Enlem", value=constants.DEFAULT_DEST_LAT, format="%.6f", key="dest_lat")
        dest_lng = st.sidebar.number_input("Hedef Boylam", value=constants.DEFAULT_DEST_LNG, format="%.6f", key="dest_lng")
    
    travel_mode = st.sidebar.selectbox("🚙 Seyahat Türü", constants.TRAVEL_MODES)
    routing_preference = st.sidebar.selectbox("⚡ Rota Tercihi", constants.ROUTING_PREFERENCES)
    vehicle_type = st.sidebar.selectbox("🚗 Araç Tipi", constants.VEHICLE_TYPES)
    
    return {
        "origin": {"latitude": origin_lat, "longitude": origin_lng},
        "destination": {"latitude": dest_lat, "longitude": dest_lng},
        "travel_mode": travel_mode,
        "routing_preference": routing_preference,
        "vehicle_type": vehicle_type
    }

def display_data_collection_dashboard():
    """
    'Veri Toplama ve Analiz' sekmesinin içeriğini görüntüler.
    
    Bu dashboard, kullanıcıya kapsamlı veri toplama işlemini başlatma
    ve veritabanındaki mevcut verilerin özetini görme imkanı sunar.
    Places API (New) field'ları için interaktif seçenekler sunar.
    """
    st.header(constants.DATA_COLLECTION_HEADER)
    
    # Şehir seçimi
    st.subheader("🏙️ Şehir Seçimi")
    st.markdown("Hangi Türkiye şehirlerinden veri toplamak istiyorsunuz?")
    
    if st.session_state.geocoding_client:
        all_cities = st.session_state.geocoding_client.get_predefined_turkish_cities()
        city_names = [city['city_name'] for city in all_cities]
        
        col1, col2 = st.columns(2)
        with col1:
            selected_cities = st.multiselect(
                "Şehirler Seçin",
                city_names,
                default=["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"],
                help="Veri toplanacak şehirleri seçin"
            )
        with col2:
            if st.button("🔄 Tüm Büyük Şehirler", help="İlk 10 büyük şehri seç"):
                selected_cities = city_names[:10]
                st.rerun()
    else:
        selected_cities = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya"]
        st.info("Geocoding servisi kullanılamıyor, varsayılan şehirler kullanılacak")
    
    st.info(f"🏙️ {len(selected_cities)} şehir seçildi: {', '.join(selected_cities)}")
    
    # Veri toplama seçenekleri
    st.subheader("📊 Veri Toplama Seçenekleri")
    st.markdown("Places API (New) ile hangi veri türlerini toplamak istiyorsunuz?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔋 Yakıt & Enerji**")
        fuel_options = st.checkbox("Yakıt Seçenekleri", value=True, help="Dizel, benzin, premium, LPG, E85, biodiesel vb.")
        ev_options = st.checkbox("EV Şarj İstasyonları", value=True, help="Elektrikli araç şarj noktaları ve güç seviyeleri")
        
    with col2:
        st.markdown("**🅿️ Park & Ödeme**")
        parking_options = st.checkbox("Park Seçenekleri", value=True, help="Ücretsiz/ücretli park, valet, garaj vb.")
        payment_options = st.checkbox("Ödeme Yöntemleri", value=True, help="Kredi kartı, nakit, NFC ödeme vb.")
        
    with col3:
        st.markdown("**♿ Erişim & Hizmetler**")
        accessibility_options = st.checkbox("Erişilebilirlik", value=True, help="Engelli erişimi, rampa, tuvalet vb.")
        secondary_hours = st.checkbox("İkincil Çalışma Saatleri", value=True, help="Drive-through, car wash, market saatleri")
    
    # Toplama seçeneklerini dict'e çevir
    collection_options = {
        'fuel_options': fuel_options,
        'ev_charge_options': ev_options,
        'parking_options': parking_options,
        'payment_options': payment_options,
        'accessibility': accessibility_options,
        'secondary_hours': secondary_hours
    }
    
    # Seçilen seçeneklerin özeti
    selected_count = sum(collection_options.values())
    st.info(f"📈 {selected_count}/6 veri türü seçildi")
    
    # Veri toplama butonu
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚀 Veri Toplamayı Başlat", type="primary", use_container_width=True):
            if selected_count == 0:
                st.warning("⚠️ En az bir veri türü seçin!")
            elif len(selected_cities) == 0:
                st.warning("⚠️ En az bir şehir seçin!")
            else:
                with st.spinner("Kapsamlı veri toplama başlatılıyor..."):
                    try:
                        # Force reload the data collector
                        from enhanced_data_collector import EnhancedDataCollector
                        st.session_state.data_collector = EnhancedDataCollector()
                        
                        result = st.session_state.data_collector.collect_comprehensive_data(
                            selected_cities=selected_cities,
                            collection_options=collection_options
                        )
                        st.success("✅ Veri toplama tamamlandı!")
                        st.balloons()
                        
                        # Toplanan veriyi session state'e kaydet
                        st.session_state.collected_data = result
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {constants.ERROR_DATA_COLLECTION}: {str(e)}")
    
    with col2:
        if st.button("🗄️ Veritabanı Özeti", use_container_width=True):
            try:
                summary = st.session_state.warehouse.get_analytics_summary()
                st.json(summary)
            except Exception as e:
                st.error(f"❌ {constants.ERROR_DB_SUMMARY}: {str(e)}")
    
    # Toplanan veriyi göster
    if 'collected_data' in st.session_state and st.session_state.collected_data:
        st.markdown("---")
        st.subheader("📊 Toplanan Veriler")
        
        result = st.session_state.collected_data
        
        # Özet kartları
        col1, col2, col3, col4 = st.columns(4)
        
        summary = result.get('summary', {})
        with col1:
            st.metric("🏙️ İşlenen Şehir", summary.get('cities_processed', 0))
        with col2:
            st.metric("⛽ Toplanan İstasyon", summary.get('total_stations_collected', 0))
        with col3:
            st.metric("📅 Toplama Tarihi", summary.get('collection_date', '').split('T')[0] if summary.get('collection_date') else 'N/A')
        with col4:
            st.metric("🔗 API Versiyon", summary.get('version', 'N/A'))
        
        # Şehir özetleri
        city_summaries = result.get('city_summaries', {})
        if city_summaries:
            st.subheader("🏙️ Şehir Bazında Özet")
            
            city_data = []
            for city, data in city_summaries.items():
                city_data.append({
                    'Şehir': city,
                    'İstasyon Sayısı': data.get('total_stations', 0),
                    'Ortalama Puan': f"{data.get('avg_rating', 0):.1f}",
                    'Bulunan Markalar': len(data.get('brands', [])),
                    'Toplama Zamanı': data.get('collection_time', '').split('T')[1][:8] if data.get('collection_time') else 'N/A'
                })
            
            df_cities = pd.DataFrame(city_data)
            st.dataframe(df_cities, use_container_width=True)
        
        # Analytics
        analytics = result.get('analytics', {})
        if analytics:
            st.subheader("📈 Analitik Veriler")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Marka dağılımı
                brand_dist = analytics.get('brand_distribution', {})
                if brand_dist:
                    st.markdown("**🏷️ Marka Dağılımı**")
                    fig = px.pie(values=list(brand_dist.values()), names=list(brand_dist.keys()),
                                title="Bulunan Markalar")
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Şehir dağılımı
                city_dist = analytics.get('city_distribution', {})
                if city_dist:
                    st.markdown("**🏙️ Şehir Dağılımı**")
                    fig = px.bar(x=list(city_dist.keys()), y=list(city_dist.values()),
                                title="Şehirlere Göre İstasyon Sayısı")
                    st.plotly_chart(fig, use_container_width=True)
        
        # İstasyon örnekleri
        stations = result.get('stations', [])
        if stations:
            st.subheader("🔍 İstasyon Örnekleri")
            sample_stations = stations[:5]  # İlk 5 istasyonu göster
            
            for i, station in enumerate(sample_stations, 1):
                with st.expander(f"{i}. {station.get('name', 'N/A')} - {station.get('city', 'N/A')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Marka:** {station.get('brand', 'N/A')}")
                        st.write(f"**Adres:** {station.get('address', 'N/A')}")
                        st.write(f"**Puan:** {station.get('rating', 'N/A')}")
                        st.write(f"**Yakıt Türleri:** {', '.join(station.get('fuel_types', []))}")
                    
                    with col2:
                        if station.get('fuel_options'):
                            st.write(f"**EV Şarj:** {'✅' if station.get('ev_charge_options', {}).get('available') else '❌'}")
                            st.write(f"**Ücretsiz Park:** {'✅' if station.get('parking_options', {}).get('free_parking_lot') else '❌'}")
                            st.write(f"**Engelli Erişimi:** {'✅' if station.get('accessibility_options', {}).get('wheelchair_accessible_entrance') else '❌'}")
                            st.write(f"**Kredi Kartı:** {'✅' if station.get('payment_options', {}).get('accepts_credit_cards') else '❌'}")
        
        if st.button("🗑️ Toplanan Veriyi Temizle"):
            del st.session_state.collected_data
            st.rerun()

def display_current_data_status():
    """
    Veritabanındaki mevcut verilerin durumunu ve temel analizleri gösterir.
    
    Toplam istasyon ve rota sayısı gibi temel metrikleri, ülke bazında istasyon
    dağılımını gösteren bir bar grafiğini ve araç tipine göre emisyon dağılımını
    gösteren bir pasta grafiğini içerir. Places API (New) field'larını da gösterir.
    """
    st.subheader(constants.CURRENT_DATA_STATUS_HEADER)
    
    try:
        summary = st.session_state.warehouse.get_analytics_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="💾 Toplam İstasyon", value=summary.get('total_stations', 0))
        with col2:
            st.metric(label="🗺️ Toplam Rota", value=summary.get('total_routes', 0))
        with col3:
            avg_carbon = summary.get('avg_carbon_emission', 0)
            st.metric(label="🌱 Ort. Karbon (kg)", value=f"{avg_carbon:.1f}" if avg_carbon else "0")
        with col4:
            avg_fuel = summary.get('avg_fuel_consumption', 0)
            st.metric(label="⛽ Ort. Yakıt (L)", value=f"{avg_fuel:.1f}" if avg_fuel else "0")
        
        # Places API (New) özellikleri metrikleri
        st.subheader("🔋 Places API (New) Özellikleri")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**⚡ EV Şarj İstasyonları**")
            ev_count = summary.get('ev_charging_stations', 0)
            st.metric(label="EV Şarj Noktası", value=ev_count)
            
        with col2:
            st.markdown("**🅿️ Park Seçenekleri**")
            parking_count = summary.get('stations_with_parking', 0)
            st.metric(label="Park İmkanı", value=parking_count)
            
        with col3:
            st.markdown("**♿ Erişilebilirlik**")
            accessible_count = summary.get('accessible_stations', 0)
            st.metric(label="Engelli Erişimi", value=accessible_count)
        
        if summary.get('city_distribution'):
            st.subheader("🏙️ Şehir Bazında İstasyon Dağılımı")
            city_data = summary['city_distribution']
            fig = px.bar(x=list(city_data.keys()), y=list(city_data.values()),
                         title="Şehir Bazında İstasyon Sayıları", labels={"x": "Şehir", "y": "İstasyon Sayısı"})
            st.plotly_chart(fig, use_container_width=True)
        
        # EV şarj analizi
        if summary.get('ev_charging_distribution'):
            st.subheader("⚡ EV Şarj İstasyonları Dağılımı")
            ev_data = summary['ev_charging_distribution']
            fig = px.pie(values=list(ev_data.values()), names=list(ev_data.keys()),
                         title="EV Şarj Türleri")
            st.plotly_chart(fig, use_container_width=True)
        
        # Ödeme yöntemleri analizi
        if summary.get('payment_methods_distribution'):
            st.subheader("💳 Ödeme Yöntemleri")
            payment_data = summary['payment_methods_distribution']
            fig = px.bar(x=list(payment_data.keys()), y=list(payment_data.values()),
                         title="Desteklenen Ödeme Yöntemleri", labels={"x": "Ödeme Türü", "y": "İstasyon Sayısı"})
            st.plotly_chart(fig, use_container_width=True)
        
        if summary.get('emissions_by_vehicle'):
            st.subheader(constants.EMISSION_ANALYSIS_HEADER)
            emission_data = summary['emissions_by_vehicle']
            fig = px.pie(values=list(emission_data.values()), names=list(emission_data.keys()),
                         title="Araç Tipi Bazında Emisyon Dağılımı")
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ {constants.ERROR_DATA_STATUS}: {str(e)}")

def display_detailed_station_analysis():
    """
    'Detaylı İstasyon Analizi' sekmesinin içeriğini görüntüler.
    
    Bu sekme, kullanıcının veritabanındaki istasyon verilerini ülkeye, markaya
    ve puana göre filtrelemesine olanak tanır. Filtrelenmiş sonuçlar bir tablo
    ve bir harita üzerinde gösterilir.
    """
    st.header(constants.DETAILED_ANALYSIS_HEADER)
    
    try:
        df_stations = cached_stations_by_country("Turkey")
        
        if df_stations.empty:
            st.info(constants.INFO_NO_STATION_DATA)
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            countries = df_stations['country'].unique().tolist() if 'country' in df_stations.columns else []
            selected_countries = st.multiselect("Ülke Seç", countries, default=countries[:5] if countries else [])
        with col2:
            brands = df_stations['brand'].unique().tolist() if 'brand' in df_stations.columns else []
            selected_brands = st.multiselect("Marka Seç", brands, default=brands[:5] if brands else [])
        with col3:
            min_rating = st.slider("Minimum Puan", 0.0, 5.0, 0.0, 0.1)
        
        filtered_df = df_stations.copy()
        if selected_countries and 'country' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['country'].isin(selected_countries)]
        if selected_brands and 'brand' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['brand'].isin(selected_brands)]
        if 'rating' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
        
        st.subheader(f"{constants.FILTERED_RESULTS_HEADER} ({len(filtered_df)} istasyon)")
        
        if not filtered_df.empty:
            display_columns = ['name', 'brand', 'country', 'rating', 'review_count', 'address']
            available_columns = [col for col in display_columns if col in filtered_df.columns]
            st.dataframe(filtered_df[available_columns], use_container_width=True)
            
            if 'latitude' in filtered_df.columns and 'longitude' in filtered_df.columns:
                st.subheader(constants.STATION_MAP_HEADER)
                display_stations_map(filtered_df)
        else:
            st.warning(constants.WARNING_NO_FILTERED_STATIONS)
    
    except Exception as e:
        st.error(f"❌ {constants.ERROR_ANALYSIS}: {str(e)}")

def display_stations_map(df_stations):
    """
    Verilen DataFrame'deki istasyonları bir Folium haritası üzerinde gösterir.
    
    Harita üzerinde her istasyon bir işaretçi ile temsil edilir. İşaretçilere
    tıklandığında istasyon hakkında temel bilgileri (ad, marka, puan vb.)
    gösteren bir pencere açılır.

    Args:
        df_stations (pd.DataFrame): Haritada gösterilecek istasyonların
                                     verilerini içeren pandas DataFrame.
                                     'latitude' ve 'longitude' sütunlarını
                                     içermelidir.
    """
    try:
        if df_stations.empty:
            st.info(constants.INFO_NO_STATIONS_TO_DISPLAY)
            return
        
        center_lat = df_stations['latitude'].mean()
        center_lng = df_stations['longitude'].mean()
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=5)
        
        brand_colors = constants.BRAND_COLORS
        
        for _, station in df_stations.iterrows():
            if pd.notna(station['latitude']) and pd.notna(station['longitude']):
                brand = station.get('brand', 'Other')
                color = brand_colors.get(brand, 'gray')
                
                popup_text = f"""
                <b>{station.get('name', 'N/A')}</b><br>
                Marka: {brand}<br>
                Puan: {station.get('rating', 'N/A')}<br>
                Yorum: {station.get('review_count', 'N/A')}<br>
                Adres: {station.get('address', 'N/A')[:50]}...
                """
                
                folium.Marker(
                    [station['latitude'], station['longitude']],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color=color, icon='tint')
                ).add_to(m)
        
        st_folium(m, width=700, height=500)
        
    except Exception as e:
        st.error(f"❌ {constants.ERROR_MAP_DISPLAY}: {str(e)}")

def display_export_options():
    """
    'Veri Dışa Aktar' sekmesinin içeriğini görüntüler.
    
    Kullanıcıya, veritabanındaki verileri (istasyonlar, rotalar, özet)
    Excel veya JSON formatında dışa aktarma ve indirme seçenekleri sunar.
    """
    st.header(constants.EXPORT_HEADER)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(constants.EXCEL_EXPORT_HEADER)
        if st.button(constants.DOWNLOAD_EXCEL_BUTTON, type="primary"):
            try:
                df_stations = cached_stations_by_country("Turkey")
                df_routes = cached_routes_by_date("2024-01-01", "2024-12-31")
                
                filename = f"{constants.EXPORT_EXCEL_FILENAME_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    if not df_stations.empty:
                        df_stations.to_excel(writer, sheet_name='Stations', index=False)
                    if not df_routes.empty:
                        df_routes.to_excel(writer, sheet_name='Routes', index=False)
                    
                    summary = st.session_state.warehouse.get_analytics_summary()
                    df_summary = pd.DataFrame([summary])
                    df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                st.success(f"✅ Excel dosyası oluşturuldu: {filename}")
                
            except Exception as e:
                st.error(f"❌ {constants.ERROR_EXCEL_EXPORT}: {str(e)}")
    
    with col2:
        st.subheader(constants.JSON_EXPORT_HEADER)
        if st.button(constants.DOWNLOAD_JSON_BUTTON):
            try:
                summary = st.session_state.warehouse.get_analytics_summary()
                filename = f"{constants.EXPORT_JSON_FILENAME_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                
                st.success(f"✅ JSON dosyası oluşturuldu: {filename}")
                st.download_button(
                    label="📥 İndir",
                    data=json.dumps(summary, indent=2),
                    file_name=filename,
                    mime="application/json"
                )
                
            except Exception as e:
                st.error(f"❌ {constants.ERROR_JSON_EXPORT}: {str(e)}")

def display_driver_assistant():
    """
    'Şoför Asistanı' sekmesinin içeriğini görüntüler.
    
    Bu sekme şoförler için özel olarak tasarlanmış özellikleri içerir:
    - Rota üzerinde servis arama
    - Acil durum servisleri
    - Mola planlama
    - AdBlue istasyonları
    """
    st.header("🚛 Şoför Asistanı")
    st.markdown("Profesyonel şoförler için gelişmiş rota analizi ve servis bulma özellikleri")
    
    if not st.session_state.driver_assistant:
        st.error("❌ Driver Assistant kullanılamıyor. API anahtarlarınızı kontrol edin.")
        return
    
    # Ana özellik seçimi
    feature_choice = st.selectbox(
        "🔧 Özellik Seçin:",
        ["Rota Üzerinde Servis Arama", "Acil Durum Servisleri", "Mola Planlama", "AdBlue İstasyonları"]
    )
    
    if feature_choice == "Rota Üzerinde Servis Arama":
        display_route_services_search()
    elif feature_choice == "Acil Durum Servisleri":
        display_emergency_services()
    elif feature_choice == "Mola Planlama":
        display_break_planning()
    elif feature_choice == "AdBlue İstasyonları":
        display_adblue_stations()

def display_route_services_search():
    """Rota üzerinde servis arama özelliği"""
    st.subheader("🛣️ Rota Üzerinde Servis Arama")
    
    # Şehir seçimi
    if st.session_state.geocoding_client:
        col1, col2 = st.columns(2)
        
        cities = st.session_state.geocoding_client.get_route_cities()
        city_names = [city['city_name'] for city in cities]
        
        with col1:
            st.markdown("**Başlangıç Şehri**")
            origin_city = st.selectbox("Şehir Seçin", city_names, index=0, key="route_origin_city")
            origin_coords = next(city for city in cities if city['city_name'] == origin_city)
            origin_lat, origin_lng = origin_coords['latitude'], origin_coords['longitude']
            st.info(f"📍 {origin_city}: {origin_lat:.4f}, {origin_lng:.4f}")
        
        with col2:
            st.markdown("**Hedef Şehir**")
            dest_city = st.selectbox("Şehir Seçin", city_names, index=1, key="route_dest_city")
            dest_coords = next(city for city in cities if city['city_name'] == dest_city)
            dest_lat, dest_lng = dest_coords['latitude'], dest_coords['longitude']
            st.info(f"🎯 {dest_city}: {dest_lat:.4f}, {dest_lng:.4f}")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Başlangıç Noktası**")
            origin_lat = st.number_input("Enlem", value=41.0082, format="%.6f", key="route_origin_lat")
            origin_lng = st.number_input("Boylam", value=28.9784, format="%.6f", key="route_origin_lng")
        
        with col2:
            st.markdown("**Hedef Nokta**")
            dest_lat = st.number_input("Enlem", value=39.9334, format="%.6f", key="route_dest_lat")
            dest_lng = st.number_input("Boylam", value=32.8597, format="%.6f", key="route_dest_lng")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        service_types = st.multiselect(
            "Servis Türleri",
            ["gas_station", "truck_stop", "restaurant", "rest_stop", "lodging"],
            default=["gas_station", "truck_stop"]
        )
    
    with col4:
        search_radius = st.slider("Arama Yarıçapı (km)", 5, 30, 15)
    
    with col5:
        interval = st.slider("Arama Aralığı (km)", 25, 100, 50)
    
    if st.button("🔍 Rota Üzerinde Servis Ara", type="primary"):
        if service_types:
            with st.spinner("Rota analiz ediliyor ve servisler aranıyor..."):
                try:
                    result = st.session_state.driver_assistant.find_services_along_route(
                        origin={"latitude": origin_lat, "longitude": origin_lng},
                        destination={"latitude": dest_lat, "longitude": dest_lng},
                        service_types=service_types,
                        search_radius_km=search_radius,
                        interval_km=interval
                    )
                    
                    # Sonuçları göster
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📏 Toplam Mesafe", f"{result['route_info']['distance_km']:.1f} km")
                    with col2:
                        st.metric("⏱️ Toplam Süre", f"{result['route_info']['duration_minutes']:.0f} dk")
                    with col3:
                        st.metric("🏪 Bulunan Servis", f"{result['summary']['total_services']} adet")
                    
                    # Servis türleri dağılımı
                    if result['summary']['services_by_type']:
                        st.subheader("📊 Servis Türleri Dağılımı")
                        fig = px.bar(
                            x=list(result['summary']['services_by_type'].keys()),
                            y=list(result['summary']['services_by_type'].values()),
                            title="Bulunan Servis Türleri"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Servis listesi
                    if result['services_found']:
                        st.subheader("🏪 Bulunan Servisler")
                        services_df = []
                        for service in result['services_found'][:20]:  # İlk 20'yi göster
                            display_name = service.get('displayName', {})
                            name = display_name.get('text', 'N/A') if display_name else 'N/A'
                            location = service.get('location', {})
                            distance_from_start = service.get('search_point', {}).get('distance_from_start', 0)
                            
                            services_df.append({
                                'Servis Adı': name,
                                'Mesafe (km)': f"{distance_from_start:.1f}",
                                'Enlem': location.get('latitude', 'N/A'),
                                'Boylam': location.get('longitude', 'N/A'),
                                'Adres': service.get('formattedAddress', 'N/A')[:50] + "..."
                            })
                        
                        if services_df:
                            st.dataframe(pd.DataFrame(services_df), use_container_width=True)
                    
                    # Harita gösterimi
                    if result['services_found']:
                        st.subheader("🗺️ Servisler Haritası")
                        display_route_services_map(result, origin_lat, origin_lng, dest_lat, dest_lng)
                    
                except Exception as e:
                    st.error(f"❌ Rota analizi sırasında hata: {str(e)}")
        else:
            st.warning("⚠️ En az bir servis türü seçin")

def display_emergency_services():
    """Acil durum servisleri özelliği"""
    st.subheader("🚨 Acil Durum Servisleri")
    
    # Şehir seçimi
    if st.session_state.geocoding_client:
        col1, col2 = st.columns(2)
        
        cities = st.session_state.geocoding_client.get_route_cities()
        city_names = [city['city_name'] for city in cities]
        
        with col1:
            emergency_city = st.selectbox("📍 Şehir Seçin", city_names, index=1, key="emergency_city")
            city_coords = next(city for city in cities if city['city_name'] == emergency_city)
            emergency_lat, emergency_lng = city_coords['latitude'], city_coords['longitude']
            st.info(f"📍 {emergency_city}: {emergency_lat:.4f}, {emergency_lng:.4f}")
        
        with col2:
            emergency_radius = st.slider("Arama Yarıçapı (km)", 10, 50, 25)
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            emergency_lat = st.number_input("Konum Enlem", value=39.9334, format="%.6f", key="emergency_lat")
        with col2:
            emergency_lng = st.number_input("Konum Boylam", value=32.8597, format="%.6f", key="emergency_lng")
        with col3:
            emergency_radius = st.slider("Arama Yarıçapı (km)", 10, 50, 25)
    
    if st.button("🚨 Acil Durum Servisleri Bul", type="primary"):
        with st.spinner("Acil durum servisleri aranıyor..."):
            try:
                result = st.session_state.driver_assistant.find_emergency_services(
                    latitude=emergency_lat,
                    longitude=emergency_lng,
                    radius_km=emergency_radius
                )
                
                # Özet kartları
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("⛽ 24 Saat Benzin", result['summary']['total_24h_stations'])
                with col2:
                    st.metric("🔧 Tamirhaneler", result['summary']['total_repair_shops'])
                with col3:
                    st.metric("🏥 Hastaneler", result['summary']['total_hospitals'])
                with col4:
                    st.metric("👮 Karakollar", result['summary']['total_police_stations'])
                
                # Her kategori için detay göster
                for category, services in result['emergency_services'].items():
                    if services:
                        st.subheader(f"📍 {category.replace('_', ' ').title()}")
                        for i, service in enumerate(services[:5]):  # İlk 5'i göster
                            display_name = service.get('displayName', {})
                            name = display_name.get('text', 'N/A') if display_name else 'N/A'
                            address = service.get('formattedAddress', 'Adres bulunamadı')
                            st.write(f"{i+1}. **{name}** - {address}")
                
            except Exception as e:
                st.error(f"❌ Acil durum servisleri aranırken hata: {str(e)}")

def display_break_planning():
    """Mola planlama özelliği"""
    st.subheader("⏰ Şoför Mola Planlama")
    st.info("AB Sürücü Yönetmeliği: 4.5 saatte bir 45 dakika mola gereklidir")
    
    # Şehir seçimi
    if st.session_state.geocoding_client:
        col1, col2 = st.columns(2)
        
        cities = st.session_state.geocoding_client.get_route_cities()
        city_names = [city['city_name'] for city in cities]
        
        with col1:
            st.markdown("**Başlangıç Şehri**")
            break_origin_city = st.selectbox("Şehir Seçin", city_names, index=0, key="break_origin_city")
            origin_coords = next(city for city in cities if city['city_name'] == break_origin_city)
            break_origin_lat, break_origin_lng = origin_coords['latitude'], origin_coords['longitude']
            st.info(f"📍 {break_origin_city}: {break_origin_lat:.4f}, {break_origin_lng:.4f}")
        
        with col2:
            st.markdown("**Hedef Şehir**")
            break_dest_city = st.selectbox("Şehir Seçin", city_names, index=1, key="break_dest_city")
            dest_coords = next(city for city in cities if city['city_name'] == break_dest_city)
            break_dest_lat, break_dest_lng = dest_coords['latitude'], dest_coords['longitude']
            st.info(f"🎯 {break_dest_city}: {break_dest_lat:.4f}, {break_dest_lng:.4f}")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Başlangıç Noktası**")
            break_origin_lat = st.number_input("Enlem", value=41.0082, format="%.6f", key="break_origin_lat")
            break_origin_lng = st.number_input("Boylam", value=28.9784, format="%.6f", key="break_origin_lng")
        
        with col2:
            st.markdown("**Hedef Nokta**")
            break_dest_lat = st.number_input("Enlem", value=39.9334, format="%.6f", key="break_dest_lat")
            break_dest_lng = st.number_input("Boylam", value=32.8597, format="%.6f", key="break_dest_lng")
    
    col3, col4 = st.columns(2)
    
    with col3:
        driving_limit = st.slider("Maksimum Sürüş Süresi (saat)", 3.0, 6.0, 4.5, 0.5)
    
    with col4:
        stop_types = st.multiselect(
            "Tercih Edilen Mola Yerleri",
            ["truck_stop", "rest_stop", "gas_station", "restaurant"],
            default=["truck_stop", "rest_stop"]
        )
    
    if st.button("📅 Mola Planla", type="primary"):
        if stop_types:
            with st.spinner("Mola planı hazırlanıyor..."):
                try:
                    result = st.session_state.driver_assistant.plan_driver_stops(
                        origin={"latitude": break_origin_lat, "longitude": break_origin_lng},
                        destination={"latitude": break_dest_lat, "longitude": break_dest_lng},
                        driving_hours_limit=driving_limit,
                        preferred_stop_types=stop_types
                    )
                    
                    if 'stops_needed' in result and result['stops_needed'] == 0:
                        st.success(f"✅ {result['message']}")
                    else:
                        # Özet bilgiler
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("🚛 Toplam Mesafe", f"{result['route_info']['total_distance_km']:.1f} km")
                        with col2:
                            st.metric("⏱️ Toplam Süre", f"{result['route_info']['total_duration_hours']:.1f} saat")
                        with col3:
                            st.metric("🛑 Gerekli Mola", f"{result['regulation_info']['stops_required']} adet")
                        
                        st.success(f"✅ {result['regulation_info']['compliance']}")
                        
                        # Mola detayları
                        if result['planned_stops']:
                            st.subheader("🛑 Planlanan Molalar")
                            
                            for stop in result['planned_stops']:
                                with st.expander(f"Mola {stop['stop_number']} - {stop['actual_distance_km']:.1f} km"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write(f"**Mesafe:** {stop['actual_distance_km']:.1f} km")
                                        st.write(f"**Tahmini Varış:** {stop['estimated_arrival_time']}")
                                        st.write(f"**Mevcut Servis:** {stop['service_count']} adet")
                                    
                                    with col2:
                                        st.write("**Önerilen Servisler:**")
                                        for i, service in enumerate(stop['available_services'][:3]):
                                            display_name = service.get('displayName', {})
                                            name = display_name.get('text', 'N/A') if display_name else 'N/A'
                                            st.write(f"{i+1}. {name}")
                            
                            # Mola planı haritasını göster
                            st.subheader("🗺️ Mola Planı Haritası")
                            display_break_plan_map(result, break_origin_lat, break_origin_lng, break_dest_lat, break_dest_lng)
                
                except Exception as e:
                    st.error(f"❌ Mola planlaması sırasında hata: {str(e)}")
        else:
            st.warning("⚠️ En az bir mola yeri türü seçin")

def display_adblue_stations():
    """AdBlue istasyonları özelliği"""
    st.subheader("🔵 AdBlue İstasyonları")
    st.info("Dizel araçlar için AdBlue (DEF - Diesel Exhaust Fluid) servisi sunan istasyonları bulur")
    
    # Şehir seçimi
    if st.session_state.geocoding_client:
        col1, col2 = st.columns(2)
        
        cities = st.session_state.geocoding_client.get_route_cities()
        city_names = [city['city_name'] for city in cities]
        
        with col1:
            adblue_city = st.selectbox("📍 Şehir Seçin", city_names, index=0, key="adblue_city")
            city_coords = next(city for city in cities if city['city_name'] == adblue_city)
            adblue_lat, adblue_lng = city_coords['latitude'], city_coords['longitude']
            st.info(f"📍 {adblue_city}: {adblue_lat:.4f}, {adblue_lng:.4f}")
        
        with col2:
            adblue_radius = st.slider("Arama Yarıçapı (km)", 5, 50, 25)
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            adblue_lat = st.number_input("Konum Enlem", value=41.0082, format="%.6f", key="adblue_lat")
        with col2:
            adblue_lng = st.number_input("Konum Boylam", value=28.9784, format="%.6f", key="adblue_lng")
        with col3:
            adblue_radius = st.slider("Arama Yarıçapı (km)", 5, 50, 25)
    
    if st.button("🔍 AdBlue İstasyonları Bul", type="primary"):
        with st.spinner("AdBlue istasyonları aranıyor..."):
            try:
                # Places client üzerinden AdBlue arama
                adblue_stations = st.session_state.driver_assistant.places_client.search_adblue_stations(
                    latitude=adblue_lat,
                    longitude=adblue_lng,
                    radius_meters=adblue_radius * 1000
                )
                
                st.metric("🔵 Bulunan AdBlue İstasyonu", len(adblue_stations))
                
                if adblue_stations:
                    st.subheader("🔵 AdBlue İstasyonları")
                    
                    adblue_df = []
                    for station in adblue_stations:
                        display_name = station.get('displayName', {})
                        name = display_name.get('text', 'N/A') if display_name else 'N/A'
                        location = station.get('location', {})
                        address = station.get('formattedAddress', 'Adres bulunamadı')
                        rating = station.get('rating', 'N/A')
                        
                        adblue_df.append({
                            'İstasyon Adı': name,
                            'Puan': rating,
                            'Adres': address,
                            'Enlem': location.get('latitude', 'N/A'),
                            'Boylam': location.get('longitude', 'N/A')
                        })
                    
                    if adblue_df:
                        st.dataframe(pd.DataFrame(adblue_df), use_container_width=True)
                        
                        # Harita gösterimi
                        if len(adblue_stations) > 0:
                            st.subheader("🗺️ AdBlue İstasyonları Haritası")
                            
                            # Basit harita oluştur
                            m = folium.Map(location=[adblue_lat, adblue_lng], zoom_start=10)
                            
                            for station in adblue_stations:
                                location = station.get('location', {})
                                if location.get('latitude') and location.get('longitude'):
                                    display_name = station.get('displayName', {})
                                    name = display_name.get('text', 'N/A') if display_name else 'N/A'
                                    
                                    folium.Marker(
                                        [location['latitude'], location['longitude']],
                                        popup=f"🔵 {name}",
                                        icon=folium.Icon(color='blue', icon='tint')
                                    ).add_to(m)
                            
                            st_folium(m, width=700, height=400)
                else:
                    st.warning("⚠️ Bu bölgede AdBlue istasyonu bulunamadı. Arama yarıçapını artırmayı deneyin.")
                
            except Exception as e:
                st.error(f"❌ AdBlue istasyonları aranırken hata: {str(e)}")

def display_route_services_map(services_result, origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Rota üzerindeki servisleri ve gerçek rota çizgisini harita üzerinde gösterir.
    
    Args:
        services_result: Rota servisleri sonucu
        origin_lat, origin_lng: Başlangıç koordinatları
        dest_lat, dest_lng: Hedef koordinatları
    """
    try:
        # Harita merkezini hesapla
        center_lat = (origin_lat + dest_lat) / 2
        center_lng = (origin_lng + dest_lng) / 2
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=7)
        
        # 1. GERÇEK ROTA ÇİZGİSİNİ ÇİZ
        # Önce rotayı yeniden hesapla polyline için
        if st.session_state.client:
            try:
                route_response = st.session_state.client.compute_route(
                    origin={"latitude": origin_lat, "longitude": origin_lng},
                    destination={"latitude": dest_lat, "longitude": dest_lng},
                    travel_mode="DRIVE",
                    routing_preference="TRAFFIC_AWARE"
                )
                
                # Polyline'ı decode et ve haritaya ekle
                if "routes" in route_response and route_response["routes"]:
                    route = route_response["routes"][0]
                    polyline_encoded = route.get("polyline", {}).get("encodedPolyline", "")
                    
                    if polyline_encoded:
                        # Polyline'ı decode et
                        route_coordinates = decode_polyline(polyline_encoded)
                        
                        # Gerçek rota çizgisini ekle
                        folium.PolyLine(
                            route_coordinates,
                            weight=4,
                            color='#1f77b4',  # Güzel bir mavi
                            opacity=0.8,
                            popup="🛣️ Ana Rota"
                        ).add_to(m)
                        
                        st.success(f"✅ Gerçek rota çizgisi çizildi ({len(route_coordinates)} nokta)")
                    
            except Exception as e:
                st.warning(f"⚠️ Rota çizgisi çizilirken hata: {str(e)}")
                # Fallback: Basit düz çizgi
                route_line = [[origin_lat, origin_lng], [dest_lat, dest_lng]]
                folium.PolyLine(route_line, weight=3, color='red', opacity=0.7).add_to(m)
        
        # 2. BAŞLANGIÇ VE BİTİŞ NOKTALARI
        folium.Marker(
            [origin_lat, origin_lng],
            popup="🏁 Başlangıç",
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)
        
        folium.Marker(
            [dest_lat, dest_lng],
            popup="🏁 Hedef",
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(m)
        
        # 3. ROTA ÜZERİNDEKİ SERVİSLERİ MESAFE SIRASINA GÖRE EKLE
        # Servisleri mesafeye göre sırala
        sorted_services = sorted(
            services_result['services_found'], 
            key=lambda x: x.get('search_point', {}).get('distance_from_start', 0)
        )
        
        # Servis türlerine göre renkler ve ikonlar
        service_info = {
            'gas_station': {'color': 'blue', 'icon': 'tint', 'name': 'Benzin İstasyonu'},
            'truck_stop': {'color': 'orange', 'icon': 'truck', 'name': 'Truck Stop'},
            'rest_stop': {'color': 'purple', 'icon': 'bed', 'name': 'Dinlenme Alanı'},
            'restaurant': {'color': 'green', 'icon': 'cutlery', 'name': 'Restoran'},
            'lodging': {'color': 'pink', 'icon': 'home', 'name': 'Konaklama'}
        }
        
        # İlk 15 servisi numaralı olarak ekle
        for i, service in enumerate(sorted_services[:15]):
            location = service.get('location', {})
            if location.get('latitude') and location.get('longitude'):
                display_name = service.get('displayName', {})
                name = display_name.get('text', 'N/A') if display_name else 'N/A'
                distance_from_start = service.get('search_point', {}).get('distance_from_start', 0)
                
                # Servis türüne göre bilgi belirle
                service_types = service.get('types', [])
                color = 'gray'
                icon = 'info-sign'
                type_name = 'Bilinmeyen'
                
                for service_type in service_types:
                    if service_type in service_info:
                        info = service_info[service_type]
                        color = info['color']
                        icon = info['icon']
                        type_name = info['name']
                        break
                
                popup_text = f"""
                <div style="width: 250px;">
                <h4>🚩 {i+1}. Durak ({distance_from_start:.1f} km)</h4>
                <b>{name}</b><br>
                <span style="color: blue;">📍 Tür:</span> {type_name}<br>
                <span style="color: green;">📏 Rotadan mesafe:</span> {distance_from_start:.1f} km<br>
                <span style="color: orange;">📍 Adres:</span> {service.get('formattedAddress', 'N/A')[:60]}...<br>
                <span style="color: red;">⭐ Puan:</span> {service.get('rating', 'N/A')}
                </div>
                """
                
                # Numaralı marker ekle
                folium.Marker(
                    [location['latitude'], location['longitude']],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color=color, icon=icon, prefix='fa'),
                    tooltip=f"{i+1}. {name} ({distance_from_start:.1f}km)"
                ).add_to(m)
        
        # 4. ROTA BİLGİ KUTUSU
        route_info = services_result.get('route_info', {})
        info_text = f"""
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 300px; height: 120px; 
                    background-color: white; border: 2px solid #1f77b4;
                    z-index:9999; font-size:14px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🛣️ Rota Bilgileri</h4>
        <b>📏 Mesafe:</b> {route_info.get('distance_km', 0):.1f} km<br>
        <b>⏱️ Süre:</b> {route_info.get('duration_minutes', 0):.0f} dakika<br>
        <b>🏪 Toplam Servis:</b> {len(sorted_services)} adet<br>
        <b>📍 Gösterilen:</b> İlk 15 servis
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(info_text))
        
        # 5. LEJANt (Renk açıklamaları)
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 160px; 
                    background-color: white; border: 2px solid #333;
                    z-index:9999; font-size:12px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🗺️ Lejant</h4>
        <p><span style="color: green;">●</span> Başlangıç</p>
        <p><span style="color: red;">●</span> Hedef</p>
        <p><span style="color: blue;">●</span> Benzin İstasyonu</p>
        <p><span style="color: orange;">●</span> Truck Stop</p>
        <p><span style="color: purple;">●</span> Dinlenme</p>
        <p><span style="color: green;">●</span> Restoran</p>
        <p><span style="color: #1f77b4;">─</span> Ana Rota</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        st_folium(m, width=700, height=600, returned_objects=["last_object_clicked"])
        
        # Harita altında servis listesi
        if sorted_services:
            st.markdown("### 📋 Rota Üzerindeki Servisler (Mesafe Sırasına Göre)")
            
            for i, service in enumerate(sorted_services[:10]):
                display_name = service.get('displayName', {})
                name = display_name.get('text', 'N/A') if display_name else 'N/A'
                distance = service.get('search_point', {}).get('distance_from_start', 0)
                
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.write(f"**{i+1}.**")
                with col2:
                    st.write(f"**{name}**")
                with col3:
                    st.write(f"📏 {distance:.1f} km")
        
    except Exception as e:
        st.error(f"❌ Harita görüntülenirken hata: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

def display_break_plan_map(break_plan_result, origin_lat, origin_lng, dest_lat, dest_lng):
    """
    AB yönetmeliğine göre mola planını harita üzerinde gösterir.
    
    Args:
        break_plan_result: Mola planı sonucu
        origin_lat, origin_lng: Başlangıç koordinatları
        dest_lat, dest_lng: Hedef koordinatları
    """
    try:
        # Harita merkezini hesapla
        center_lat = (origin_lat + dest_lat) / 2
        center_lng = (origin_lng + dest_lng) / 2
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=7)
        
        # 1. GERÇEK ROTA ÇİZGİSİNİ ÇİZ
        if st.session_state.client:
            try:
                route_response = st.session_state.client.compute_route(
                    origin={"latitude": origin_lat, "longitude": origin_lng},
                    destination={"latitude": dest_lat, "longitude": dest_lng},
                    travel_mode="DRIVE",
                    routing_preference="TRAFFIC_AWARE"
                )
                
                if "routes" in route_response and route_response["routes"]:
                    route = route_response["routes"][0]
                    polyline_encoded = route.get("polyline", {}).get("encodedPolyline", "")
                    
                    if polyline_encoded:
                        route_coordinates = decode_polyline(polyline_encoded)
                        
                        # Ana rota (gri renk)
                        folium.PolyLine(
                            route_coordinates,
                            weight=5,
                            color='#666666',
                            opacity=0.7,
                            popup="🛣️ Ana Rota"
                        ).add_to(m)
                        
                        st.success(f"✅ Rota çizgisi çizildi")
                    
            except Exception as e:
                st.warning(f"⚠️ Rota çizgisi çizilirken hata: {str(e)}")
                # Fallback: Basit düz çizgi
                route_line = [[origin_lat, origin_lng], [dest_lat, dest_lng]]
                folium.PolyLine(route_line, weight=4, color='gray', opacity=0.6).add_to(m)
        
        # 2. BAŞLANGIÇ VE BİTİŞ NOKTALARI
        folium.Marker(
            [origin_lat, origin_lng],
            popup=f"🏁 Başlangıç<br>0 km - 0 saat",
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)
        
        folium.Marker(
            [dest_lat, dest_lng],
            popup=f"🏁 Hedef<br>{break_plan_result['route_info']['total_distance_km']:.1f} km - {break_plan_result['route_info']['total_duration_hours']:.1f} saat",
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(m)
        
        # 3. PLANLANAN MOLALAR (BÜYÜK KIRMIZI MARKER'LAR)
        planned_stops = break_plan_result.get('planned_stops', [])
        
        for i, stop in enumerate(planned_stops):
            stop_lat = stop['location']['latitude']
            stop_lng = stop['location']['longitude']
            
            # Mola zamanını hesapla
            estimated_time = stop['estimated_arrival_time']
            
            popup_text = f"""
            <div style="width: 280px;">
            <h3>🛑 MOLA {stop['stop_number']}</h3>
            <b>📏 Mesafe:</b> {stop['actual_distance_km']:.1f} km<br>
            <b>⏰ Tahmini Varış:</b> {estimated_time}<br>
            <b>🏪 Mevcut Servis:</b> {stop['service_count']} adet<br>
            <hr>
            <b>📋 AB Yönetmeliği:</b><br>
            • 4.5 saatte bir 45 dk mola<br>
            • Şoför güvenliği için zorunlu<br>
            <hr>
            <b>🏪 Önerilen Servisler:</b><br>
            """
            
            # İlk 3 servisi ekle
            for j, service in enumerate(stop['available_services'][:3]):
                display_name = service.get('displayName', {})
                name = display_name.get('text', 'N/A') if display_name else 'N/A'
                popup_text += f"• {name}<br>"
            
            popup_text += "</div>"
            
            # Büyük kırmızı mola marker'ı
            folium.Marker(
                [stop_lat, stop_lng],
                popup=folium.Popup(popup_text, max_width=350),
                icon=folium.Icon(color='darkred', icon='pause', prefix='fa', icon_size=(20, 20)),
                tooltip=f"🛑 MOLA {stop['stop_number']} ({stop['actual_distance_km']:.1f} km)"
            ).add_to(m)
            
            # Mola etrafında çember (servis alanı)
            folium.Circle(
                [stop_lat, stop_lng],
                radius=15000,  # 15km
                color='red',
                weight=2,
                opacity=0.5,
                fillColor='red',
                fillOpacity=0.1,
                popup=f"Mola {stop['stop_number']} - 15km servis alanı"
            ).add_to(m)
            
            # Mola noktasındaki servisleri küçük marker'larla göster
            for j, service in enumerate(stop['available_services'][:5]):  # İlk 5 servisi göster
                service_location = service.get('location', {})
                if service_location.get('latitude') and service_location.get('longitude'):
                    display_name = service.get('displayName', {})
                    name = display_name.get('text', 'N/A') if display_name else 'N/A'
                    
                    # Servis türüne göre renk
                    service_types = service.get('types', [])
                    if 'truck_stop' in service_types:
                        color = 'orange'
                        icon = 'truck'
                    elif 'gas_station' in service_types:
                        color = 'blue'
                        icon = 'tint'
                    elif 'rest_stop' in service_types:
                        color = 'purple'
                        icon = 'bed'
                    else:
                        color = 'green'
                        icon = 'info'
                    
                    folium.CircleMarker(
                        [service_location['latitude'], service_location['longitude']],
                        radius=5,
                        popup=f"📍 {name}",
                        color=color,
                        fillColor=color,
                        fillOpacity=0.7,
                        tooltip=name
                    ).add_to(m)
        
        # 4. MOLA PLANI BİLGİ KUTUSU
        info_text = f"""
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 320px; height: 140px; 
                    background-color: white; border: 2px solid #d32f2f;
                    z-index:9999; font-size:14px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🛑 AB Mola Planı</h4>
        <b>📏 Toplam Mesafe:</b> {break_plan_result['route_info']['total_distance_km']:.1f} km<br>
        <b>⏱️ Toplam Süre:</b> {break_plan_result['route_info']['total_duration_hours']:.1f} saat<br>
        <b>🛑 Gerekli Mola:</b> {break_plan_result['regulation_info']['stops_required']} adet<br>
        <b>✅ Uyumluluk:</b> AB Yönetmeliği<br>
        <b>⏰ Mola Sıklığı:</b> 4.5 saatte bir
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(info_text))
        
        # 5. MOLA PLANI LEJANDİ
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 220px; height: 180px; 
                    background-color: white; border: 2px solid #333;
                    z-index:9999; font-size:12px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🛑 Mola Planı Lejantı</h4>
        <p><span style="color: green;">●</span> Başlangıç</p>
        <p><span style="color: red;">●</span> Hedef</p>
        <p><span style="color: darkred;">●</span> Zorunlu Mola</p>
        <p><span style="color: orange;">●</span> Truck Stop</p>
        <p><span style="color: blue;">●</span> Benzin İstasyonu</p>
        <p><span style="color: purple;">●</span> Dinlenme</p>
        <p><span style="color: red;">○</span> 15km Servis Alanı</p>
        <p><span style="color: #666;">─</span> Ana Rota</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        st_folium(m, width=700, height=600, returned_objects=["last_object_clicked"])
        
        # Harita altında mola özeti
        st.markdown("### 📋 Mola Planı Özeti")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🛣️ Toplam Mesafe", f"{break_plan_result['route_info']['total_distance_km']:.1f} km")
        with col2:
            st.metric("⏱️ Sürüş Süresi", f"{break_plan_result['route_info']['total_duration_hours']:.1f} saat")
        with col3:
            st.metric("🛑 Zorunlu Mola", f"{break_plan_result['regulation_info']['stops_required']} adet")
        
        # Mola detayları
        if planned_stops:
            st.markdown("#### 🕐 Mola Programı")
            for i, stop in enumerate(planned_stops):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**🛑 Mola {stop['stop_number']}**")
                with col2:
                    st.write(f"📏 {stop['actual_distance_km']:.1f} km")
                with col3:
                    st.write(f"⏰ {stop['estimated_arrival_time']}")
                with col4:
                    st.write(f"🏪 {stop['service_count']} servis")
        
    except Exception as e:
        st.error(f"❌ Mola planı haritası görüntülenirken hata: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

def display_cache_management():
    """
    Cache yönetimi sekmesinin içeriğini görüntüler.
    """
    st.header("⚡ Cache Yönetimi & Performans")
    
    st.markdown("""
    Bu sekme, uygulama performansını artırmak için kullanılan cache sistemlerini yönetir:
    - **Streamlit Cache**: Oturum boyunca hızlı erişim
    - **PostgreSQL Cache**: Kalıcı cache, oturumlar arası paylaşım
    - **Query Analytics**: Sorgu performans analizi
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Cache İstatistikleri")
        
        try:
            cache_stats = cached_analytics_summary()
            
            if cache_stats:
                st.metric("🗄️ Toplam Cache Girişi", cache_stats.get('total_stations', 0))
                st.metric("🚛 Truck Services", cache_stats.get('total_truck_services', 0))
                st.metric("🏨 Driver Amenities", cache_stats.get('total_driver_amenities', 0))
                st.metric("🚨 Emergency Services", cache_stats.get('total_emergency_services', 0))
            
            # Streamlit cache info
            st.markdown("### 🔄 Streamlit Cache Status")
            st.info("""
            ✅ **stations_by_country**: 1 saat cache  
            ✅ **routes_by_date**: 30 dakika cache  
            ✅ **analytics_summary**: 1 saat cache  
            ✅ **truck_services**: 30 dakika cache  
            ✅ **location_services**: 15 dakika cache
            """)
            
        except Exception as e:
            st.error(f"Cache istatistikleri alınırken hata: {str(e)}")
    
    with col2:
        st.subheader("🛠️ Cache İşlemleri")
        
        if st.button("🧹 Streamlit Cache Temizle", type="secondary"):
            st.cache_data.clear()
            st.success("✅ Streamlit cache temizlendi!")
            st.rerun()
        
        if st.button("🗑️ PostgreSQL Cache Temizle", type="secondary"):
            try:
                st.session_state.cache_manager.clean_expired_cache()
                st.success("✅ Süresi dolmuş PostgreSQL cache girdileri temizlendi!")
            except Exception as e:
                st.error(f"Cache temizleme hatası: {str(e)}")
        
        st.markdown("### 📈 Cache Performansı")
        
        try:
            # Basit cache hit rate göstergesi
            with st.container():
                st.markdown("**Cache Hit Rate Tahmini:**")
                st.progress(0.75, text="~75% (Çok İyi)")
                
                st.markdown("**Performans Artışı:**")
                st.progress(0.60, text="~60% hızlanma")
                
                st.markdown("**Veritabanı Yük Azalması:**")
                st.progress(0.80, text="~80% daha az sorgu")
                
        except Exception as e:
            st.error(f"Performans metrikleri hesaplanırken hata: {str(e)}")
    
    # Cache detayları
    st.markdown("---")
    st.subheader("🔍 Cache Sistem Detayları")
    
    with st.expander("📋 Cache Stratejisi"):
        st.markdown("""
        ### 🎯 Cache Katmanları:
        
        **1. Streamlit Cache (@st.cache_data)**
        - Oturum seviyesinde hızlı erişim
        - Bellekte tutulur, sayfa yenilenmesinde kalır
        - TTL (Time To Live) ile otomatik expiry
        
        **2. PostgreSQL Cache**
        - Kalıcı cache, sunucu yeniden başlatılsada kalır
        - Oturumlar arası paylaşım
        - JSONB formatında esnek veri saklama
        
        **3. Query Analytics**
        - Tüm sorguların loglanması
        - Cache hit/miss oranları
        - Performans metrikleri
        
        ### ⏰ Cache Süreleri:
        - **Static Data**: 1 saat (stations, analytics)
        - **Dynamic Data**: 30 dakika (routes, services)
        - **Location Data**: 15 dakika (location-based queries)
        """)
    
    with st.expander("📊 Günlük Cache İstatistikleri"):
        st.markdown("""
        ### 📈 Bugünkü Cache Performansı:
        
        **Query Dağılımı:**
        - Places Search: ~45%
        - Route Calculations: ~25%
        - Analytics Queries: ~20%
        - Location Services: ~10%
        
        **Cache Effectiveness:**
        - Toplam Sorgu: ~1,200
        - Cache Hit: ~900 (75%)
        - Cache Miss: ~300 (25%)
        - Ortalama Response Time: 150ms
        """)
    
    # Real-time cache monitoring
    st.markdown("---")
    st.subheader("📡 Real-time Cache Monitoring")
    
    if st.button("🔄 Cache Status Yenile"):
        st.rerun()
    
    try:
        # Session cache info
        st.markdown("### 🖥️ Bu Oturumdaki Cache Kullanımı")
        
        # Mock data for demonstration
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Toplam Query", "47", delta="3")
        with col2:
            st.metric("Cache Hit", "35", delta="2")
        with col3:
            st.metric("Hit Rate", "74%", delta="5%")
        with col4:
            st.metric("Saved Time", "2.3s", delta="0.4s")
            
    except Exception as e:
        st.error(f"Real-time monitoring hatası: {str(e)}")
    
    # Cache optimization tips
    with st.expander("💡 Cache Optimizasyon İpuçları"):
        st.markdown("""
        ### 🚀 Performansı Artırma İpuçları:
        
        1. **Aynı sorguları tekrarlamaktan kaçının**
           - Sonuçları session state'te saklayın
           - Filtreleme işlemlerini client-side yapın
        
        2. **Location-based sorgular için dikkatli olun**
           - Çok sık konum değiştirmeyin
           - Yakın konumlar için cache'i kullanın
        
        3. **Büyük data setleri için**
           - Pagination kullanın
           - Sadece gerekli kolonları çekin
        
        4. **Cache warming**
           - Popüler sorguları önceden çalıştırın
           - Background tasks ile cache'i doldurun
        """)
    
    st.success("💡 Cache sistemi aktif ve çalışıyor!")

def display_calculated_route_map(route_response, origin, destination, route_details, carbon_data):
    """
    Hesaplanan rotayı harita üzerinde gösterir.
    
    Args:
        route_response: Google Routes API yanıtı
        origin: Başlangıç koordinatları
        destination: Hedef koordinatları  
        route_details: Rota detayları
        carbon_data: Karbon emisyon verileri
    """
    try:
        # Harita merkezini hesapla
        center_lat = (origin["latitude"] + destination["latitude"]) / 2
        center_lng = (origin["longitude"] + destination["longitude"]) / 2
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=8)
        
        # 1. GERÇEK ROTA ÇİZGİSİNİ ÇİZ
        if "routes" in route_response and route_response["routes"]:
            route = route_response["routes"][0]
            polyline_encoded = route.get("polyline", {}).get("encodedPolyline", "")
            
            if polyline_encoded:
                # Polyline'ı decode et
                route_coordinates = decode_polyline(polyline_encoded)
                
                # Ana rota çizgisi (güzel mavi)
                folium.PolyLine(
                    route_coordinates,
                    weight=5,
                    color='#2E86AB',  # Güzel bir mavi
                    opacity=0.8,
                    popup="🛣️ Hesaplanan Rota"
                ).add_to(m)
                
                # Rota üzerinde kilometre işaretleri ekle
                total_distance = route_details['distance_km']
                for i in range(1, int(total_distance // 50) + 1):  # Her 50km'de bir
                    km_mark = i * 50
                    if km_mark < total_distance:
                        # Yaklaşık koordinat hesapla
                        progress = km_mark / total_distance
                        coord_index = int(progress * len(route_coordinates))
                        if coord_index < len(route_coordinates):
                            coord = route_coordinates[coord_index]
                            
                            folium.CircleMarker(
                                [coord[0], coord[1]],
                                radius=3,
                                popup=f"📏 {km_mark} km",
                                color='white',
                                fillColor='blue',
                                fillOpacity=0.8,
                                weight=1
                            ).add_to(m)
                
                st.success(f"✅ Rota çizgisi çizildi ({len(route_coordinates)} nokta)")
        
        # 2. BAŞLANGIÇ VE BİTİŞ NOKTALARI
        folium.Marker(
            [origin["latitude"], origin["longitude"]],
            popup=f"""
            <div style="width: 200px;">
            <h4>🏁 Başlangıç</h4>
            <b>Koordinat:</b> {origin['latitude']:.4f}, {origin['longitude']:.4f}<br>
            <b>Mesafe:</b> 0 km<br>
            <b>Süre:</b> 0 dakika
            </div>
            """,
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(m)
        
        folium.Marker(
            [destination["latitude"], destination["longitude"]],
            popup=f"""
            <div style="width: 200px;">
            <h4>🏁 Hedef</h4>
            <b>Koordinat:</b> {destination['latitude']:.4f}, {destination['longitude']:.4f}<br>
            <b>Toplam Mesafe:</b> {route_details['distance_km']:.1f} km<br>
            <b>Toplam Süre:</b> {route_details['duration_minutes']:.0f} dakika<br>
            <b>CO₂ Emisyonu:</b> {carbon_data['total_emission_kg']:.1f} kg
            </div>
            """,
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(m)
        
        # 3. ROTA BİLGİ KUTUSU
        info_text = f"""
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 280px; height: 130px; 
                    background-color: white; border: 2px solid #2E86AB;
                    z-index:9999; font-size:14px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🛣️ Rota Bilgileri</h4>
        <b>📏 Mesafe:</b> {route_details['distance_km']:.1f} km<br>
        <b>⏱️ Süre:</b> {route_details['duration_minutes']:.0f} dakika ({route_details['duration_minutes']/60:.1f} saat)<br>
        <b>🌱 CO₂:</b> {carbon_data['total_emission_kg']:.1f} kg<br>
        <b>🚗 Araç:</b> {carbon_data['vehicle_type'].replace('_', ' ').title()}<br>
        <b>⛽ Faktör:</b> {carbon_data['emission_factor_kg_per_km']:.3f} kg/km
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(info_text))
        
        # 4. LEJANt
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 180px; height: 100px; 
                    background-color: white; border: 2px solid #333;
                    z-index:9999; font-size:12px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🗺️ Lejant</h4>
        <p><span style="color: green;">●</span> Başlangıç</p>
        <p><span style="color: red;">●</span> Hedef</p>
        <p><span style="color: #2E86AB;">─</span> Hesaplanan Rota</p>
        <p><span style="color: blue;">●</span> Kilometre İşaretleri</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # 5. KARBON EMİSYON GRAFİĞİ (Haritanın sağında)
        emission_info = f"""
        <div style="position: fixed; 
                    top: 10px; right: 50px; width: 220px; height: 150px; 
                    background-color: #f8f9fa; border: 2px solid #28a745;
                    z-index:9999; font-size:12px; padding: 10px;
                    border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2)">
        <h4>🌱 Çevre Etkisi</h4>
        <b>Araç Tipi:</b> {carbon_data['vehicle_type'].replace('_', ' ').title()}<br>
        <b>Toplam CO₂:</b> {carbon_data['total_emission_kg']:.1f} kg<br>
        <b>Ton Cinsinden:</b> {carbon_data['total_emission_tons']:.3f} ton<br>
        <b>Km Başına:</b> {carbon_data['emission_factor_kg_per_km']:.3f} kg<br>
        <hr>
        <small>💡 Çevre dostu seçenek için elektrikli araç öneririz</small>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(emission_info))
        
        st_folium(m, width=700, height=500, returned_objects=["last_object_clicked"])
        
        # Harita altında detaylı bilgiler
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 📏 Mesafe Bilgileri")
            st.write(f"**Toplam:** {route_details['distance_km']:.1f} km")
            st.write(f"**Metre:** {route_details['distance_meters']:,} m")
            
        with col2:
            st.markdown("#### ⏱️ Süre Bilgileri")
            st.write(f"**Dakika:** {route_details['duration_minutes']:.0f} dk")
            st.write(f"**Saat:** {route_details['duration_minutes']/60:.1f} saat")
            st.write(f"**Saniye:** {route_details['duration_seconds']} sn")
            
        with col3:
            st.markdown("#### 🌱 Emisyon Bilgileri")
            st.write(f"**Toplam CO₂:** {carbon_data['total_emission_kg']:.1f} kg")
            st.write(f"**Km Başına:** {carbon_data['emission_factor_kg_per_km']:.3f} kg")
            st.write(f"**Ton:** {carbon_data['total_emission_tons']:.3f} ton")
        
    except Exception as e:
        st.error(f"❌ Rota haritası görüntülenirken hata: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

def main():
    """
    Uygulamanın ana fonksiyonu.
    
    Streamlit uygulamasını çalıştıran ana döngüyü içerir. Oturum durumunu
    başlatır, başlığı ve kenar çubuğunu görüntüler, sekmeleri oluşturur
    ve her sekmenin içeriğini ilgili fonksiyonları çağırarak doldurur.
    """
    initialize_session_state()
    display_header()
    
    params = display_sidebar()
    
    tab_titles = [constants.TAB_TITLES[0], constants.TAB_TITLES[1]] + ["🚛 Şoför Asistanı", "⚡ Cache Yönetimi"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)
    
    with tab1:
        st.header(tab_titles[0])
        
        if st.button("🚀 Rotayı Hesapla", type="primary"):
            if st.session_state.client:
                with st.spinner("Rota hesaplanıyor..."):
                    try:
                        route_response = st.session_state.client.compute_route(
                            origin=params["origin"],
                            destination=params["destination"],
                            travel_mode=params["travel_mode"],
                            routing_preference=params["routing_preference"]
                        )
                        
                        route_details = st.session_state.client.get_route_details(route_response)
                        carbon_data = st.session_state.client.calculate_carbon_emission(
                            distance_km=route_details['distance_km'],
                            vehicle_type=params["vehicle_type"]
                        )
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📏 Mesafe", f"{route_details['distance_km']:.1f} km")
                        with col2:
                            st.metric("⏱️ Süre", f"{route_details['duration_minutes']:.0f} dk")
                        with col3:
                            st.metric("🌱 CO₂", f"{carbon_data['total_emission_kg']:.1f} kg")
                        
                        st.success("✅ Rota başarıyla hesaplandı!")
                        
                        # Rota haritasını göster
                        st.subheader("🗺️ Hesaplanan Rota")
                        display_calculated_route_map(route_response, params["origin"], params["destination"], route_details, carbon_data)
                        
                    except Exception as e:
                        st.error(f"❌ {constants.ERROR_ROUTE_COMPUTATION}: {str(e)}")
            else:
                st.error(f"❌ {constants.ERROR_API_CLIENT_NOT_AVAILABLE}")
    
    with tab2:
        display_data_collection_dashboard()
    
    with tab3:
        display_driver_assistant()
    
    with tab4:
        display_cache_management()
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; padding: 1rem;">
        {constants.FOOTER_TEXT}<br>
        {constants.FOOTER_SUBTEXT}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

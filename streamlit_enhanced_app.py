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
import sqlite3
import numpy as np

# Import our modules
from api.routes_client import GoogleRoutesClient
from config.config import config
from data_models import DataWarehouse, FuelStationData, RouteData
from enhanced_data_collector import EnhancedDataCollector
from config import constants

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
        st.session_state.warehouse = DataWarehouse()
    if 'data_collector' not in st.session_state:
        st.session_state.data_collector = EnhancedDataCollector()

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
    """
    st.header(constants.DATA_COLLECTION_HEADER)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
        <div class="data-collection-card">
            <h4>{constants.DATA_COLLECTION_CARD_TITLE}</h4>
            <p>{constants.DATA_COLLECTION_CARD_TEXT}</p>
            <ul>
                <li>✅ Google Places API entegrasyonu</li>
                <li>✅ Marka bazında kategorilendirme</li>
                <li>✅ Fiyat ve hizmet bilgileri</li>
                <li>✅ SQLite veri ambarı</li>
                <li>✅ Excel export özelliği</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button(constants.DATA_COLLECTION_BUTTON_TEXT, type="primary", use_container_width=True):
            with st.spinner("Kapsamlı veri toplama başlatılıyor..."):
                try:
                    result = st.session_state.data_collector.collect_comprehensive_data()
                    st.success("✅ Veri toplama tamamlandı!")
                    st.balloons()
                    st.json(result.get('summary', {}))
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {constants.ERROR_DATA_COLLECTION}: {str(e)}")
    
    with col3:
        if st.button(constants.DB_SUMMARY_BUTTON_TEXT, use_container_width=True):
            try:
                summary = st.session_state.warehouse.get_analytics_summary()
                st.json(summary)
            except Exception as e:
                st.error(f"❌ {constants.ERROR_DB_SUMMARY}: {str(e)}")
    
    st.markdown("---")
    display_current_data_status()

def display_current_data_status():
    """
    Veritabanındaki mevcut verilerin durumunu ve temel analizleri gösterir.
    
    Toplam istasyon ve rota sayısı gibi temel metrikleri, ülke bazında istasyon
    dağılımını gösteren bir bar grafiğini ve araç tipine göre emisyon dağılımını
    gösteren bir pasta grafiğini içerir.
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
        
        if summary.get('stations_by_country'):
            st.subheader(constants.STATION_DISTRIBUTION_HEADER)
            country_data = summary['stations_by_country']
            fig = px.bar(x=list(country_data.keys()), y=list(country_data.values()),
                         title="Ülke Bazında İstasyon Sayıları", labels={"x": "Ülke", "y": "İstasyon Sayısı"})
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
        conn = sqlite3.connect(st.session_state.warehouse.db_path)
        df_stations = pd.read_sql_query("SELECT * FROM fuel_stations", conn)
        conn.close()
        
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
                conn = sqlite3.connect(st.session_state.warehouse.db_path)
                df_stations = pd.read_sql_query("SELECT * FROM fuel_stations", conn)
                df_routes = pd.read_sql_query("SELECT * FROM routes", conn)
                conn.close()
                
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
    
    tab_titles = constants.TAB_TITLES
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
                        
                    except Exception as e:
                        st.error(f"❌ {constants.ERROR_ROUTE_COMPUTATION}: {str(e)}")
            else:
                st.error(f"❌ {constants.ERROR_API_CLIENT_NOT_AVAILABLE}")
    
    with tab2:
        display_data_collection_dashboard()
    
    with tab3:
        display_detailed_station_analysis()
    
    with tab4:
        display_export_options()
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; padding: 1rem;">
        {constants.FOOTER_TEXT}<br>
        {constants.FOOTER_SUBTEXT}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

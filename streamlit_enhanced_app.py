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

# Page configuration
st.set_page_config(
    page_title="Fuel2go - Akıllı Rota ve Veri Yönetimi",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    """Initialize session state variables"""
    if 'routes_data' not in st.session_state:
        st.session_state.routes_data = []
    if 'client' not in st.session_state:
        try:
            st.session_state.client = GoogleRoutesClient()
        except Exception as e:
            st.error(f"API istemcisi başlatılamadı: {str(e)}")
            st.session_state.client = None
    if 'warehouse' not in st.session_state:
        st.session_state.warehouse = DataWarehouse()
    if 'data_collector' not in st.session_state:
        st.session_state.data_collector = EnhancedDataCollector()

def display_header():
    """Display main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🚗 Fuel2go - Advanced Data Platform</h1>
        <h3>Akıllı Rota Optimizasyonu ve Kapsamlı Veri Yönetimi</h3>
        <p>Google Routes API + Avrupa Geneli Benzin İstasyonu Veri Platformu</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Display sidebar with controls"""
    st.sidebar.header("🎛️ Kontrol Paneli")
    
    # System status
    st.sidebar.subheader("📊 Sistem Durumu")
    
    # API status
    if st.session_state.client:
        st.sidebar.markdown('<span class="status-indicator status-active">✅ API Aktif</span>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<span class="status-indicator status-inactive">❌ API İnaktif</span>', unsafe_allow_html=True)
    
    # Database status
    try:
        summary = st.session_state.warehouse.get_analytics_summary()
        st.sidebar.markdown('<span class="status-indicator status-active">✅ Veritabanı Aktif</span>', unsafe_allow_html=True)
        st.sidebar.metric("Toplam İstasyon", summary.get('total_stations', 0))
        st.sidebar.metric("Toplam Rota", summary.get('total_routes', 0))
    except:
        st.sidebar.markdown('<span class="status-indicator status-inactive">❌ Veritabanı Hatası</span>', unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Route settings (existing code)
    st.sidebar.subheader("📍 Rota Ayarları")
    origin_lat = st.sidebar.number_input("Başlangıç Enlem", value=41.0082, format="%.6f", key="origin_lat")
    origin_lng = st.sidebar.number_input("Başlangıç Boylam", value=28.9784, format="%.6f", key="origin_lng")
    dest_lat = st.sidebar.number_input("Hedef Enlem", value=39.9334, format="%.6f", key="dest_lat")
    dest_lng = st.sidebar.number_input("Hedef Boylam", value=32.8597, format="%.6f", key="dest_lng")
    
    travel_mode = st.sidebar.selectbox("🚙 Seyahat Türü", ["DRIVE", "WALK", "BICYCLE", "TRANSIT"])
    routing_preference = st.sidebar.selectbox("⚡ Rota Tercihi", ["TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL", "FUEL_EFFICIENT"])
    vehicle_type = st.sidebar.selectbox("🚗 Araç Tipi", ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"])
    
    return {
        "origin": {"latitude": origin_lat, "longitude": origin_lng},
        "destination": {"latitude": dest_lat, "longitude": dest_lng},
        "travel_mode": travel_mode,
        "routing_preference": routing_preference,
        "vehicle_type": vehicle_type
    }

def display_data_collection_dashboard():
    """Ana veri toplama dashboard'u"""
    st.header("📊 Kapsamlı Veri Toplama Merkezi")
    
    # Ana kontrol paneli
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="data-collection-card">
            <h4>🌍 Avrupa Geneli Benzin İstasyonu Verisi</h4>
            <p>16 Avrupa ülkesinden kapsamlı benzin istasyonu verisi toplama sistemi</p>
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
        if st.button("🚀 Veri Toplama Başlat", type="primary", use_container_width=True):
            with st.spinner("Kapsamlı veri toplama başlatılıyor..."):
                try:
                    result = st.session_state.data_collector.collect_comprehensive_data()
                    st.success("✅ Veri toplama tamamlandı!")
                    st.balloons()
                    st.json(result.get('summary', {}))
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Veri toplama hatası: {str(e)}")
    
    with col3:
        if st.button("📈 Veritabanı Özet", use_container_width=True):
            try:
                summary = st.session_state.warehouse.get_analytics_summary()
                st.json(summary)
            except Exception as e:
                st.error(f"❌ Özet alınamadı: {str(e)}")
    
    # Mevcut veri durumu
    st.markdown("---")
    display_current_data_status()

def display_current_data_status():
    """Mevcut veri durumunu göster"""
    st.subheader("📊 Mevcut Veri Durumu")
    
    try:
        summary = st.session_state.warehouse.get_analytics_summary()
        
        # Ana metrikler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💾 Toplam İstasyon",
                value=summary.get('total_stations', 0)
            )
        
        with col2:
            st.metric(
                label="🗺️ Toplam Rota",
                value=summary.get('total_routes', 0)
            )
        
        with col3:
            avg_carbon = summary.get('avg_carbon_emission', 0)
            st.metric(
                label="🌱 Ort. Karbon (kg)",
                value=f"{avg_carbon:.1f}" if avg_carbon else "0"
            )
        
        with col4:
            avg_fuel = summary.get('avg_fuel_consumption', 0)
            st.metric(
                label="⛽ Ort. Yakıt (L)",
                value=f"{avg_fuel:.1f}" if avg_fuel else "0"
            )
        
        # Ülke dağılımı
        if summary.get('stations_by_country'):
            st.subheader("🌍 Ülke Bazında İstasyon Dağılımı")
            country_data = summary['stations_by_country']
            
            fig = px.bar(
                x=list(country_data.keys()),
                y=list(country_data.values()),
                title="Ülke Bazında İstasyon Sayıları",
                labels={"x": "Ülke", "y": "İstasyon Sayısı"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Araç tipi emisyon analizi
        if summary.get('emissions_by_vehicle'):
            st.subheader("🚗 Araç Tipi Bazında Ortalama Emisyon")
            emission_data = summary['emissions_by_vehicle']
            
            fig = px.pie(
                values=list(emission_data.values()),
                names=list(emission_data.keys()),
                title="Araç Tipi Bazında Emisyon Dağılımı"
            )
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Veri durumu gösterilemedi: {str(e)}")

def display_detailed_station_analysis():
    """Detaylı istasyon analizi"""
    st.header("🔍 Detaylı İstasyon Analizi")
    
    try:
        # Veritabanından tüm istasyonları al
        conn = sqlite3.connect(st.session_state.warehouse.db_path)
        df_stations = pd.read_sql_query("SELECT * FROM fuel_stations", conn)
        conn.close()
        
        if df_stations.empty:
            st.info("📄 Henüz istasyon verisi yok. Veri toplama işlemini başlatın.")
            return
        
        # Filtreleme seçenekleri
        col1, col2, col3 = st.columns(3)
        
        with col1:
            countries = df_stations['country'].unique().tolist() if 'country' in df_stations.columns else []
            selected_countries = st.multiselect("Ülke Seç", countries, default=countries[:5] if countries else [])
        
        with col2:
            brands = df_stations['brand'].unique().tolist() if 'brand' in df_stations.columns else []
            selected_brands = st.multiselect("Marka Seç", brands, default=brands[:5] if brands else [])
        
        with col3:
            min_rating = st.slider("Minimum Puan", 0.0, 5.0, 0.0, 0.1)
        
        # Filtrelenmiş veri
        filtered_df = df_stations.copy()
        if selected_countries and 'country' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['country'].isin(selected_countries)]
        if selected_brands and 'brand' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['brand'].isin(selected_brands)]
        if 'rating' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
        
        # Sonuçlar
        st.subheader(f"📋 Filtrelenmiş Sonuçlar ({len(filtered_df)} istasyon)")
        
        # Tablo görünümü
        if not filtered_df.empty:
            display_columns = ['name', 'brand', 'country', 'rating', 'review_count', 'address']
            available_columns = [col for col in display_columns if col in filtered_df.columns]
            st.dataframe(filtered_df[available_columns], use_container_width=True)
            
            # Harita görünümü
            if 'latitude' in filtered_df.columns and 'longitude' in filtered_df.columns:
                st.subheader("🗺️ İstasyon Haritası")
                display_stations_map(filtered_df)
        else:
            st.warning("⚠️ Filtreye uygun istasyon bulunamadı.")
    
    except Exception as e:
        st.error(f"❌ Analiz hatası: {str(e)}")

def display_stations_map(df_stations):
    """İstasyonları haritada göster"""
    try:
        if df_stations.empty:
            st.info("Gösterilecek istasyon yok")
            return
        
        # Harita merkezi hesapla
        center_lat = df_stations['latitude'].mean()
        center_lng = df_stations['longitude'].mean()
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=5)
        
        # Marka bazında renk kodlaması
        brand_colors = {
            'Shell': 'red',
            'BP': 'green', 
            'Total': 'blue',
            'Petrol Ofisi': 'orange',
            'Opet': 'purple',
            'Other': 'gray'
        }
        
        # İstasyonları ekle
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
        st.error(f"Harita görüntülenemiyor: {str(e)}")

def display_export_options():
    """Veri dışa aktarma seçenekleri"""
    st.header("📤 Veri Dışa Aktarma")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Excel Export")
        if st.button("Excel Dosyası İndir", type="primary"):
            try:
                # Veritabanından veri al
                conn = sqlite3.connect(st.session_state.warehouse.db_path)
                df_stations = pd.read_sql_query("SELECT * FROM fuel_stations", conn)
                df_routes = pd.read_sql_query("SELECT * FROM routes", conn)
                conn.close()
                
                # Excel dosyası oluştur
                filename = f"fuel2go_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    if not df_stations.empty:
                        df_stations.to_excel(writer, sheet_name='Stations', index=False)
                    if not df_routes.empty:
                        df_routes.to_excel(writer, sheet_name='Routes', index=False)
                    
                    # Özet sayfa
                    summary = st.session_state.warehouse.get_analytics_summary()
                    df_summary = pd.DataFrame([summary])
                    df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                st.success(f"✅ Excel dosyası oluşturuldu: {filename}")
                
            except Exception as e:
                st.error(f"❌ Excel export hatası: {str(e)}")
    
    with col2:
        st.subheader("🗃️ JSON Export")
        if st.button("JSON Dosyası İndir"):
            try:
                summary = st.session_state.warehouse.get_analytics_summary()
                filename = f"fuel2go_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
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
                st.error(f"❌ JSON export hatası: {str(e)}")

def main():
    """Main application function"""
    initialize_session_state()
    display_header()
    
    # Sidebar controls
    params = display_sidebar()
    
    # Ana sekme yapısı
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚗 Rota Hesaplama", 
        "📊 Veri Toplama", 
        "🔍 Analiz", 
        "📤 Export"
    ])
    
    with tab1:
        # Mevcut rota hesaplama (basitleştirilmiş)
        st.header("🚗 Rota Hesaplama")
        
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
                        st.error(f"❌ Rota hesaplama hatası: {str(e)}")
            else:
                st.error("❌ API istemcisi mevcut değil")
    
    with tab2:
        display_data_collection_dashboard()
    
    with tab3:
        display_detailed_station_analysis()
    
    with tab4:
        display_export_options()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        🌱 <strong>Fuel2go</strong> - Gelişmiş Veri Platformu<br>
        Google Routes API + Avrupa Geneli Benzin İstasyonu Veritabanı
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

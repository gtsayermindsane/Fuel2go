#!/usr/bin/env python3
"""
Fuel2go - Streamlit Dashboard
Akıllı rota optimizasyonu ve karbon emisyon analizi için web arayüzü
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

# Import our API client
from api.routes_client import GoogleRoutesClient
from config.config import config

# Page configuration
st.set_page_config(
    page_title="Fuel2go - Akıllı Rota Optimizasyonu",
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
    .route-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #e9ecef;
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

def display_header():
    """Display main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🚗 Fuel2go</h1>
        <h3>Akıllı Rota Optimizasyonu ve Karbon Emisyon Analizi</h3>
        <p>Google Routes API ile desteklenen çevresel etki analizi platformu</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Display sidebar with controls"""
    st.sidebar.header("🎛️ Rota Ayarları")
    
    # API key status
    if st.session_state.client:
        st.sidebar.success("✅ API bağlantısı aktif")
    else:
        st.sidebar.error("❌ API bağlantısı yok")
        st.sidebar.info("💡 .env dosyasında GOOGLE_ROUTES_API_KEY ayarlayın")
    
    st.sidebar.markdown("---")
    
    # Route settings
    st.sidebar.subheader("📍 Başlangıç Noktası")
    origin_lat = st.sidebar.number_input("Enlem", value=41.0082, format="%.6f", key="origin_lat")
    origin_lng = st.sidebar.number_input("Boylam", value=28.9784, format="%.6f", key="origin_lng")
    
    st.sidebar.subheader("🎯 Hedef")
    dest_lat = st.sidebar.number_input("Enlem", value=39.9334, format="%.6f", key="dest_lat")
    dest_lng = st.sidebar.number_input("Boylam", value=32.8597, format="%.6f", key="dest_lng")
    
    st.sidebar.markdown("---")
    
    # Travel options
    travel_mode = st.sidebar.selectbox(
        "🚙 Seyahat Türü",
        ["DRIVE", "WALK", "BICYCLE", "TRANSIT"],
        index=0
    )
    
    routing_preference = st.sidebar.selectbox(
        "⚡ Rota Tercihi",
        ["TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL", "FUEL_EFFICIENT"],
        index=0
    )
    
    vehicle_type = st.sidebar.selectbox(
        "🚗 Araç Tipi",
        ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"],
        index=0,
        format_func=lambda x: {
            "gasoline_car": "Benzinli Araç",
            "diesel_car": "Dizel Araç", 
            "electric_car": "Elektrikli Araç",
            "hybrid_car": "Hibrit Araç"
        }[x]
    )
    
    alternative_routes = st.sidebar.checkbox("🔄 Alternatif rotalar", value=True)
    
    return {
        "origin": {"latitude": origin_lat, "longitude": origin_lng},
        "destination": {"latitude": dest_lat, "longitude": dest_lng},
        "travel_mode": travel_mode,
        "routing_preference": routing_preference,
        "vehicle_type": vehicle_type,
        "compute_alternative_routes": alternative_routes
    }

def calculate_route(params: Dict):
    """Calculate route using Google Routes API"""
    if not st.session_state.client:
        st.error("API istemcisi mevcut değil")
        return None
    
    try:
        with st.spinner("🔄 Rota hesaplanıyor..."):
            route_response = st.session_state.client.compute_route(
                origin=params["origin"],
                destination=params["destination"],
                travel_mode=params["travel_mode"],
                routing_preference=params["routing_preference"],
                compute_alternative_routes=params["compute_alternative_routes"]
            )
            
            # Process route details
            route_details = st.session_state.client.get_route_details(route_response)
            
            # Calculate carbon emission
            carbon_data = st.session_state.client.calculate_carbon_emission(
                distance_km=route_details['distance_km'],
                vehicle_type=params["vehicle_type"]
            )
            
            # Get traffic conditions
            traffic_info = st.session_state.client.get_traffic_conditions(route_response)
            
            # Store in session state
            route_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "params": params,
                "route_details": route_details,
                "carbon_data": carbon_data,
                "traffic_info": traffic_info,
                "raw_response": route_response
            }
            
            st.session_state.routes_data.append(route_data)
            
            return route_data
            
    except Exception as e:
        st.error(f"Rota hesaplama hatası: {str(e)}")
        return None

def display_route_metrics(route_data: Dict):
    """Display route metrics"""
    route_details = route_data["route_details"]
    carbon_data = route_data["carbon_data"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📏 Mesafe",
            value=f"{route_details['distance_km']:.1f} km"
        )
    
    with col2:
        st.metric(
            label="⏱️ Süre",
            value=f"{route_details['duration_minutes']:.0f} dk"
        )
    
    with col3:
        st.metric(
            label="🌱 CO₂ Emisyonu",
            value=f"{carbon_data['total_emission_kg']:.1f} kg"
        )
    
    with col4:
        avg_speed = route_details['distance_km'] / (route_details['duration_minutes'] / 60)
        st.metric(
            label="⚡ Ortalama Hız",
            value=f"{avg_speed:.0f} km/h"
        )

def display_map(route_data: Dict):
    """Display route on map"""
    origin = route_data["params"]["origin"]
    destination = route_data["params"]["destination"]
    
    # Create map centered between origin and destination
    center_lat = (origin["latitude"] + destination["latitude"]) / 2
    center_lng = (origin["longitude"] + destination["longitude"]) / 2
    
    m = folium.Map(location=[center_lat, center_lng], zoom_start=7)
    
    # Add origin marker
    folium.Marker(
        [origin["latitude"], origin["longitude"]],
        popup="Başlangıç",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    
    # Add destination marker
    folium.Marker(
        [destination["latitude"], destination["longitude"]],
        popup="Hedef",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)
    
    # Add route line if polyline is available
    route_details = route_data["route_details"]
    if route_details.get("polyline"):
        try:
            import polyline
            coordinates = polyline.decode(route_details["polyline"])
            folium.PolyLine(
                coordinates,
                weight=5,
                color="blue",
                opacity=0.8
            ).add_to(m)
        except:
            pass
    
    return m

def display_carbon_comparison():
    """Display carbon emission comparison chart"""
    if not st.session_state.routes_data:
        return
    
    st.subheader("🌱 Araç Tiplerine Göre Karbon Emisyonu Karşılaştırması")
    
    # Get latest route distance
    latest_route = st.session_state.routes_data[-1]
    distance_km = latest_route["route_details"]["distance_km"]
    
    # Calculate emissions for all vehicle types
    vehicle_types = ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"]
    vehicle_names = ["Benzinli", "Dizel", "Elektrikli", "Hibrit"]
    
    emissions = []
    for vehicle_type in vehicle_types:
        carbon_data = st.session_state.client.calculate_carbon_emission(
            distance_km=distance_km,
            vehicle_type=vehicle_type
        )
        emissions.append(carbon_data["total_emission_kg"])
    
    # Create bar chart
    fig = px.bar(
        x=vehicle_names,
        y=emissions,
        title=f"Karbon Emisyonu Karşılaştırması ({distance_km:.1f} km rota için)",
        labels={"x": "Araç Tipi", "y": "CO₂ Emisyonu (kg)"},
        color=emissions,
        color_continuous_scale="RdYlGn_r"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_route_history():
    """Display route calculation history"""
    if not st.session_state.routes_data:
        st.info("📊 Henüz hesaplanan rota yok")
        return
    
    st.subheader("📈 Rota Geçmişi")
    
    # Create dataframe from route history
    history_data = []
    for i, route in enumerate(st.session_state.routes_data):
        history_data.append({
            "Sıra": i + 1,
            "Zaman": route["timestamp"],
            "Mesafe (km)": f"{route['route_details']['distance_km']:.1f}",
            "Süre (dk)": f"{route['route_details']['duration_minutes']:.0f}",
            "Araç Tipi": route["params"]["vehicle_type"],
            "CO₂ (kg)": f"{route['carbon_data']['total_emission_kg']:.1f}"
        })
    
    df = pd.DataFrame(history_data)
    st.dataframe(df, use_container_width=True)
    
    # Clear history button
    if st.button("🗑️ Geçmişi Temizle"):
        st.session_state.routes_data = []
        st.rerun()

def main():
    """Main application function"""
    initialize_session_state()
    display_header()
    
    # Sidebar controls
    params = display_sidebar()
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 🎯 Rota Hesapla")
        if st.button("🚀 Rotayı Hesapla", type="primary", use_container_width=True):
            route_data = calculate_route(params)
            if route_data:
                st.success("✅ Rota başarıyla hesaplandı!")
    
    with col1:
        # Display latest route if available
        if st.session_state.routes_data:
            latest_route = st.session_state.routes_data[-1]
            
            st.markdown("### 📊 Rota Detayları")
            display_route_metrics(latest_route)
            
            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["🗺️ Harita", "📈 Analiz", "📋 Detaylar"])
            
            with tab1:
                map_obj = display_map(latest_route)
                st_folium(map_obj, width=700, height=500)
            
            with tab2:
                display_carbon_comparison()
            
            with tab3:
                st.json(latest_route["route_details"])
        
        else:
            st.info("👆 Rota hesaplamak için yukarıdaki butonu kullanın")
    
    st.markdown("---")
    
    # Route history
    display_route_history()
    
    # Footer
    st.markdown("""
    ---
    <div style="text-align: center; color: #666; padding: 1rem;">
        🌱 <strong>Fuel2go</strong> - Sürdürülebilir bir gelecek için akıllı rota seçimi!<br>
        Google Routes API ile desteklenen karbon emisyon optimizasyonu
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

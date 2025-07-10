#!/usr/bin/env python3
"""
Example usage of Google Routes API client for Istanbul-Ankara route
"""

import json
import os
from datetime import datetime, timezone
from api.routes_client import GoogleRoutesClient

def main():
    """Main function to demonstrate API usage"""
    
    # Make sure to set your API key in .env file
    if not os.path.exists('.env'):
        print("Error: .env file not found. Please copy .env.example to .env and add your API key.")
        return
    
    # Initialize client
    print("🚀 Initializing Google Routes API client...")
    client = GoogleRoutesClient()
    
    # Define Istanbul and Ankara coordinates
    istanbul = {
        "latitude": 41.0082,
        "longitude": 28.9784
    }
    
    ankara = {
        "latitude": 39.9334,
        "longitude": 32.8597
    }
    
    print(f"📍 Route: Istanbul ({istanbul['latitude']}, {istanbul['longitude']}) -> Ankara ({ankara['latitude']}, {ankara['longitude']})")
    
    try:
        # Example 1: Basic route calculation
        print("\n🔄 Computing basic route...")
        route_response = client.compute_route(
            origin=istanbul,
            destination=ankara,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE"
        )
        
        # Extract route details
        route_details = client.get_route_details(route_response)
        
        print(f"✅ Route calculated successfully:")
        print(f"   Distance: {route_details['distance_km']:.2f} km")
        print(f"   Duration: {route_details['duration_minutes']:.1f} minutes")
        print(f"   Legs: {len(route_details['legs'])}")
        
        # Calculate carbon emission
        carbon_data = client.calculate_carbon_emission(
            distance_km=route_details['distance_km'],
            vehicle_type="gasoline_car"
        )
        
        print(f"🌱 Carbon Emission (Gasoline Car):")
        print(f"   Total: {carbon_data['total_emission_kg']:.2f} kg CO2")
        print(f"   Per km: {carbon_data['emission_factor_kg_per_km']:.3f} kg CO2/km")
        
        # Get traffic conditions
        traffic_info = client.get_traffic_conditions(route_response)
        print(f"🚦 Traffic Info:")
        print(f"   Duration in traffic: {traffic_info['duration_in_traffic_minutes']:.1f} minutes")
        
        # Save sample data
        sample_data = {
            "request_info": {
                "origin": istanbul,
                "destination": ankara,
                "travel_mode": "DRIVE",
                "routing_preference": "TRAFFIC_AWARE",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "route_response": route_response,
            "processed_data": {
                "route_details": route_details,
                "carbon_emission": carbon_data,
                "traffic_conditions": traffic_info
            }
        }
        
        # Save to docs/sample_data
        os.makedirs("docs/sample_data", exist_ok=True)
        with open("docs/sample_data/istanbul_ankara_route.json", "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sample data saved to: docs/sample_data/istanbul_ankara_route.json")
        
        # Example 2: Alternative routes
        print("\n🔄 Computing alternative routes...")
        alt_route_response = client.compute_route(
            origin=istanbul,
            destination=ankara,
            travel_mode="DRIVE",
            routing_preference="TRAFFIC_AWARE",
            compute_alternative_routes=True
        )
        
        if "routes" in alt_route_response and len(alt_route_response["routes"]) > 1:
            print(f"✅ Found {len(alt_route_response['routes'])} alternative routes")
            
            for i, route in enumerate(alt_route_response["routes"]):
                distance = route.get("distanceMeters", 0) / 1000
                duration = int(route.get("duration", "0s").replace("s", "")) / 60
                print(f"   Route {i+1}: {distance:.2f} km, {duration:.1f} min")
        
        # Save alternative routes data
        alt_sample_data = {
            "request_info": {
                "origin": istanbul,
                "destination": ankara,
                "travel_mode": "DRIVE",
                "routing_preference": "TRAFFIC_AWARE",
                "compute_alternative_routes": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "route_response": alt_route_response
        }
        
        with open("docs/sample_data/istanbul_ankara_alternative_routes.json", "w", encoding="utf-8") as f:
            json.dump(alt_sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Alternative routes data saved to: docs/sample_data/istanbul_ankara_alternative_routes.json")
        
        # Example 3: Different vehicle types carbon comparison
        print("\n🚗 Carbon emission comparison by vehicle type:")
        vehicle_types = ["gasoline_car", "diesel_car", "electric_car", "hybrid_car"]
        
        for vehicle in vehicle_types:
            carbon = client.calculate_carbon_emission(
                distance_km=route_details['distance_km'],
                vehicle_type=vehicle
            )
            print(f"   {vehicle.replace('_', ' ').title()}: {carbon['total_emission_kg']:.2f} kg CO2")
        
        print("\n🎉 Data collection completed successfully!")
        print("📊 Ready for machine learning model training and analysis.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Make sure your API key is correctly set in .env file")

if __name__ == "__main__":
    main()
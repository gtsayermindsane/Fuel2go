#!/usr/bin/env python3
"""
Google Polyline Decoder
Google Routes API'den gelen polyline'ları haritada çizmek için decode eder
"""

def decode_polyline(polyline_str):
    """
    Google polyline encoding'ini decode eder.
    
    Args:
        polyline_str (str): Encoded polyline string
        
    Returns:
        List[Tuple[float, float]]: Koordinat listesi [(lat, lng), ...]
    """
    index = 0
    lat = 0
    lng = 0
    coordinates = []
    
    while index < len(polyline_str):
        # Latitude decode
        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat
        
        # Longitude decode
        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng
        
        coordinates.append((lat / 1e5, lng / 1e5))
    
    return coordinates
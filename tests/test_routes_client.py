import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from api.routes_client import GoogleRoutesClient
from config import config
import requests

class TestGoogleRoutesClient(unittest.TestCase):
    """Google Routes API client test cases"""
    
    def setUp(self):
        """Test setup"""
        self.client = GoogleRoutesClient()
        self.sample_origin = {"latitude": 41.0082, "longitude": 28.9784}
        self.sample_destination = {"latitude": 39.9334, "longitude": 32.8597}
        
        # Sample API response
        self.sample_response = {
            "routes": [{
                "distanceMeters": 454000,
                "duration": "18300s",
                "polyline": {
                    "encodedPolyline": "sample_polyline"
                },
                "legs": [{
                    "distanceMeters": 454000,
                    "duration": "18300s",
                    "startLocation": {
                        "latLng": {"latitude": 41.0082, "longitude": 28.9784}
                    },
                    "endLocation": {
                        "latLng": {"latitude": 39.9334, "longitude": 32.8597}
                    },
                    "steps": []
                }]
            }]
        }
    
    def test_init(self):
        """Test client initialization"""
        self.assertIsNotNone(self.client.config)
        self.assertIsNotNone(self.client.session)
        self.assertEqual(self.client.min_interval, 1.0)  # 60 requests per minute
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        import time
        
        # First call should not sleep
        start_time = time.time()
        self.client._rate_limit()
        first_call_time = time.time() - start_time
        
        # Second call should sleep
        start_time = time.time()
        self.client._rate_limit()
        second_call_time = time.time() - start_time
        
        self.assertLess(first_call_time, 0.1)  # First call should be quick
        self.assertGreater(second_call_time, 0.5)  # Second call should wait
    
    @patch('requests.Session.post')
    def test_compute_route_success(self, mock_post):
        """Test successful route computation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.client.compute_route(
            origin=self.sample_origin,
            destination=self.sample_destination
        )
        
        # Assertions
        self.assertEqual(result, self.sample_response)
        mock_post.assert_called_once()
        
        # Check request body
        call_args = mock_post.call_args
        request_body = call_args[1]['json']
        
        self.assertEqual(request_body['origin']['location']['latLng']['latitude'], 41.0082)
        self.assertEqual(request_body['destination']['location']['latLng']['latitude'], 39.9334)
        self.assertEqual(request_body['travelMode'], 'DRIVE')
    
    @patch('requests.Session.post')
    def test_compute_route_with_waypoints(self, mock_post):
        """Test route computation with waypoints"""
        mock_response = Mock()
        mock_response.json.return_value = self.sample_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        waypoints = [{"latitude": 40.7369, "longitude": 31.6061}]
        
        self.client.compute_route(
            origin=self.sample_origin,
            destination=self.sample_destination,
            waypoints=waypoints
        )
        
        # Check waypoints in request
        call_args = mock_post.call_args
        request_body = call_args[1]['json']
        
        self.assertIn('intermediates', request_body)
        self.assertEqual(len(request_body['intermediates']), 1)
        self.assertEqual(request_body['intermediates'][0]['location']['latLng']['latitude'], 40.7369)
    
    @patch('requests.Session.post')
    def test_compute_route_api_error(self, mock_post):
        """Test API error handling"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_post.return_value = mock_response
        
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.compute_route(
                origin=self.sample_origin,
                destination=self.sample_destination
            )
    
    def test_get_route_details(self):
        """Test route details extraction"""
        route_details = self.client.get_route_details(self.sample_response)
        
        self.assertEqual(route_details['distance_km'], 454.0)
        self.assertEqual(route_details['duration_minutes'], 305.0)
        self.assertEqual(route_details['polyline'], 'sample_polyline')
        self.assertEqual(len(route_details['legs']), 1)
    
    def test_get_route_details_no_routes(self):
        """Test route details with no routes"""
        empty_response = {"routes": []}
        
        with self.assertRaises(ValueError):
            self.client.get_route_details(empty_response)
    
    def test_calculate_carbon_emission(self):
        """Test carbon emission calculation"""
        # Test gasoline car
        result = self.client.calculate_carbon_emission(100, "gasoline_car")
        
        self.assertEqual(result['distance_km'], 100)
        self.assertEqual(result['vehicle_type'], 'gasoline_car')
        self.assertEqual(result['emission_factor_kg_per_km'], 0.192)
        self.assertEqual(result['total_emission_kg'], 19.2)
        self.assertEqual(result['total_emission_tons'], 0.0192)
        
        # Test electric car
        result = self.client.calculate_carbon_emission(100, "electric_car")
        self.assertEqual(result['total_emission_kg'], 6.7)
        
        # Test unknown vehicle type (should default to gasoline)
        result = self.client.calculate_carbon_emission(100, "unknown_car")
        self.assertEqual(result['total_emission_kg'], 19.2)
    
    def test_get_traffic_conditions(self):
        """Test traffic conditions extraction"""
        traffic_info = self.client.get_traffic_conditions(self.sample_response)
        
        self.assertEqual(traffic_info['duration_in_traffic_seconds'], 18300)
        self.assertEqual(traffic_info['duration_in_traffic_minutes'], 305.0)
        self.assertTrue(traffic_info['has_traffic_data'])
        self.assertIn('route_computed_at', traffic_info)
    
    def test_get_traffic_conditions_no_routes(self):
        """Test traffic conditions with no routes"""
        empty_response = {"routes": []}
        
        traffic_info = self.client.get_traffic_conditions(empty_response)
        self.assertEqual(traffic_info['traffic_conditions'], 'no_data')

class TestConfigValidation(unittest.TestCase):
    """Test configuration validation"""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_api_key(self):
        """Test behavior when API key is missing"""
        with self.assertRaises(ValueError):
            from config import Config
            config = Config()
            config.validate_api_keys()
    
    @patch.dict('os.environ', {'GOOGLE_ROUTES_API_KEY': 'test_key'})
    def test_valid_api_key(self):
        """Test behavior with valid API key"""
        from config import Config
        config = Config()
        self.assertTrue(config.validate_api_keys())
    
    def test_get_headers(self):
        """Test header generation"""
        from config import Config
        config = Config()
        config.google_routes_api_key = 'test_key'
        
        headers = config.get_headers()
        
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['X-Goog-Api-Key'], 'test_key')
        self.assertIn('X-Goog-FieldMask', headers)

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    @patch('requests.Session.post')
    def test_full_workflow(self, mock_post):
        """Test complete workflow"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "routes": [{
                "distanceMeters": 454000,
                "duration": "18300s",
                "polyline": {"encodedPolyline": "test_polyline"},
                "legs": [{
                    "distanceMeters": 454000,
                    "duration": "18300s",
                    "startLocation": {"latLng": {"latitude": 41.0082, "longitude": 28.9784}},
                    "endLocation": {"latLng": {"latitude": 39.9334, "longitude": 32.8597}},
                    "steps": []
                }]
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Initialize client
        client = GoogleRoutesClient()
        
        # Compute route
        route_response = client.compute_route(
            origin={"latitude": 41.0082, "longitude": 28.9784},
            destination={"latitude": 39.9334, "longitude": 32.8597}
        )
        
        # Process results
        route_details = client.get_route_details(route_response)
        carbon_data = client.calculate_carbon_emission(route_details['distance_km'])
        traffic_info = client.get_traffic_conditions(route_response)
        
        # Assertions
        self.assertEqual(route_details['distance_km'], 454.0)
        self.assertEqual(carbon_data['total_emission_kg'], 87.168)
        self.assertEqual(traffic_info['duration_in_traffic_minutes'], 305.0)

if __name__ == '__main__':
    unittest.main()
import unittest
import pandas as pd
import numpy as np
import json
import tempfile
import os
from utils.data_preprocessing import RouteDataProcessor

class TestRouteDataProcessor(unittest.TestCase):
    """Test cases for RouteDataProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = RouteDataProcessor()
        
        # Create sample data
        self.sample_route_data = {
            "routes": [{
                "id": "test_route_1",
                "origin": {"latitude": 41.0082, "longitude": 28.9784, "name": "Istanbul"},
                "destination": {"latitude": 39.9334, "longitude": 32.8597, "name": "Ankara"},
                "routing_preference": "TRAFFIC_AWARE",
                "travel_mode": "DRIVE",
                "metrics": {
                    "distance_km": 454.0,
                    "duration_minutes": 305.0,
                    "fuel_consumption_liters": 36.32,
                    "carbon_emission_kg": 87.168,
                    "traffic_delay_minutes": 45.0,
                    "toll_cost_try": 89.50
                },
                "weather_conditions": {
                    "temperature_celsius": 22,
                    "precipitation_mm": 0,
                    "wind_speed_kmh": 15,
                    "visibility_km": 10
                },
                "road_conditions": {
                    "construction_zones": 2,
                    "accident_reports": 1,
                    "average_speed_kmh": 89.5
                }
            }]
        }
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        
        # Write sample data to temp file
        with open(os.path.join(self.temp_dir, 'test_routes.json'), 'w') as f:
            json.dump(self.sample_route_data, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test processor initialization"""
        self.assertIsNotNone(self.processor.scaler)
        self.assertIsInstance(self.processor.feature_columns, list)
        self.assertIsInstance(self.processor.target_columns, list)
        self.assertGreater(len(self.processor.feature_columns), 0)
    
    def test_extract_route_features(self):
        """Test feature extraction from route data"""
        route = self.sample_route_data['routes'][0]
        features = self.processor._extract_route_features(route)
        
        # Check that key features are extracted
        self.assertEqual(features['distance_km'], 454.0)
        self.assertEqual(features['duration_minutes'], 305.0)
        self.assertEqual(features['carbon_emission_kg'], 87.168)
        self.assertEqual(features['temperature_celsius'], 22)
        self.assertEqual(features['construction_zones'], 2)
        self.assertEqual(features['routing_preference'], 'TRAFFIC_AWARE')
        self.assertEqual(features['origin_lat'], 41.0082)
        self.assertEqual(features['dest_lat'], 39.9334)
    
    def test_load_route_data(self):
        """Test loading route data from files"""
        df = self.processor.load_route_data(self.temp_dir)
        
        # Check DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        
        # Check that key columns exist
        expected_columns = ['distance_km', 'duration_minutes', 'carbon_emission_kg']
        for col in expected_columns:
            self.assertIn(col, df.columns)
    
    def test_clean_data(self):
        """Test data cleaning functionality"""
        # Create dirty data
        dirty_data = pd.DataFrame({
            'distance_km': [100, 200, -50, 1000000, np.nan],
            'duration_minutes': [60, 120, 90, 30, 150],
            'carbon_emission_kg': [20, 40, 30, 2000000, 35],
            'temperature_celsius': [20, 25, -100, 50, 22]
        })
        
        cleaned_data = self.processor._clean_data(dirty_data)
        
        # Check that negative values are removed or fixed
        self.assertTrue((cleaned_data['distance_km'] >= 0).all())
        
        # Check that NaN values are filled
        self.assertFalse(cleaned_data.isnull().any().any())
        
        # Check that average_speed_kmh is calculated if possible
        if 'average_speed_kmh' in cleaned_data.columns:
            self.assertTrue((cleaned_data['average_speed_kmh'] >= 0).all())
    
    def test_generate_synthetic_data(self):
        """Test synthetic data generation"""
        synthetic_df = self.processor.generate_synthetic_data(n_samples=100)
        
        # Check DataFrame structure
        self.assertEqual(len(synthetic_df), 100)
        self.assertGreater(len(synthetic_df.columns), 10)
        
        # Check that key columns exist
        expected_columns = [
            'distance_km', 'duration_minutes', 'carbon_emission_kg',
            'fuel_consumption_liters', 'temperature_celsius'
        ]
        for col in expected_columns:
            self.assertIn(col, synthetic_df.columns)
        
        # Check value ranges
        self.assertTrue((synthetic_df['distance_km'] >= 50).all())
        self.assertTrue((synthetic_df['distance_km'] <= 1000).all())
        self.assertTrue((synthetic_df['duration_minutes'] > 0).all())
        self.assertTrue((synthetic_df['carbon_emission_kg'] > 0).all())
    
    def test_prepare_ml_data(self):
        """Test ML data preparation"""
        # First create some test data
        synthetic_df = self.processor.generate_synthetic_data(n_samples=50)
        
        # Save to temp file
        synthetic_df.to_json(os.path.join(self.temp_dir, 'synthetic_data.json'), orient='records')
        
        # Prepare ML data
        X, y = self.processor.prepare_ml_data(self.temp_dir, target_col='carbon_emission_kg')
        
        # Check shapes
        self.assertEqual(X.shape[0], y.shape[0])
        self.assertGreater(X.shape[1], 0)
        
        # Check that data is normalized (mean should be close to 0)
        self.assertAlmostEqual(np.mean(X), 0, places=1)
    
    def test_feature_importance_analysis(self):
        """Test feature importance analysis"""
        # Generate synthetic data
        synthetic_df = self.processor.generate_synthetic_data(n_samples=100)
        
        # Prepare data
        feature_cols = ['distance_km', 'duration_minutes', 'temperature_celsius']
        X = synthetic_df[feature_cols].values
        y = synthetic_df['carbon_emission_kg'].values
        
        # Normalize
        X = self.processor.scaler.fit_transform(X)
        
        # Analyze importance
        importance_df = self.processor.create_feature_importance_analysis(X, y, feature_cols)
        
        # Check result structure
        self.assertEqual(len(importance_df), len(feature_cols))
        self.assertIn('feature', importance_df.columns)
        self.assertIn('overall_score', importance_df.columns)
        self.assertIn('rf_importance', importance_df.columns)
        
        # Check that scores are reasonable
        self.assertTrue((importance_df['overall_score'] >= 0).all())
        self.assertTrue((importance_df['overall_score'] <= 1).all())
    
    def test_save_processed_data(self):
        """Test saving processed data"""
        # Create test data
        test_df = pd.DataFrame({
            'distance_km': [100, 200, 300],
            'duration_minutes': [60, 120, 180],
            'carbon_emission_kg': [20, 40, 60]
        })
        
        # Save data
        output_path = os.path.join(self.temp_dir, 'test_output')
        self.processor.save_processed_data(test_df, output_path)
        
        # Check that files were created
        self.assertTrue(os.path.exists(f"{output_path}.csv"))
        self.assertTrue(os.path.exists(f"{output_path}.json"))
        self.assertTrue(os.path.exists(f"{output_path}_stats.json"))
        
        # Check CSV content
        loaded_df = pd.read_csv(f"{output_path}.csv")
        self.assertEqual(len(loaded_df), 3)
        
        # Check stats file
        with open(f"{output_path}_stats.json", 'r') as f:
            stats = json.load(f)
        
        self.assertEqual(stats['total_samples'], 3)
        self.assertIn('features', stats)
        self.assertIn('statistics', stats)
    
    def test_handle_missing_target_variable(self):
        """Test handling when target variable is missing"""
        # Create data without carbon_emission_kg
        test_data = {
            "routes": [{
                "metrics": {
                    "distance_km": 100,
                    "duration_minutes": 60
                }
            }]
        }
        
        # Write to temp file
        with open(os.path.join(self.temp_dir, 'no_target.json'), 'w') as f:
            json.dump(test_data, f)
        
        # Should estimate carbon emission from distance
        X, y = self.processor.prepare_ml_data(self.temp_dir, target_col='carbon_emission_kg')
        
        # Check that target was estimated
        self.assertGreater(y[0], 0)  # Should have estimated some emission
    
    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with non-existent directory
        with self.assertRaises(FileNotFoundError):
            self.processor.load_route_data('/non/existent/path')
        
        # Test with invalid target column that can't be estimated
        with self.assertRaises(ValueError):
            self.processor.prepare_ml_data(self.temp_dir, target_col='invalid_column')

class TestDataValidation(unittest.TestCase):
    """Test data validation and edge cases"""
    
    def setUp(self):
        self.processor = RouteDataProcessor()
    
    def test_outlier_detection(self):
        """Test outlier detection and removal"""
        # Create data with outliers
        data_with_outliers = pd.DataFrame({
            'distance_km': [100, 200, 300, 10000, 150],  # 10000 is an outlier
            'duration_minutes': [60, 120, 180, 600, 90],
            'carbon_emission_kg': [20, 40, 60, 2000, 30]  # 2000 is an outlier
        })
        
        cleaned_data = self.processor._clean_data(data_with_outliers)
        
        # Outliers should be removed
        self.assertLess(len(cleaned_data), len(data_with_outliers))
        self.assertTrue((cleaned_data['distance_km'] < 5000).all())
        self.assertTrue((cleaned_data['carbon_emission_kg'] < 1000).all())
    
    def test_categorical_encoding(self):
        """Test categorical variable encoding"""
        # Create data with categorical variables
        test_data = pd.DataFrame({
            'distance_km': [100, 200, 300],
            'routing_preference': ['TRAFFIC_AWARE', 'FUEL_EFFICIENT', 'TRAFFIC_AWARE'],
            'travel_mode': ['DRIVE', 'DRIVE', 'DRIVE']
        })
        
        # Process categorical columns
        categorical_cols = test_data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col not in self.processor.label_encoders:
                from sklearn.preprocessing import LabelEncoder
                self.processor.label_encoders[col] = LabelEncoder()
                test_data[col] = self.processor.label_encoders[col].fit_transform(test_data[col])
        
        # Check that categorical data is now numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(test_data['routing_preference']))
        self.assertTrue(pd.api.types.is_numeric_dtype(test_data['travel_mode']))

if __name__ == '__main__':
    unittest.main()
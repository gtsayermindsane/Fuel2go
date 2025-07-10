import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import os
import logging
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class RouteDataProcessor:
    """
    Veri ön işleme ve makine öğrenimi için hazırlık sınıfı
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = [
            'distance_km', 'duration_minutes', 'traffic_delay_minutes',
            'temperature_celsius', 'precipitation_mm', 'wind_speed_kmh',
            'visibility_km', 'construction_zones', 'accident_reports',
            'average_speed_kmh', 'toll_cost_try'
        ]
        self.target_columns = [
            'fuel_consumption_liters', 'carbon_emission_kg', 'duration_minutes'
        ]
        
    def load_route_data(self, data_path: str) -> pd.DataFrame:
        """
        JSON dosyalarından rota verilerini yükle
        
        Args:
            data_path: Veri klasörü yolu
            
        Returns:
            DataFrame: Temizlenmiş rota verileri
        """
        all_routes = []
        
        # Klasördeki tüm JSON dosyalarını oku
        for filename in os.listdir(data_path):
            if filename.endswith('.json') and filename != 'README.md':
                file_path = os.path.join(data_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Farklı JSON yapılarını handle et
                    if 'routes' in data:
                        # multiple_routes_comparison.json formatı
                        for route in data['routes']:
                            route_data = self._extract_route_features(route)
                            all_routes.append(route_data)
                    elif 'processed_data' in data:
                        # Single route format
                        route_data = self._extract_single_route_features(data)
                        all_routes.append(route_data)
                        
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
                    continue
        
        if not all_routes:
            raise ValueError("No valid route data found")
            
        df = pd.DataFrame(all_routes)
        return self._clean_data(df)
    
    def _extract_route_features(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rota verilerinden özellik çıkarımı
        """
        features = {}
        
        # Temel metrikler
        if 'metrics' in route:
            features.update(route['metrics'])
        
        # Lokasyon bilgileri
        if 'origin' in route:
            features['origin_lat'] = route['origin']['latitude']
            features['origin_lon'] = route['origin']['longitude']
        if 'destination' in route:
            features['dest_lat'] = route['destination']['latitude']
            features['dest_lon'] = route['destination']['longitude']
        
        # Rota tercihleri
        features['routing_preference'] = route.get('routing_preference', 'TRAFFIC_AWARE')
        features['travel_mode'] = route.get('travel_mode', 'DRIVE')
        
        # Hava durumu
        if 'weather_conditions' in route:
            features.update(route['weather_conditions'])
        
        # Yol koşulları
        if 'road_conditions' in route:
            features.update(route['road_conditions'])
        
        # Zaman bilgileri
        features['timestamp'] = datetime.now().isoformat()
        
        return features
    
    def _extract_single_route_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tek rota verisinden özellik çıkarımı
        """
        features = {}
        
        # Request info
        if 'request_info' in data:
            req_info = data['request_info']
            features['origin_lat'] = req_info['origin']['latitude']
            features['origin_lon'] = req_info['origin']['longitude']
            features['dest_lat'] = req_info['destination']['latitude']
            features['dest_lon'] = req_info['destination']['longitude']
            features['travel_mode'] = req_info.get('travel_mode', 'DRIVE')
            features['routing_preference'] = req_info.get('routing_preference', 'TRAFFIC_AWARE')
        
        # Processed data
        if 'processed_data' in data:
            processed = data['processed_data']
            
            # Route details
            if 'route_details' in processed:
                route_details = processed['route_details']
                features['distance_km'] = route_details['distance_km']
                features['duration_minutes'] = route_details['duration_minutes']
            
            # Carbon emission
            if 'carbon_emission' in processed:
                carbon = processed['carbon_emission']
                features['carbon_emission_kg'] = carbon['total_emission_kg']
                features['fuel_consumption_liters'] = carbon['distance_km'] * 0.08  # Estimated
            
            # Traffic conditions
            if 'traffic_conditions' in processed:
                traffic = processed['traffic_conditions']
                features['duration_in_traffic_minutes'] = traffic['duration_in_traffic_minutes']
        
        # Default values for missing features
        features.setdefault('temperature_celsius', 20)
        features.setdefault('precipitation_mm', 0)
        features.setdefault('wind_speed_kmh', 10)
        features.setdefault('visibility_km', 10)
        features.setdefault('construction_zones', 0)
        features.setdefault('accident_reports', 0)
        features.setdefault('traffic_delay_minutes', 0)
        features.setdefault('toll_cost_try', 0)
        
        return features
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Veri temizleme ve validation
        """
        # Eksik değerleri doldur
        df = df.fillna(0)
        
        # Aykırı değerleri temizle
        for col in ['distance_km', 'duration_minutes', 'carbon_emission_kg']:
            if col in df.columns:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
        
        # Negatif değerleri temizle
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].clip(lower=0)
        
        # Calculated features
        if 'distance_km' in df.columns and 'duration_minutes' in df.columns:
            df['average_speed_kmh'] = df['distance_km'] / (df['duration_minutes'] / 60)
            df['average_speed_kmh'] = df['average_speed_kmh'].fillna(0)
        
        return df
    
    def prepare_ml_data(self, data_path: str, target_col: str = 'carbon_emission_kg') -> Tuple[np.ndarray, np.ndarray]:
        """
        Makine öğrenimi için veri hazırlama
        
        Args:
            data_path: Veri klasörü yolu
            target_col: Hedef değişken
            
        Returns:
            Tuple: (X, y) feature matrix ve target vector
        """
        df = self.load_route_data(data_path)
        
        # Feature seçimi
        available_features = [col for col in self.feature_columns if col in df.columns]
        if not available_features:
            raise ValueError("No valid features found in data")
        
        # Categorical variables'ı encode et
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df[col] = self.label_encoders[col].fit_transform(df[col].astype(str))
            else:
                df[col] = self.label_encoders[col].transform(df[col].astype(str))
        
        # Feature matrix
        X = df[available_features].values
        
        # Target variable
        if target_col not in df.columns:
            # Eğer hedef değişken yoksa, tahmin et
            if target_col == 'carbon_emission_kg' and 'distance_km' in df.columns:
                y = df['distance_km'].values * 0.192  # Estimated emission factor
            else:
                raise ValueError(f"Target column '{target_col}' not found and cannot be estimated")
        else:
            y = df[target_col].values
        
        # Normalization
        X = self.scaler.fit_transform(X)
        
        return X, y
    
    def create_feature_importance_analysis(self, X: np.ndarray, y: np.ndarray, 
                                         feature_names: List[str]) -> pd.DataFrame:
        """
        Feature importance analizi
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.feature_selection import mutual_info_regression
        
        # Random Forest feature importance
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        rf_importance = rf.feature_importances_
        
        # Mutual information
        mi_scores = mutual_info_regression(X, y)
        
        # Correlation with target
        df_temp = pd.DataFrame(X, columns=feature_names)
        df_temp['target'] = y
        correlations = df_temp.corr()['target'].drop('target').abs()
        
        # Combine results
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'rf_importance': rf_importance,
            'mutual_info': mi_scores,
            'correlation': correlations.values
        })
        
        # Overall importance score
        importance_df['overall_score'] = (
            importance_df['rf_importance'] * 0.4 +
            importance_df['mutual_info'] * 0.3 +
            importance_df['correlation'] * 0.3
        )
        
        return importance_df.sort_values('overall_score', ascending=False)
    
    def generate_synthetic_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        Makine öğrenimi modeli eğitimi için sentetik veri üretimi
        """
        np.random.seed(42)
        
        # Base features
        distances = np.random.normal(400, 150, n_samples)  # km
        distances = np.clip(distances, 50, 1000)
        
        # Weather conditions
        temperatures = np.random.normal(20, 10, n_samples)
        precipitation = np.random.exponential(2, n_samples)
        wind_speeds = np.random.normal(15, 5, n_samples)
        
        # Road conditions
        construction_zones = np.random.poisson(1, n_samples)
        accident_reports = np.random.poisson(0.5, n_samples)
        
        # Traffic conditions
        traffic_delays = np.random.exponential(20, n_samples)
        
        # Calculate dependent variables
        base_speed = 80 - (precipitation * 2) - (construction_zones * 5) - (accident_reports * 10)
        base_speed = np.clip(base_speed, 40, 120)
        
        durations = distances / base_speed * 60  # minutes
        durations += traffic_delays
        
        # Fuel consumption (liters/100km varies by conditions)
        base_consumption = 8.0  # L/100km
        weather_factor = 1 + (precipitation * 0.01) + (np.abs(temperatures - 20) * 0.005)
        traffic_factor = 1 + (traffic_delays * 0.002)
        
        fuel_consumption = distances * base_consumption * weather_factor * traffic_factor / 100
        
        # Carbon emission
        carbon_emission = fuel_consumption * 2.31  # kg CO2 per liter gasoline
        
        # Toll costs (varies by distance and route type)
        toll_costs = distances * 0.15 + np.random.normal(0, 10, n_samples)
        toll_costs = np.clip(toll_costs, 0, None)
        
        # Create DataFrame
        synthetic_data = pd.DataFrame({
            'distance_km': distances,
            'duration_minutes': durations,
            'temperature_celsius': temperatures,
            'precipitation_mm': precipitation,
            'wind_speed_kmh': wind_speeds,
            'construction_zones': construction_zones,
            'accident_reports': accident_reports,
            'traffic_delay_minutes': traffic_delays,
            'average_speed_kmh': base_speed,
            'fuel_consumption_liters': fuel_consumption,
            'carbon_emission_kg': carbon_emission,
            'toll_cost_try': toll_costs,
            'visibility_km': np.random.normal(10, 3, n_samples),
            'routing_preference': np.random.choice(['TRAFFIC_AWARE', 'FUEL_EFFICIENT'], n_samples),
            'travel_mode': np.random.choice(['DRIVE'], n_samples)
        })
        
        return synthetic_data
    
    def save_processed_data(self, df: pd.DataFrame, output_path: str):
        """
        İşlenmiş veriyi kaydet
        """
        # CSV format
        df.to_csv(f"{output_path}.csv", index=False)
        
        # JSON format
        df.to_json(f"{output_path}.json", orient='records', indent=2)
        
        # Statistics
        stats = {
            'total_samples': len(df),
            'features': list(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'data_types': df.dtypes.astype(str).to_dict(),
            'statistics': df.describe().to_dict()
        }
        
        with open(f"{output_path}_stats.json", 'w') as f:
            json.dump(stats, f, indent=2)
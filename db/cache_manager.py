#!/usr/bin/env python3
"""
Cache Manager - Streamlit Cache & PostgreSQL Cache Management
Hem Streamlit cache hem de PostgreSQL tabanlı kalıcı cache yönetimi
"""

import streamlit as st
import pandas as pd
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from functools import wraps

from db.postgresql_config import postgresql_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache girişi için veri modeli"""
    cache_key: str
    query_hash: str
    query_params: Dict[str, Any]
    result_data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class CacheManager:
    """
    Unified cache management sistemi.
    
    1. Streamlit cache (@st.cache_data) - Oturum boyunca hızlı erişim
    2. PostgreSQL cache - Kalıcı cache, oturumlar arası paylaşım
    3. Query logging - Yapılan sorguların analizi
    """
    
    def __init__(self):
        """Cache manager'ı başlatır"""
        self.config = postgresql_config
        self.setup_cache_tables()
        
    def setup_cache_tables(self):
        """Cache tabloları oluşturur"""
        try:
            # Cache tablosu
            cache_table_sql = """
            CREATE TABLE IF NOT EXISTS query_cache (
                id SERIAL PRIMARY KEY,
                cache_key VARCHAR(255) UNIQUE NOT NULL,
                query_hash VARCHAR(64) NOT NULL,
                query_type VARCHAR(100) NOT NULL,
                query_params JSONB,
                result_data JSONB,
                result_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_query_cache_key ON query_cache (cache_key);
            CREATE INDEX IF NOT EXISTS idx_query_cache_hash ON query_cache (query_hash);
            CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON query_cache (expires_at);
            """
            
            # Query log tablosu
            query_log_sql = """
            CREATE TABLE IF NOT EXISTS query_log (
                id SERIAL PRIMARY KEY,
                query_type VARCHAR(100) NOT NULL,
                query_hash VARCHAR(64) NOT NULL,
                query_params JSONB,
                execution_time_ms INTEGER,
                result_count INTEGER,
                cache_hit BOOLEAN DEFAULT FALSE,
                user_session VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_query_log_type ON query_log (query_type);
            CREATE INDEX IF NOT EXISTS idx_query_log_hash ON query_log (query_hash);
            CREATE INDEX IF NOT EXISTS idx_query_log_created ON query_log (created_at);
            """
            
            self.config.execute_query(cache_table_sql)
            self.config.execute_query(query_log_sql)
            
        except Exception as e:
            logger.error(f"Cache tabloları oluşturma hatası: {e}")
    
    def generate_cache_key(self, query_type: str, **params) -> str:
        """
        Sorgu parametrelerinden cache key oluşturur.
        
        Args:
            query_type: Sorgu türü (places_search, routes_calc, etc.)
            **params: Sorgu parametreleri
            
        Returns:
            str: Cache key
        """
        # Parametreleri sıralayıp string'e çevir
        param_str = json.dumps(params, sort_keys=True, default=str)
        
        # Hash oluştur
        hash_input = f"{query_type}:{param_str}"
        cache_key = hashlib.md5(hash_input.encode()).hexdigest()
        
        return f"{query_type}_{cache_key[:16]}"
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Cache'den veri getirir.
        
        Args:
            cache_key: Cache anahtarı
            
        Returns:
            Cache'deki veri veya None
        """
        try:
            query = """
            SELECT result_data, expires_at, access_count
            FROM query_cache
            WHERE cache_key = %s
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
            """
            
            result = self.config.execute_query(query, (cache_key,))
            
            if result and len(result) > 0:
                # Access count güncelle
                self.config.execute_query(
                    """
                    UPDATE query_cache 
                    SET access_count = access_count + 1, 
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE cache_key = %s;
                    """,
                    (cache_key,)
                )
                
                return result[0]['result_data']
            
            return None
            
        except Exception as e:
            logger.error(f"Cache okuma hatası: {e}")
            return None
    
    def set_cache(self, cache_key: str, query_type: str, query_params: Dict[str, Any], 
                  result_data: Any, expires_in_hours: int = 24):
        """
        Cache'e veri kaydet.
        
        Args:
            cache_key: Cache anahtarı
            query_type: Sorgu türü
            query_params: Sorgu parametreleri
            result_data: Kaydedilecek veri
            expires_in_hours: Kaç saat sonra expire olacak
        """
        try:
            query_hash = hashlib.md5(json.dumps(query_params, sort_keys=True).encode()).hexdigest()
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            # JSON serializable hale getir
            if isinstance(result_data, pd.DataFrame):
                result_json = result_data.to_dict('records')
                result_size = len(result_data)
            else:
                result_json = result_data
                result_size = len(result_data) if isinstance(result_data, list) else 1
            
            query = """
            INSERT INTO query_cache (
                cache_key, query_hash, query_type, query_params, 
                result_data, result_size, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cache_key) 
            DO UPDATE SET
                result_data = EXCLUDED.result_data,
                result_size = EXCLUDED.result_size,
                expires_at = EXCLUDED.expires_at,
                access_count = query_cache.access_count + 1,
                last_accessed = CURRENT_TIMESTAMP;
            """
            
            self.config.execute_query(query, (
                cache_key, query_hash, query_type, 
                json.dumps(query_params), json.dumps(result_json), 
                result_size, expires_at
            ))
            
        except Exception as e:
            logger.error(f"Cache kaydetme hatası: {e}")
    
    def log_query(self, query_type: str, query_params: Dict[str, Any], 
                  execution_time_ms: int, result_count: int, cache_hit: bool = False):
        """
        Sorgu logunu kaydeder.
        
        Args:
            query_type: Sorgu türü
            query_params: Sorgu parametreleri
            execution_time_ms: Çalışma süresi (ms)
            result_count: Sonuç sayısı
            cache_hit: Cache'den mi geldi
        """
        try:
            query_hash = hashlib.md5(json.dumps(query_params, sort_keys=True).encode()).hexdigest()
            user_session = st.session_state.get('session_id', 'unknown')
            
            query = """
            INSERT INTO query_log (
                query_type, query_hash, query_params, execution_time_ms,
                result_count, cache_hit, user_session
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            
            self.config.execute_query(query, (
                query_type, query_hash, json.dumps(query_params),
                execution_time_ms, result_count, cache_hit, user_session
            ))
            
        except Exception as e:
            logger.error(f"Query log kaydetme hatası: {e}")
    
    def clean_expired_cache(self):
        """Süresi dolmuş cache girdilerini temizler"""
        try:
            query = "DELETE FROM query_cache WHERE expires_at < CURRENT_TIMESTAMP;"
            result = self.config.execute_query(query)
            
            if result:
                logger.info(f"Temizlenen cache girişi: {result}")
            
        except Exception as e:
            logger.error(f"Cache temizleme hatası: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Cache istatistiklerini döndürür"""
        try:
            stats = {}
            
            # Toplam cache girişi
            result = self.config.execute_query("SELECT COUNT(*) FROM query_cache;")
            stats['total_entries'] = result[0]['count'] if result else 0
            
            # Aktif cache girişi
            result = self.config.execute_query(
                "SELECT COUNT(*) FROM query_cache WHERE expires_at > CURRENT_TIMESTAMP;"
            )
            stats['active_entries'] = result[0]['count'] if result else 0
            
            # Query türlerine göre dağılım
            result = self.config.execute_query(
                """
                SELECT query_type, COUNT(*) as count, AVG(access_count) as avg_access
                FROM query_cache 
                GROUP BY query_type 
                ORDER BY count DESC;
                """
            )
            stats['by_type'] = {row['query_type']: {
                'count': row['count'], 
                'avg_access': float(row['avg_access']) if row['avg_access'] else 0
            } for row in result} if result else {}
            
            # Son 24 saat query istatistikleri
            result = self.config.execute_query(
                """
                SELECT query_type, COUNT(*) as count, 
                       AVG(execution_time_ms) as avg_time,
                       SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM query_log
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                GROUP BY query_type;
                """
            )
            stats['last_24h'] = {row['query_type']: {
                'count': row['count'],
                'avg_time_ms': float(row['avg_time']) if row['avg_time'] else 0,
                'cache_hits': row['cache_hits'],
                'cache_hit_rate': row['cache_hits'] / row['count'] if row['count'] > 0 else 0
            } for row in result} if result else {}
            
            return stats
            
        except Exception as e:
            logger.error(f"Cache stats hatası: {e}")
            return {}

# Global cache manager instance
cache_manager = CacheManager()

def cached_query(query_type: str, expires_in_hours: int = 24):
    """
    Fonksiyon decorator - otomatik cache management
    
    Args:
        query_type: Sorgu türü
        expires_in_hours: Cache expire süresi (saat)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Cache key oluştur
            cache_key = cache_manager.generate_cache_key(query_type, args=args, kwargs=kwargs)
            
            # Cache'de var mı kontrol et
            cached_result = cache_manager.get_from_cache(cache_key)
            if cached_result is not None:
                # Cache hit - log kaydet
                cache_manager.log_query(
                    query_type=query_type,
                    query_params={'args': args, 'kwargs': kwargs},
                    execution_time_ms=0,
                    result_count=len(cached_result) if isinstance(cached_result, list) else 1,
                    cache_hit=True
                )
                
                # DataFrame'e dönüştür
                if isinstance(cached_result, list) and len(cached_result) > 0:
                    return pd.DataFrame(cached_result)
                return cached_result
            
            # Cache'de yok - fonksiyonu çalıştır
            start_time = datetime.now()
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Sonucu cache'e kaydet
            cache_manager.set_cache(
                cache_key=cache_key,
                query_type=query_type,
                query_params={'args': args, 'kwargs': kwargs},
                result_data=result,
                expires_in_hours=expires_in_hours
            )
            
            # Log kaydet
            cache_manager.log_query(
                query_type=query_type,
                query_params={'args': args, 'kwargs': kwargs},
                execution_time_ms=int(execution_time),
                result_count=len(result) if isinstance(result, (list, pd.DataFrame)) else 1,
                cache_hit=False
            )
            
            return result
        
        return wrapper
    return decorator

# Streamlit cache decorators
@st.cache_data(ttl=3600)  # 1 saat cache
def cached_stations_by_country(country: str) -> pd.DataFrame:
    """Cache'li stations by country sorgusu"""
    from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
    warehouse = PostgreSQLDataWarehouse()
    return warehouse.get_stations_by_country(country)

@st.cache_data(ttl=1800)  # 30 dakika cache
def cached_routes_by_date(start_date: str, end_date: str) -> pd.DataFrame:
    """Cache'li routes by date sorgusu"""
    from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
    warehouse = PostgreSQLDataWarehouse()
    return warehouse.get_routes_by_date_range(start_date, end_date)

@st.cache_data(ttl=3600)  # 1 saat cache
def cached_analytics_summary() -> Dict[str, Any]:
    """Cache'li analytics summary"""
    from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
    warehouse = PostgreSQLDataWarehouse()
    return warehouse.get_analytics_summary()

@st.cache_data(ttl=1800)  # 30 dakika cache
def cached_truck_services_by_type(service_type: str, limit: int = 50) -> pd.DataFrame:
    """Cache'li truck services by type sorgusu"""
    from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
    warehouse = PostgreSQLDataWarehouse()
    return warehouse.get_truck_services_by_type(service_type, limit)

@st.cache_data(ttl=900)  # 15 dakika cache (location sensitive)
def cached_services_near_location(latitude: float, longitude: float, 
                                radius_km: float = 50, service_type: str = None) -> pd.DataFrame:
    """Cache'li services near location sorgusu"""
    from db.postgresql_data_warehouse import PostgreSQLDataWarehouse
    warehouse = PostgreSQLDataWarehouse()
    return warehouse.get_services_near_location(latitude, longitude, radius_km, service_type)
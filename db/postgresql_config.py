#!/usr/bin/env python3
"""
PostgreSQL Database Configuration
PostgreSQL veritabanı bağlantı ayarları ve konfigürasyonu
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional, Dict, Any
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Streamlit imports (sadece gerekli olduğunda)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLConfig:
    """
    PostgreSQL veritabanı bağlantı konfigürasyonu ve yönetimi.
    """
    
    def __init__(self):
        """
        PostgreSQL konfigürasyonu başlatır.
        """
        # Veritabanı bağlantı bilgileri (önce env, yoksa Streamlit secrets)
        self.connection_params = {
            'host': self._get_config_value('POSTGRES_HOST', 'localhost'),
            'port': int(self._get_config_value('POSTGRES_PORT', '5432')),
            'database': self._get_config_value('POSTGRES_DATABASE', 'fueltwogo'),
            'user': self._get_config_value('POSTGRES_USER', 'fuel_user'),
            'password': self._get_config_value('POSTGRES_PASSWORD', '')
        }
        
        # Bağlantı havuzu ayarları
        self.pool_params = {
            'minconn': 1,
            'maxconn': 20,
            'connect_timeout': 30,
            'command_timeout': 30
        }
        
        self._connection = None
        
    def _get_config_value(self, key: str, default: str = '') -> str:
        """
        Önce environment variable'dan oku, yoksa Streamlit secrets'den oku.
        
        Args:
            key (str): Config anahtarı
            default (str): Varsayılan değer
            
        Returns:
            str: Config değeri veya varsayılan değer
        """
        # Önce environment variable'dan dene
        value = os.getenv(key)
        
        if value:
            return value
            
        # Eğer Streamlit mevcutsa ve secrets var ise oradan dene
        if STREAMLIT_AVAILABLE:
            try:
                if hasattr(st, 'secrets') and key in st.secrets:
                    return st.secrets[key]
            except Exception:
                # Secrets erişimi başarısız olursa geç
                pass
        
        return default
        
    def get_connection_string(self) -> str:
        """
        PostgreSQL bağlantı string'i oluşturur.
        
        Returns:
            str: PostgreSQL bağlantı string'i
        """
        return f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}@{self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}"
    
    @contextmanager
    def get_connection(self):
        """
        PostgreSQL bağlantısı için context manager.
        
        Yields:
            psycopg2.connection: PostgreSQL bağlantısı
        """
        conn = None
        try:
            conn = psycopg2.connect(
                **self.connection_params,
                cursor_factory=RealDictCursor
            )
            yield conn
        except Exception as e:
            logger.error(f"PostgreSQL bağlantı hatası: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """
        PostgreSQL bağlantısını test eder.
        
        Returns:
            bool: Bağlantı başarılı ise True, aksi halde False
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()
                    logger.info(f"PostgreSQL bağlantısı başarılı: {version}")
                    return True
        except Exception as e:
            logger.error(f"PostgreSQL bağlantı testi başarısız: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Optional[list]:
        """
        PostgreSQL sorgusu çalıştırır.
        
        Args:
            query (str): Çalıştırılacak SQL sorgusu
            params (tuple, optional): Sorgu parametreleri
            
        Returns:
            Optional[list]: Sorgu sonuçları veya None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    
                    # SELECT sorgusu ise sonuçları döndür
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return cursor.rowcount
                        
        except Exception as e:
            logger.error(f"PostgreSQL sorgu hatası: {e}")
            return None
    
    def execute_many(self, query: str, params_list: list) -> Optional[int]:
        """
        Birden fazla veri için toplu işlem yapar.
        
        Args:
            query (str): Çalıştırılacak SQL sorgusu
            params_list (list): Parametre listesi
            
        Returns:
            Optional[int]: Etkilenen satır sayısı veya None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return cursor.rowcount
                    
        except Exception as e:
            logger.error(f"PostgreSQL toplu işlem hatası: {e}")
            return None
    
    def create_database_if_not_exists(self, database_name: str) -> bool:
        """
        Veritabanı yoksa oluşturur.
        
        Args:
            database_name (str): Oluşturulacak veritabanı adı
            
        Returns:
            bool: İşlem başarılı ise True
        """
        try:
            # Varsayılan postgres veritabanına bağlan
            temp_params = self.connection_params.copy()
            temp_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**temp_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Veritabanı var mı kontrol et
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (database_name,)
                )
                
                if not cursor.fetchone():
                    # Veritabanı yok, oluştur
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {}").format(
                            sql.Identifier(database_name)
                        )
                    )
                    logger.info(f"Veritabanı '{database_name}' oluşturuldu")
                else:
                    logger.info(f"Veritabanı '{database_name}' zaten mevcut")
                
                return True
                
        except Exception as e:
            logger.error(f"Veritabanı oluşturma hatası: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_table_info(self, table_name: str) -> Optional[list]:
        """
        Tablo bilgilerini getirir.
        
        Args:
            table_name (str): Tablo adı
            
        Returns:
            Optional[list]: Tablo sütun bilgileri veya None
        """
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
        """
        
        return self.execute_query(query, (table_name,))
    
    def table_exists(self, table_name: str) -> bool:
        """
        Tablo var mı kontrol eder.
        
        Args:
            table_name (str): Kontrol edilecek tablo adı
            
        Returns:
            bool: Tablo varsa True, yoksa False
        """
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
        """
        
        result = self.execute_query(query, (table_name,))
        return result[0]['exists'] if result else False

# Global PostgreSQL config instance
postgresql_config = PostgreSQLConfig()
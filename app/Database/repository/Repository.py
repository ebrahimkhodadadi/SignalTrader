import sqlite3
from typing import List, Tuple, Any, Dict, TypeVar, Generic, Optional

from .cache import LRUCache

T = TypeVar('T')


class SQLiteRepository(Generic[T]):
    def __init__(self, db_path: str, table_name: str, enable_cache: bool = True,
                 cache_size: int = 1000, default_ttl: float = 300.0):
        self.db_path = db_path
        self.table_name = table_name
        self.enable_cache = enable_cache

        if enable_cache:
            self.cache = LRUCache(max_size=cache_size, default_ttl=default_ttl)
        else:
            self.cache = None
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        # Increase timeout for busy database
        conn.execute('PRAGMA busy_timeout=10000')
        return conn
    
    def create_table(self, columns: Dict[str, str]):
        with self._connect() as conn:
            cursor = conn.cursor()
            columns_def = ', '.join(f'{col} {dtype}' for col, dtype in columns.items())
            query = f'CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_def})'
            cursor.execute(query)
            conn.commit()
    
    def insert(self, data: Dict[str, Any]):
        result = None
        inserted_record = None

        with self._connect() as conn:
            cursor = conn.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join('?' * len(data))
            values = tuple(data.values())
            query = f'INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})'
            cursor.execute(query, values)
            conn.commit()
            result = cursor.lastrowid

            # Immediately fetch the inserted record for caching
            if result and self.cache:
                cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (result,))
                inserted_record = cursor.fetchone()

        # Update cache with the inserted record (write-through caching)
        if self.cache and inserted_record:
            cache_key = f"{self.table_name}:get_by_id:{result}"
            self.cache.put(cache_key, inserted_record)
            # Also invalidate any query caches that might be affected
            self.cache.invalidate_pattern(f"{self.table_name}:query:")

        return result
    
    def get_all(self) -> List[Tuple]:
        with self._connect() as conn:
            cursor = conn.cursor()
            query = f'SELECT * FROM {self.table_name}'
            cursor.execute(query)
            return cursor.fetchall()
    
    def get_by_id(self, record_id: Any) -> Tuple:
        if self.cache:
            cache_key = f"{self.table_name}:get_by_id:{record_id}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = None
        with self._connect() as conn:
            cursor = conn.cursor()
            query = f'SELECT * FROM {self.table_name} WHERE id = ?'
            cursor.execute(query, (record_id,))
            result = cursor.fetchone()

        if self.cache and result is not None:
            self.cache.put(cache_key, result)

        return result
    
    def update(self, record_id: Any, data: Dict[str, Any]):
        with self._connect() as conn:
            cursor = conn.cursor()
            set_clause = ', '.join(f'{col} = ?' for col in data.keys())
            values = tuple(data.values()) + (record_id,)
            query = f'UPDATE {self.table_name} SET {set_clause} WHERE id = ?'
            cursor.execute(query, values)
            conn.commit()

        # Invalidate cache for this table and specific record
        if self.cache:
            self.cache.invalidate_pattern(f"{self.table_name}:")
            self.cache.invalidate(f"{self.table_name}:get_by_id:{record_id}")
    
    def delete(self, record_id: Any):
        with self._connect() as conn:
            cursor = conn.cursor()
            query = f'DELETE FROM {self.table_name} WHERE id = ?'
            cursor.execute(query, (record_id,))
            conn.commit()

        # Invalidate cache for this table and specific record
        if self.cache:
            self.cache.invalidate_pattern(f"{self.table_name}:")
            self.cache.invalidate(f"{self.table_name}:get_by_id:{record_id}")
    
    def execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        if self.cache:
            # Create a cache key from query and params
            cache_key = f"{self.table_name}:query:{hash((query, str(params)))}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = []
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()

        if self.cache:
            self.cache.put(cache_key, result)

        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"enabled": False}

    def clear_cache(self) -> None:
        """Clear all cache entries for this repository"""
        if self.cache:
            self.cache.clear()

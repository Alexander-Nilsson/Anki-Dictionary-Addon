"""
Simplified Database Module
Handles dictionary database operations with minimal dependencies
"""

import sqlite3
import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class DictionaryDatabase:
    """Simplified dictionary database with clean interface"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_path = self._get_default_db_path()
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.cursor = None
        self._connect()
        self._initialize_tables()
    
    def _get_default_db_path(self) -> str:
        """Get default database path"""
        return os.path.join(os.getcwd(), "user_files", "db", "dictionaries.sqlite")
    
    def _connect(self):
        """Establish database connection"""
        try:
            # Check if the path is a directory (which would cause sqlite3 to fail)
            if self.db_path.exists() and self.db_path.is_dir():
                raise DatabaseError(f"Database path is a directory: {self.db_path}")
            
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
            self.cursor = self.conn.cursor()
            
            # Enable foreign keys and case-sensitive LIKE
            self.cursor.execute("PRAGMA foreign_keys = ON")
            self.cursor.execute("PRAGMA case_sensitive_like = ON")
            
            logger.info(f"Connected to database: {self.db_path}")
            
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")
        except Exception as e:
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    def _initialize_tables(self):
        """Create necessary tables if they don't exist"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS langnames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                langname TEXT UNIQUE NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS dictionaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                language_id INTEGER,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (language_id) REFERENCES langnames (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dictionary_id INTEGER,
                term TEXT NOT NULL,
                definition TEXT NOT NULL,
                reading TEXT,
                frequency INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                results_count INTEGER DEFAULT 0
            )
            """
        ]
        
        try:
            for table_sql in tables:
                self.cursor.execute(table_sql)
            self.conn.commit()
            logger.info("Database tables initialized")
            
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize tables: {e}")
    
    def get_language_id(self, language: str) -> Optional[int]:
        """Get language ID by name
        
        Args:
            language: Language name
            
        Returns:
            Language ID or None if not found
        """
        try:
            self.cursor.execute("SELECT id FROM langnames WHERE langname = ?", (language,))
            result = self.cursor.fetchone()
            return result['id'] if result else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting language ID: {e}")
            return None
    
    def add_language(self, language: str) -> int:
        """Add a new language
        
        Args:
            language: Language name
            
        Returns:
            Language ID
        """
        try:
            self.cursor.execute("INSERT INTO langnames (langname) VALUES (?)", (language,))
            self.conn.commit()
            return self.cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Language already exists, return existing ID
            return self.get_language_id(language)
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to add language: {e}")
    
    def search_definitions(self, term: str, limit: int = 50) -> List[Dict]:
        """Search for definitions
        
        Args:
            term: Search term
            limit: Maximum number of results
            
        Returns:
            List of definition dictionaries
        """
        try:
            # Record search in history
            self._add_search_history(term)
            
            query = """
            SELECT d.term, d.definition, d.reading, d.frequency,
                   dict.name as dictionary_name, lang.langname as language
            FROM definitions d
            JOIN dictionaries dict ON d.dictionary_id = dict.id
            JOIN langnames lang ON dict.language_id = lang.id
            WHERE dict.enabled = 1 AND (
                d.term LIKE ? OR 
                d.definition LIKE ? OR 
                d.reading LIKE ?
            )
            ORDER BY d.frequency DESC, d.term ASC
            LIMIT ?
            """
            
            search_pattern = f"%{term}%"
            self.cursor.execute(query, (search_pattern, search_pattern, search_pattern, limit))
            
            results = []
            for row in self.cursor.fetchall():
                results.append({
                    'term': row['term'],
                    'definition': row['definition'],
                    'reading': row['reading'],
                    'frequency': row['frequency'],
                    'dictionary': row['dictionary_name'],
                    'language': row['language']
                })
            
            # Update search history with results count
            self._update_search_history_count(term, len(results))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Error searching definitions: {e}")
            return []
    
    def add_definition(self, dictionary_name: str, term: str, definition: str, 
                      reading: str = None, frequency: int = 0) -> bool:
        """Add a new definition
        
        Args:
            dictionary_name: Name of the dictionary
            term: The term/word
            definition: Definition text
            reading: Pronunciation/reading (optional)
            frequency: Frequency score (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create dictionary
            dict_id = self._get_or_create_dictionary(dictionary_name)
            
            self.cursor.execute("""
                INSERT INTO definitions (dictionary_id, term, definition, reading, frequency)
                VALUES (?, ?, ?, ?, ?)
            """, (dict_id, term, definition, reading, frequency))
            
            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error adding definition: {e}")
            return False
    
    def _get_or_create_dictionary(self, name: str, language: str = "English") -> int:
        """Get or create dictionary ID
        
        Args:
            name: Dictionary name
            language: Language name
            
        Returns:
            Dictionary ID
        """
        # Check if dictionary exists
        self.cursor.execute("SELECT id FROM dictionaries WHERE name = ?", (name,))
        result = self.cursor.fetchone()
        
        if result:
            return result['id']
        
        # Create new dictionary
        lang_id = self.get_language_id(language)
        if lang_id is None:
            lang_id = self.add_language(language)
        
        self.cursor.execute("""
            INSERT INTO dictionaries (name, language_id)
            VALUES (?, ?)
        """, (name, lang_id))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def _add_search_history(self, term: str):
        """Add search to history"""
        try:
            self.cursor.execute("""
                INSERT INTO search_history (term) VALUES (?)
            """, (term,))
            self.conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Error adding search history: {e}")
    
    def _update_search_history_count(self, term: str, count: int):
        """Update search history with results count"""
        try:
            self.cursor.execute("""
                UPDATE search_history 
                SET results_count = ? 
                WHERE term = ? AND id = (
                    SELECT MAX(id) FROM search_history WHERE term = ?
                )
            """, (count, term, term))
            self.conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Error updating search history: {e}")
    
    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """Get recent search history
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of search history entries
        """
        try:
            self.cursor.execute("""
                SELECT term, timestamp, results_count
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in self.cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting search history: {e}")
            return []
    
    def get_dictionaries(self) -> List[Dict]:
        """Get all dictionaries
        
        Returns:
            List of dictionary information
        """
        try:
            self.cursor.execute("""
                SELECT d.id, d.name, d.enabled, d.created_at,
                       l.langname as language,
                       COUNT(def.id) as definition_count
                FROM dictionaries d
                JOIN langnames l ON d.language_id = l.id
                LEFT JOIN definitions def ON d.id = def.dictionary_id
                GROUP BY d.id, d.name, d.enabled, d.created_at, l.langname
                ORDER BY d.name
            """)
            
            return [dict(row) for row in self.cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting dictionaries: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
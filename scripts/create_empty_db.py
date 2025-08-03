#!/usr/bin/env python3
"""
Database initialization script for Anki Dictionary Addon

This script creates a new empty database with the required schema for the addon.
"""

import sqlite3
import os
import sys


def create_empty_database(db_path: str) -> None:
    """Create an empty database with the required schema."""
    
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"   ✓ Removed existing database: {db_path}")
    
    try:
        # Create new database
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Enable foreign keys and case sensitive like
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA case_sensitive_like=ON;")
        
        # Create langnames table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "langnames" (
                `id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                `langname`	TEXT NOT NULL UNIQUE,
                `font`	TEXT
            )
        """)
        
        # Create dictnames table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "dictnames" (
                `id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                `dictname`	TEXT NOT NULL UNIQUE,
                `lid`	INTEGER NOT NULL,
                `fields`	TEXT NOT NULL,
                `addtype`	TEXT NOT NULL,
                `termHeader`	TEXT NOT NULL,
                `duplicateHeader`	INTEGER NOT NULL,
                CONSTRAINT `langdicts` FOREIGN KEY(`lid`) REFERENCES `langnames`(`id`) ON DELETE CASCADE
            )
        """)
        
        # Commit changes and close
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"   ✓ Created empty database: {db_path}")
        
    except Exception as e:
        print(f"   ❌ Error creating database: {e}")
        raise


def main():
    """Main function to create the database."""
    if len(sys.argv) != 2:
        print("Usage: python create_empty_db.py <database_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    print(f"Creating empty database: {db_path}")
    create_empty_database(db_path)
    print("✅ Database creation completed")


if __name__ == '__main__':
    main()

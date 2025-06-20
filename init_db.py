#!/usr/bin/env python3
"""
Database initialization script for Thyme timeline app
"""

from thyme import app, db

def init_database():
    """Initialize the database and create all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database initialized successfully!")
        print("You can now run the import scripts or start the Flask app.")

if __name__ == "__main__":
    init_database() 
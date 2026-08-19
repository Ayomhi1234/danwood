"""
Danwood Database Helper
Utility functions for managing houses, favorites, and inquiries
"""

import mysql.connector
from mysql.connector import Error
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

load_dotenv()

class DanwoodDB:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', 'root')
        self.database = os.getenv('DB_NAME', 'danwood_houses')
        self.conn = None
    
    def connect(self):
        """Create database connection"""
        try:
            self.conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print(f"✓ Connected to {self.database}")
            return True
        except Error as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Connection closed")
    
    # ============================================
    # HOUSE OPERATIONS
    # ============================================
    
    def add_house(self, slug, name, category_id, series, sqm, rooms, description, url):
        """Add new house"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO houses 
                (slug, name, category_id, series, square_meters, rooms, description, danwood_url, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (slug, name, category_id, series, sqm, rooms, description, url))
            self.conn.commit()
            print(f"✓ Added house: {name}")
            return cursor.lastrowid
        except Error as e:
            print(f"✗ Error adding house: {e}")
            return None
    
    def get_all_houses_df(self):
        """Get all houses as pandas DataFrame"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT h.*, c.name as category_name
                FROM houses h
                LEFT JOIN categories c ON h.category_id = c.id
                WHERE h.is_active = TRUE
                ORDER BY h.name
            """)
            return pd.DataFrame(cursor.fetchall())
        except Error as e:
            print(f"✗ Error fetching houses: {e}")
            return pd.DataFrame()
    
    def get_house_by_slug(self, slug):
        """Get house by slug"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM houses WHERE slug = %s", (slug,))
            return cursor.fetchone()
        except Error as e:
            print(f"✗ Error: {e}")
            return None
    
    def search_houses(self, search_term):
        """Search houses by name or series"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM houses 
                WHERE (name LIKE %s OR series LIKE %s) AND is_active = TRUE
            """, (f"%{search_term}%", f"%{search_term}%"))
            return cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def filter_houses(self, category=None, series=None, min_sqm=None, max_sqm=None, min_rooms=None, max_rooms=None):
        """Filter houses by multiple criteria"""
        try:
            query = "SELECT h.* FROM houses h WHERE h.is_active = TRUE"
            params = []
            
            if category:
                query += " AND h.category_id = %s"
                params.append(category)
            if series:
                query += " AND h.series = %s"
                params.append(series)
            if min_sqm:
                query += " AND h.square_meters >= %s"
                params.append(min_sqm)
            if max_sqm:
                query += " AND h.square_meters <= %s"
                params.append(max_sqm)
            if min_rooms:
                query += " AND h.rooms >= %s"
                params.append(min_rooms)
            if max_rooms:
                query += " AND h.rooms <= %s"
                params.append(max_rooms)
            
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def update_house(self, house_id, **kwargs):
        """Update house fields"""
        try:
            allowed_fields = ['name', 'series', 'square_meters', 'rooms', 'description', 'energy_class']
            updates = []
            values = []
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if not updates:
                print("No valid fields to update")
                return False
            
            values.append(house_id)
            query = f"UPDATE houses SET {', '.join(updates)} WHERE id = %s"
            
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            print(f"✓ Updated house {house_id}")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    def delete_house(self, house_id):
        """Soft delete house (mark inactive)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE houses SET is_active = FALSE WHERE id = %s", (house_id,))
            self.conn.commit()
            print(f"✓ Deleted house {house_id}")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    # ============================================
    # STATISTICS
    # ============================================
    
    def get_statistics(self):
        """Get database statistics"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            stats = {}
            
            # Total houses
            cursor.execute("SELECT COUNT(*) as total FROM houses WHERE is_active = TRUE")
            stats['total_houses'] = cursor.fetchone()['total']
            
            # Houses by category
            cursor.execute("""
                SELECT c.name, COUNT(*) as count FROM houses h
                JOIN categories c ON h.category_id = c.id
                WHERE h.is_active = TRUE
                GROUP BY c.id
            """)
            stats['by_category'] = cursor.fetchall()
            
            # Average size
            cursor.execute("SELECT AVG(square_meters) as avg_sqm FROM houses WHERE is_active = TRUE")
            stats['avg_sqm'] = cursor.fetchone()['avg_sqm']
            
            # Size distribution
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN square_meters < 100 THEN 1 END) as 'under_100',
                    COUNT(CASE WHEN square_meters BETWEEN 100 AND 150 THEN 1 END) as '100-150',
                    COUNT(CASE WHEN square_meters BETWEEN 150 AND 200 THEN 1 END) as '150-200',
                    COUNT(CASE WHEN square_meters > 200 THEN 1 END) as 'over_200'
                FROM houses WHERE is_active = TRUE
            """)
            stats['size_distribution'] = cursor.fetchone()
            
            # Most popular (most favorited)
            cursor.execute("""
                SELECT h.name, COUNT(f.id) as favorites FROM houses h
                LEFT JOIN favorites f ON h.id = f.house_id
                WHERE h.is_active = TRUE
                GROUP BY h.id
                ORDER BY favorites DESC
                LIMIT 5
            """)
            stats['most_favorited'] = cursor.fetchall()
            
            return stats
        except Error as e:
            print(f"✗ Error: {e}")
            return {}
    
    # ============================================
    # FAVORITES
    # ============================================
    
    def get_user_favorites(self, user_id):
        """Get user's favorite houses"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT h.* FROM favorites f
                JOIN houses h ON f.house_id = h.id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
            """, (user_id,))
            return cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def save_favorite(self, user_id, house_id):
        """Save favorite"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT IGNORE INTO favorites (user_id, house_id) VALUES (%s, %s)
            """, (user_id, house_id))
            self.conn.commit()
            print(f"✓ Saved favorite for user {user_id}")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    def remove_favorite(self, user_id, house_id):
        """Remove favorite"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM favorites WHERE user_id = %s AND house_id = %s
            """, (user_id, house_id))
            self.conn.commit()
            print(f"✓ Removed favorite")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    # ============================================
    # INQUIRIES
    # ============================================
    
    def get_inquiries(self, status='new', limit=50):
        """Get inquiries by status"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT i.*, h.name as house_name FROM inquiries i
                LEFT JOIN houses h ON i.house_id = h.id
                WHERE i.status = %s
                ORDER BY i.created_at DESC
                LIMIT %s
            """, (status, limit))
            return cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def submit_inquiry(self, name, email, phone, message, house_id=None):
        """Submit inquiry"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO inquiries (name, email, phone, message, house_id, inquiry_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, message, house_id, 'contact', 'new'))
            self.conn.commit()
            print(f"✓ Inquiry submitted from {name}")
            return cursor.lastrowid
        except Error as e:
            print(f"✗ Error: {e}")
            return None
    
    def mark_inquiry_as_responded(self, inquiry_id):
        """Mark inquiry as responded"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE inquiries SET status = 'responded' WHERE id = %s
            """, (inquiry_id,))
            self.conn.commit()
            print(f"✓ Marked inquiry as responded")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    # ============================================
    # FEATURES & SPECS
    # ============================================
    
    def add_feature(self, house_id, feature_name):
        """Add feature to house"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO house_features (house_id, feature_name)
                VALUES (%s, %s)
            """, (house_id, feature_name))
            self.conn.commit()
            print(f"✓ Added feature: {feature_name}")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    def add_specification(self, house_id, spec_key, spec_value):
        """Add specification to house"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO specifications (house_id, spec_key, spec_value)
                VALUES (%s, %s, %s)
            """, (house_id, spec_key, spec_value))
            self.conn.commit()
            print(f"✓ Added spec: {spec_key} = {spec_value}")
            return True
        except Error as e:
            print(f"✗ Error: {e}")
            return False
    
    # ============================================
    # BULK OPERATIONS
    # ============================================
    
    def import_from_json(self, json_file):
        """Import houses from JSON file"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            count = 0
            for house in data.get('houses', []):
                house_id = self.add_house(
                    slug=house['id'],
                    name=house['name'],
                    category_id=1,  # Adjust based on your data
                    series=house.get('series', ''),
                    sqm=house.get('squareMeters', 0),
                    rooms=house.get('rooms', 0),
                    description=house.get('description', ''),
                    url=house.get('url', '')
                )
                if house_id:
                    count += 1
            
            print(f"✓ Imported {count} houses")
            return count
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return 0
    
    def export_to_json(self, output_file='houses_export.json'):
        """Export all houses to JSON"""
        try:
            df = self.get_all_houses_df()
            
            # Convert to list of dicts
            houses = df.to_dict('records')
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_houses': len(houses),
                'houses': houses
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✓ Exported to {output_file}")
            return True
        except Exception as e:
            print(f"✗ Export failed: {e}")
            return False
    
    # ============================================
    # CATEGORIES
    # ============================================
    
    def get_categories(self):
        """Get all categories"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM categories ORDER BY name")
            return cursor.fetchall()
        except Error as e:
            print(f"✗ Error: {e}")
            return []
    
    def get_series_list(self):
        """Get all series"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT series FROM houses 
                WHERE is_active = TRUE AND series IS NOT NULL 
                ORDER BY series
            """)
            return [row['series'] for row in cursor.fetchall()]
        except Error as e:
            print(f"✗ Error: {e}")
            return []


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    # Initialize database helper
    db = DanwoodDB()
    
    if not db.connect():
        exit(1)
    
    # Example: Get all houses
    houses = db.get_all_houses_df()
    print(f"\nTotal houses: {len(houses)}")
    print(houses[['name', 'series', 'square_meters', 'rooms']].head())
    
    # Example: Get statistics
    print("\n📊 Database Statistics:")
    stats = db.get_statistics()
    print(f"Total houses: {stats.get('total_houses')}")
    print(f"Average size: {stats.get('avg_sqm', 0):.0f} m²")
    print("\nMost favorited houses:")
    for house in stats.get('most_favorited', []):
        print(f"  - {house['name']}: {house['favorites']} favorites")
    
    # Example: Search
    print("\nSearching for 'Perfect':")
    results = db.search_houses('Perfect')
    for house in results[:3]:
        print(f"  - {house['name']} ({house['square_meters']} m²)")
    
    # Example: Filter
    print("\nFiltering: Bungalows, 100-150 sqm:")
    results = db.filter_houses(min_sqm=100, max_sqm=150)
    print(f"Found {len(results)} houses")
    
    # Example: Get categories
    print("\nCategories:")
    for cat in db.get_categories():
        print(f"  - {cat['name']}")
    
    db.close()

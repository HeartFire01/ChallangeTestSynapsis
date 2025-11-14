"""
Polygon Manager - List, View, Delete polygons
"""

import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager


class PolygonManager:
    def __init__(self):
        self.db = DatabaseManager()

    def list_polygons(self):
        """List all polygons"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, name, coordinates, description, is_active, created_at, updated_at
                FROM polygon_areas
                ORDER BY created_at DESC
            """)

            polygons = cursor.fetchall()
            cursor.close()

            if not polygons:
                print("ℹ️ No polygons found")
                return

            print("\n" + "=" * 80)
            print("📋 POLYGON AREAS")
            print("=" * 80)

            for poly in polygons:
                status = "✅ Active" if poly['is_active'] else "❌ Inactive"
                coords = json.loads(poly['coordinates'])

                print(f"\n[ID: {poly['id']}] {poly['name']} - {status}")
                print(f"  Description: {poly['description']}")
                print(f"  Points: {len(coords['points'])}")
                print(f"  Coordinates: {coords}")
                print(f"  Created: {poly['created_at']}")
                print(f"  Updated: {poly['updated_at']}")
                print("-" * 80)

            print("=" * 80 + "\n")

        except Exception as e:
            print(f"❌ Error: {e}")

    def delete_polygon(self, polygon_id):
        """Delete polygon by ID"""
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("DELETE FROM polygon_areas WHERE id = %s", (polygon_id,))
            self.db.connection.commit()

            if cursor.rowcount > 0:
                print(f"✅ Polygon ID {polygon_id} deleted")
            else:
                print(f"⚠️ Polygon ID {polygon_id} not found")

            cursor.close()

        except Exception as e:
            print(f"❌ Error: {e}")

    def toggle_active(self, polygon_id):
        """Toggle polygon active status"""
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("""
                UPDATE polygon_areas 
                SET is_active = NOT is_active 
                WHERE id = %s
            """, (polygon_id,))
            self.db.connection.commit()

            if cursor.rowcount > 0:
                print(f"✅ Polygon ID {polygon_id} status toggled")
            else:
                print(f"⚠️ Polygon ID {polygon_id} not found")

            cursor.close()

        except Exception as e:
            print(f"❌ Error: {e}")

    def close(self):
        self.db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Polygon Manager')
    parser.add_argument('--list', '-l', action='store_true', help='List all polygons')
    parser.add_argument('--delete', '-d', type=int, help='Delete polygon by ID')
    parser.add_argument('--toggle', '-t', type=int, help='Toggle active status')

    args = parser.parse_args()

    manager = PolygonManager()

    if args.list:
        manager.list_polygons()
    elif args.delete:
        manager.delete_polygon(args.delete)
    elif args.toggle:
        manager.toggle_active(args.toggle)
    else:
        parser.print_help()

    manager.close()
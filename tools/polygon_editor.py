import cv2
import numpy as np
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from config.config import Config


class PolygonEditor:

    def __init__(self, video_source=None):
        self.config = Config()
        self.video_source = video_source or self.config.VIDEO_SOURCE
        self.points = []
        self.current_polygon = []
        self.drawing = False
        self.frame = None
        self.original_frame = None
        self.polygon_name = ""
        self.polygon_description = ""
        self.window_name = "Polygon Editor - Click to add points | Press 'h' for help"
        self.db = DatabaseManager()
        self.color_point = (0, 255, 0)  # Green
        self.color_line = (255, 0, 0)  # Blue
        self.color_polygon = (0, 255, 255)  # Yellow
        self.color_text = (255, 255, 255)  # White

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Add point
            self.points.append([x, y])
            print(f"✅ Point added: ({x}, {y}) | Total points: {len(self.points)}")
            self.draw_overlay()

        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.points:
                removed = self.points.pop()
                print(f"❌ Point removed: {removed} | Remaining: {len(self.points)}")
                self.draw_overlay()

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.points:
                temp_frame = self.frame.copy()
                cv2.line(temp_frame, tuple(self.points[-1]), (x, y),
                         self.color_line, 2)
                cv2.imshow(self.window_name, temp_frame)

    def draw_overlay(self):
        self.frame = self.original_frame.copy()

        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                cv2.line(self.frame, tuple(self.points[i]),
                         tuple(self.points[i + 1]), self.color_line, 2)

        if len(self.points) > 2:
            cv2.line(self.frame, tuple(self.points[-1]),
                     tuple(self.points[0]), self.color_line, 2)

            overlay = self.frame.copy()
            pts = np.array(self.points, dtype=np.int32)
            cv2.fillPoly(overlay, [pts], self.color_polygon)
            cv2.addWeighted(overlay, 0.3, self.frame, 0.7, 0, self.frame)

        for i, point in enumerate(self.points):
            cv2.circle(self.frame, tuple(point), 5, self.color_point, -1)
            cv2.putText(self.frame, str(i + 1),
                        (point[0] + 10, point[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_text, 2)

        self.draw_instructions()

        cv2.imshow(self.window_name, self.frame)

    def draw_instructions(self):
        instructions = [
            f"Points: {len(self.points)}",
            "Left Click: Add point",
            "Right Click: Remove last",
            "'c': Complete & Save",
            "'r': Reset",
            "'q': Quit",
            "'h': Help"
        ]

        y_offset = 30
        for i, text in enumerate(instructions):
            cv2.putText(self.frame, text, (10, y_offset + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
            cv2.putText(self.frame, text, (10, y_offset + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_text, 1)

    def show_help(self):
        print("\n" + "=" * 70)
        print("🎨 POLYGON EDITOR - HELP")
        print("=" * 70)
        print("MOUSE CONTROLS:")
        print("  • Left Click       : Add point to polygon")
        print("  • Right Click      : Remove last point")
        print("  • Mouse Move       : Preview line to cursor")
        print("\nKEYBOARD CONTROLS:")
        print("  • 'c' or ENTER     : Complete polygon & save to database")
        print("  • 'r'              : Reset/clear all points")
        print("  • 'q' or ESC       : Quit editor")
        print("  • 'h'              : Show this help")
        print("  • 's'              : Save screenshot")
        print("\nTIPS:")
        print("  • Minimum 3 points required for polygon")
        print("  • Click points in clockwise or counter-clockwise order")
        print("  • Polygon will auto-close when you press 'c'")
        print("=" * 70 + "\n")

    def capture_frame(self):
        print(f"📹 Capturing frame from: {self.video_source[:60]}...")

        cap = cv2.VideoCapture(self.video_source)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print("❌ Failed to open video source!")
            return False

        # Read a few frames to get stable frame
        for _ in range(5):
            ret, frame = cap.read()

        if not ret:
            print("❌ Failed to capture frame!")
            cap.release()
            return False

        self.original_frame = frame.copy()
        self.frame = frame.copy()

        cap.release()

        print(f"✅ Frame captured: {frame.shape[1]}x{frame.shape[0]}")
        return True

    def get_polygon_info(self):
        print("\n" + "=" * 70)
        print("📝 POLYGON INFORMATION")
        print("=" * 70)

        self.polygon_name = input("Enter polygon name (e.g., 'Main Entrance'): ").strip()

        if not self.polygon_name:
            self.polygon_name = f"Polygon_{len(self.points)}_points"
            print(f"⚠️ Using default name: {self.polygon_name}")

        self.polygon_description = input("Enter description (optional): ").strip()

        if not self.polygon_description:
            self.polygon_description = f"Polygon with {len(self.points)} points"

        print(f"✅ Name: {self.polygon_name}")
        print(f"✅ Description: {self.polygon_description}")

    def save_to_database(self):
        if len(self.points) < 3:
            print("❌ Need at least 3 points to create a polygon!")
            return False

        # Get polygon info from user
        self.get_polygon_info()

        coordinates = {
            "points": [{"x": int(p[0]), "y": int(p[1])} for p in self.points]
        }

        try:
            cursor = self.db.connection.cursor()

            query = """
                INSERT INTO polygon_areas (name, coordinates, description, is_active)
                VALUES (%s, %s, %s, TRUE)
            """

            cursor.execute(query, (
                self.polygon_name,
                json.dumps(coordinates),
                self.polygon_description
            ))

            self.db.connection.commit()
            polygon_id = cursor.lastrowid
            cursor.close()

            print("\n" + "=" * 70)
            print("✅ POLYGON SAVED TO DATABASE!")
            print("=" * 70)
            print(f"Polygon ID: {polygon_id}")
            print(f"Name: {self.polygon_name}")
            print(f"Points: {len(self.points)}")
            print(f"Coordinates: {coordinates}")
            print("=" * 70 + "\n")

            self.save_backup_json(polygon_id, coordinates)

            return True

        except Exception as e:
            print(f"❌ Error saving to database: {e}")
            return False

    def save_backup_json(self, polygon_id, coordinates):
        try:
            os.makedirs('polygons', exist_ok=True)

            filename = f"polygons/polygon_{polygon_id}_{self.polygon_name.replace(' ', '_')}.json"

            backup_data = {
                "id": polygon_id,
                "name": self.polygon_name,
                "description": self.polygon_description,
                "coordinates": coordinates,
                "created_at": None  # Will be set by database
            }

            with open(filename, 'w') as f:
                json.dump(backup_data, f, indent=2)

            print(f"💾 Backup JSON saved: {filename}")

        except Exception as e:
            print(f"⚠️ Warning: Could not save backup JSON: {e}")

    def load_existing_polygons(self):
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, name, coordinates, description, is_active, created_at
                FROM polygon_areas
                ORDER BY created_at DESC
            """)

            polygons = cursor.fetchall()
            cursor.close()

            if not polygons:
                print("ℹ️ No existing polygons found in database")
                return

            print("\n" + "=" * 70)
            print("📋 EXISTING POLYGONS")
            print("=" * 70)

            for poly in polygons:
                status = "✅ Active" if poly['is_active'] else "❌ Inactive"
                coords = json.loads(poly['coordinates'])
                num_points = len(coords['points'])

                print(f"\nID: {poly['id']} | {status}")
                print(f"Name: {poly['name']}")
                print(f"Description: {poly['description']}")
                print(f"Points: {num_points}")
                print(f"Created: {poly['created_at']}")
                print("-" * 70)

            print("=" * 70 + "\n")

        except Exception as e:
            print(f"❌ Error loading polygons: {e}")

    def reset(self):
        self.points = []
        self.frame = self.original_frame.copy()
        self.draw_overlay()
        print("🔄 Reset: All points cleared")

    def run(self):
        print("\n" + "=" * 70)
        print("🎨 POLYGON EDITOR")
        print("=" * 70)

        self.load_existing_polygons()

        if not self.capture_frame():
            return

        # Setup window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1280, 720)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        # Show help
        self.show_help()

        # Initial display
        self.draw_overlay()

        print("🎨 Editor started! Click on the frame to add polygon points.")
        print("Press 'h' for help\n")

        # Main loop
        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:
                print("👋 Exiting editor...")
                break

            elif key == ord('c') or key == 13:
                if len(self.points) < 3:
                    print("⚠️ Need at least 3 points! Current points: {len(self.points)}")
                else:
                    if self.save_to_database():
                        response = input("\nCreate another polygon? (y/n): ").strip().lower()
                        if response == 'y':
                            self.reset()
                        else:
                            break

            elif key == ord('r'):
                self.reset()

            elif key == ord('h'):  # Help
                self.show_help()

            elif key == ord('s'):  # Screenshot
                filename = f"polygon_screenshot_{len(self.points)}_points.jpg"
                cv2.imwrite(filename, self.frame)
                print(f"📸 Screenshot saved: {filename}")

        # Cleanup
        cv2.destroyAllWindows()
        self.db.close()

        print("\n✅ Polygon Editor closed")


def main():
    """
    Main function untuk menjalankan Polygon Editor
    """
    import argparse

    parser = argparse.ArgumentParser(description='Polygon Editor for People Counting System')
    parser.add_argument('--source', '-s', type=str, default=None,
                        help='Video source (URL or file path). If not provided, uses config.')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List existing polygons and exit')

    args = parser.parse_args()

    # If just listing
    if args.list:
        editor = PolygonEditor()
        editor.load_existing_polygons()
        editor.db.close()
        return

    # Run editor
    editor = PolygonEditor(video_source=args.source)
    editor.run()


if __name__ == "__main__":
    main()
import mysql.connector
from datetime import datetime, date
import json
from config.config import Config


class DatabaseManager:
    def __init__(self):
        self.config = Config()
        self.connection = None
        self.connect()

    def connect(self):
        """Connect ke database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config.DB_HOST,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )
            print("✅ Database connected")
        except Exception as e:
            print(f"❌ Database connection error: {e}")

    def get_polygon_area(self, area_id=1):
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM polygon_areas 
                WHERE id = %s AND is_active = TRUE
            """, (area_id,))

            result = cursor.fetchone()
            cursor.close()

            if result:
                coords = json.loads(result['coordinates'])
                return {
                    'id': result['id'],
                    'name': result['name'],
                    'points': [(p['x'], p['y']) for p in coords['points']]
                }
            return None

        except Exception as e:
            print(f"❌ Error fetching polygon: {e}")
            return None

    def save_detection(self, tracking_id, polygon_area_id, bbox, centroid,
                       confidence, is_inside, frame_number, video_source):
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO detections 
                (tracking_id, polygon_area_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                 centroid_x, centroid_y, confidence, is_inside_polygon, 
                 frame_number, video_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                tracking_id, polygon_area_id,
                bbox[0], bbox[1], bbox[2], bbox[3],
                centroid[0], centroid[1],
                confidence, is_inside,
                frame_number, video_source
            ))

            self.connection.commit()
            cursor.close()

        except Exception as e:
            print(f"❌ Error saving detection: {e}")

    def save_counting_event(self, polygon_area_id, tracking_id, event_type,
                            frame_number, video_source):
        """
        Simpan counting event (ENTER/EXIT)
        """
        try:
            cursor = self.connection.cursor()
            query = """
                INSERT INTO people_counting 
                (polygon_area_id, tracking_id, event_type, frame_number, video_source)
                VALUES (%s, %s, %s, %s, %s)
            """

            cursor.execute(query, (
                polygon_area_id, tracking_id, event_type,
                frame_number, video_source
            ))

            self.connection.commit()
            cursor.close()

        except Exception as e:
            print(f"❌ Error saving counting event: {e}")

    def update_summary(self, polygon_area_id, total_entered, total_exited, current_count):
        try:
            cursor = self.connection.cursor()
            today = date.today()
            current_hour = datetime.now().hour

            query = """
                INSERT INTO counting_summary 
                (polygon_area_id, total_entered, total_exited, current_count, 
                 summary_date, summary_hour)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_entered = VALUES(total_entered),
                    total_exited = VALUES(total_exited),
                    current_count = VALUES(current_count),
                    updated_at = CURRENT_TIMESTAMP
            """

            cursor.execute(query, (
                polygon_area_id, total_entered, total_exited,
                current_count, today, current_hour
            ))

            self.connection.commit()
            cursor.close()

        except Exception as e:
            print(f"❌ Error updating summary: {e}")

    def update_counting_summary(self, polygon_area_id, total_entered, total_exited, current_count):
        try:
            from datetime import datetime

            cursor = self.connection.cursor()

            now = datetime.now()
            summary_date = now.date()
            summary_hour = now.hour

            query = """
                INSERT INTO counting_summary 
                (polygon_area_id, summary_date, summary_hour, total_entered, total_exited, current_count, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    total_entered = VALUES(total_entered),
                    total_exited = VALUES(total_exited),
                    current_count = VALUES(current_count),
                    updated_at = NOW()
            """

            values = (
                int(polygon_area_id),
                summary_date,
                int(summary_hour),
                int(total_entered),
                int(total_exited),
                int(current_count)
            )

            cursor.execute(query, values)
            self.connection.commit()
            cursor.close()

            return True

        except Exception as e:
            print(f"❌ Error updating counting summary: {e}")
            import traceback
            traceback.print_exc()
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")
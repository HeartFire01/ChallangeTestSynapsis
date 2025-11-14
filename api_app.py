from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from database.db_manager import DatabaseManager
import cv2, torch, time, numpy as np, json
from datetime import datetime, timedelta
from ultralytics import YOLO
from config.config import Config
from core.polygon import PolygonChecker
from core.counter import PeopleCounter

from pydantic import BaseModel
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

db = DatabaseManager()
config = Config()

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🔧 Device: {device}")
model = YOLO(config.YOLO_MODEL)
model.to(device)

cursor = db.connection.cursor(dictionary=True)
cursor.execute("""
    SELECT id, name, coordinates FROM polygon_areas
    WHERE is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 1
""")
polygon_config = cursor.fetchone()
cursor.close()

if polygon_config:
    coords = json.loads(polygon_config['coordinates'])
    polygon_points = [(int(p['x']), int(p['y'])) for p in coords['points']]
    polygon_name = polygon_config['name']
    polygon_id = polygon_config['id']
    print(f"✅ Polygon loaded: {polygon_name} (ID: {polygon_id})")
else:
    polygon_points = config.DEFAULT_POLYGON
    polygon_name = "Default Area"
    polygon_id = None
    print("⚠️ Using default polygon")

polygon_checker = PolygonChecker(polygon_points)
counter = PeopleCounter(polygon_checker)

class ChangeYOLOModelRequest(BaseModel):
    model_path: str
@app.post("/api/config/yolo/change_model")
def change_yolo_model(req: ChangeYOLOModelRequest):
    global model
    try:
        model = YOLO(req.model_path)
        model.to(device)
        return {
            "success": True,
            "current_model": req.model_path,
            "device": device
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

class Point(BaseModel):
    x: int
    y: int

class PolygonCreate(BaseModel):
    name: str
    description: str = ""
    points: List[Point]


class PolygonUpdate(BaseModel):
    name: str = None
    description: str = None
    points: List[Point] = None


@app.post("/api/polygon/create")
def create_polygon(polygon: PolygonCreate):

    if len(polygon.points) < 3:
        raise HTTPException(400, "Polygon must have at least 3 points")

    try:
        coordinates = {
            "points": [{"x": p.x, "y": p.y} for p in polygon.points]
        }

        cursor = db.connection.cursor()
        cursor.execute("""
            INSERT INTO polygon_areas (name, description, coordinates, is_active)
            VALUES (%s, %s, %s, FALSE)
        """, (polygon.name, polygon.description, json.dumps(coordinates)))
        db.connection.commit()
        polygon_id = cursor.lastrowid
        cursor.close()

        return {
            "success": True,
            "message": "Polygon created successfully",
            "polygon_id": polygon_id,
            "name": polygon.name,
            "points_count": len(polygon.points)
        }
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(500, f"Failed to create polygon: {str(e)}")


@app.get("/api/polygon/list")
def list_polygons(active_only: bool = False):
    try:
        cursor = db.connection.cursor(dictionary=True)
        if active_only:
            cursor.execute("SELECT * FROM polygon_areas WHERE is_active = TRUE ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM polygon_areas ORDER BY created_at DESC")

        polygons = cursor.fetchall()
        cursor.close()

        for poly in polygons:
            poly['coordinates'] = json.loads(poly['coordinates'])
            poly['created_at'] = poly['created_at'].strftime("%Y-%m-%d %H:%M:%S") if poly['created_at'] else None
            poly['updated_at'] = poly['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if poly['updated_at'] else None

        return {
            "success": True,
            "count": len(polygons),
            "polygons": polygons
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/polygon/{polygon_id}")
def get_polygon(polygon_id: int):
    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM polygon_areas WHERE id = %s", (polygon_id,))
        polygon = cursor.fetchone()
        cursor.close()

        if not polygon:
            raise HTTPException(404, "Polygon not found")

        polygon['coordinates'] = json.loads(polygon['coordinates'])
        polygon['created_at'] = polygon['created_at'].strftime("%Y-%m-%d %H:%M:%S") if polygon['created_at'] else None
        polygon['updated_at'] = polygon['updated_at'].strftime("%Y-%m-%d %H:%M:%S") if polygon['updated_at'] else None

        return {
            "success": True,
            "polygon": polygon
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/api/polygon/{polygon_id}")
def update_polygon(polygon_id: int, polygon: PolygonUpdate):
    try:
        cursor = db.connection.cursor()

        # Build dynamic update query
        updates = []
        values = []

        if polygon.name:
            updates.append("name = %s")
            values.append(polygon.name)

        if polygon.description is not None:
            updates.append("description = %s")
            values.append(polygon.description)

        if polygon.points:
            if len(polygon.points) < 3:
                raise HTTPException(400, "Polygon must have at least 3 points")
            coordinates = {"points": [{"x": p.x, "y": p.y} for p in polygon.points]}
            updates.append("coordinates = %s")
            values.append(json.dumps(coordinates))

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = NOW()")
        values.append(polygon_id)

        sql = f"UPDATE polygon_areas SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(sql, values)
        db.connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "Polygon not found")

        cursor.close()

        return {
            "success": True,
            "message": "Polygon updated successfully",
            "polygon_id": polygon_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(500, str(e))


# 5. DELETE - Hapus polygon (soft delete)
@app.delete("/api/polygon/{polygon_id}")
def delete_polygon(polygon_id: int, hard_delete: bool = False):
    try:
        cursor = db.connection.cursor()

        if hard_delete:
            cursor.execute("DELETE FROM polygon_areas WHERE id = %s", (polygon_id,))
            msg = "Polygon permanently deleted"
        else:
            cursor.execute("UPDATE polygon_areas SET is_active = FALSE WHERE id = %s", (polygon_id,))
            msg = "Polygon deactivated"

        db.connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(404, "Polygon not found")

        cursor.close()
        return {
            "success": True,
            "message": msg,
            "polygon_id": polygon_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(500, str(e))

@app.put("/api/polygon/{polygon_id}/activate")
def activate_polygon(polygon_id: int):
    try:
        cursor = db.connection.cursor()

        # Cek polygon exists
        cursor.execute("SELECT id FROM polygon_areas WHERE id = %s", (polygon_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Polygon not found")

        cursor.execute("UPDATE polygon_areas SET is_active = FALSE")

        cursor.execute("UPDATE polygon_areas SET is_active = TRUE, updated_at = NOW() WHERE id = %s", (polygon_id,))

        db.connection.commit()
        cursor.close()

        return {
            "success": True,
            "message": f"Polygon {polygon_id} activated successfully",
            "polygon_id": polygon_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/polygon/reload")
def reload_polygon():
    global polygon_checker, counter, polygon_id, polygon_name, polygon_points

    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, coordinates FROM polygon_areas
            WHERE is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        polygon_config = cursor.fetchone()
        cursor.close()

        if not polygon_config:
            raise HTTPException(404, "No active polygon found in database")

        coords = json.loads(polygon_config['coordinates'])
        new_polygon_points = [(int(p['x']), int(p['y'])) for p in coords['points']]

        # Update global variables
        polygon_points = new_polygon_points
        polygon_checker = PolygonChecker(polygon_points)
        counter = PeopleCounter(polygon_checker)  # Reset counter untuk area baru
        polygon_id = polygon_config['id']
        polygon_name = polygon_config['name']

        return {
            "success": True,
            "message": "Polygon reloaded successfully",
            "polygon_id": polygon_id,
            "polygon_name": polygon_name,
            "points_count": len(polygon_points),
            "note": "Counter has been reset for the new area"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/polygon/import")
def import_polygon_from_json(data: dict):
    try:
        name = data.get('name', 'Imported Polygon')
        description = data.get('description', '')
        coordinates = data.get('coordinates', {})

        if 'points' not in coordinates or len(coordinates['points']) < 3:
            raise HTTPException(400, "Invalid polygon data: need at least 3 points")

        cursor = db.connection.cursor()
        cursor.execute("""
            INSERT INTO polygon_areas (name, description, coordinates, is_active)
            VALUES (%s, %s, %s, FALSE)
        """, (name, description, json.dumps(coordinates)))
        db.connection.commit()
        polygon_id = cursor.lastrowid
        cursor.close()

        return {
            "success": True,
            "message": "Polygon imported successfully",
            "polygon_id": polygon_id,
            "name": name,
            "points_count": len(coordinates['points'])
        }
    except HTTPException:
        raise
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(500, str(e))

def gen_frames_api():
    cap = cv2.VideoCapture(config.VIDEO_SOURCE)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("❌ Failed to open video stream!")
        return

    frame_count = 0
    fps_start = time.time()
    fps = 0

    print("✅ Video stream opened for API endpoint")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Stream interrupted, reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(config.VIDEO_SOURCE)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        frame_count += 1

        if frame_count % config.FRAME_SKIP != 0:
            continue

        results = model.track(
            frame,
            persist=True,
            tracker=config.TRACKER_TYPE + '.yaml',
            classes=config.DETECT_CLASSES,
            conf=config.CONFIDENCE_THRESHOLD,
            iou=config.IOU_THRESHOLD,
            imgsz=640,
            max_det=30,
            verbose=False,
            agnostic_nms=True
        )

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            active_track_ids = []

            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                centroid_x = int((x1 + x2) / 2)
                centroid_y = int((y1 + y2) / 2)
                centroid = (centroid_x, centroid_y)

                is_inside = polygon_checker.is_inside(centroid)

                event = counter.update(track_id, centroid, frame_count)

                active_track_ids.append(track_id)

                color = (0, 255, 0) if is_inside else (0, 0, 255)
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

                label = f"ID:{track_id} {conf:.2f}"
                cv2.putText(frame, label, (int(x1), int(y1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                cv2.circle(frame, centroid, 5, color, -1)

                if event:
                    event_text = "MASUK" if event == "entered" else "KELUAR"
                    cv2.putText(frame, event_text, (int(x1), int(y2) + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            counter.cleanup_old_tracks(active_track_ids)

        frame = polygon_checker.draw_polygon(frame, color=(255, 0, 255), thickness=3)

        stats = counter.get_stats()

        if polygon_id and frame_count % 100 == 0:
            try:
                db.update_summary(
                    polygon_area_id=polygon_id,
                    total_entered=stats['total_entered'],
                    total_exited=stats['total_exited'],
                    current_count=stats['current_inside']
                )
            except Exception as e:
                print(f"⚠️ DB update error: {e}")

        fps_end = time.time()
        time_diff = fps_end - fps_start
        if time_diff > 0:
            fps = 1 / time_diff
        fps_start = fps_end

        info_height = 150
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (350, info_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        y = 35
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += 30
        cv2.putText(frame, f"Entered: {stats['total_entered']}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += 30
        cv2.putText(frame, f"Exited: {stats['total_exited']}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        y += 30
        cv2.putText(frame, f"Inside: {stats['current_inside']}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret: continue

        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames_api(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get("/api/stats/live")
def stats_live(area_id: int = None):
    stats = counter.get_stats()
    return {
        "jumlah_orang_terdeteksi": stats['current_inside'],
        "total_masuk": stats['total_entered'],
        "total_keluar": stats['total_exited'],
        "waktu_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/api/stats/history")
def stats_history(minutes: int = 60):
    t0 = datetime.now() - timedelta(minutes=minutes)
    try:
        cur = db.connection.cursor()
        cur.execute(
            "SELECT updated_at, current_count FROM counting_summary WHERE updated_at >= %s ORDER BY updated_at",
            (t0,)
        )
        rows = cur.fetchall()
        cur.close()
        times = [r[0].strftime("%Y-%m-%d %H:%M:%S") for r in rows]
        counts = [r[1] for r in rows]
        return {"times": times, "counts": counts}
    except Exception as e:
        raise HTTPException(500, str(e))


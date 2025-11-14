import cv2
import torch
from ultralytics import YOLO
import numpy as np
from datetime import datetime
import time

from config.config import Config
from core.polygon import PolygonChecker
from core.counter import PeopleCounter
from database.db_manager import DatabaseManager


def main():
    print("=" * 70)
    print("🎥 PEOPLE COUNTING SYSTEM - YOLOv11 + BoT-SORT")
    print("=" * 70)

    config = Config()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n🔧 Device: {device}")
    if device == 'cuda':
        print(f"🎮 GPU: {torch.cuda.get_device_name(0)}")

    print(f"\n📦 Loading YOLOv11 Medium...")
    model = YOLO(config.YOLO_MODEL)
    model.to(device)
    print(f"✅ Model loaded on {device}")
    print(f"\n💾 Connecting to database...")
    db = DatabaseManager()

    print(f"\n📐 Loading polygon configuration from database...")

    try:
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, coordinates, description, is_active
            FROM polygon_areas
            WHERE is_active = TRUE
            ORDER BY created_at DESC
        """)
        available_polygons = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"❌ Error querying polygons: {e}")
        available_polygons = []

    polygon_config = None
    polygon_points = None
    polygon_name = None
    polygon_id = None

    if available_polygons:
        print(f"✅ Found {len(available_polygons)} active polygon(s) in database")
        if len(available_polygons) == 1:
            polygon_config = available_polygons[0]
            print(f"✅ Auto-selected: {polygon_config['name']} (ID: {polygon_config['id']})")
        else:
            print("\n📋 Available Polygons:")
            print("-" * 70)
            for i, poly in enumerate(available_polygons, 1):
                import json
                coords = json.loads(poly['coordinates'])
                print(f"  [{i}] ID: {poly['id']} | Name: {poly['name']} | Points: {len(coords['points'])}")
                print(f"      Description: {poly['description']}")
            print("-" * 70)

            while True:
                try:
                    choice = input(f"\nSelect polygon [1-{len(available_polygons)}] or 'q' to quit: ").strip()

                    if choice.lower() == 'q':
                        print("👋 Exiting...")
                        db.close()
                        return

                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(available_polygons):
                        polygon_config = available_polygons[choice_idx]
                        print(f"✅ Selected: {polygon_config['name']}")
                        break
                    else:
                        print(f"⚠️ Invalid choice. Enter number 1-{len(available_polygons)}")
                except ValueError:
                    print("⚠️ Invalid input. Enter a number or 'q'")

        if polygon_config:
            import json
            coords = json.loads(polygon_config['coordinates'])
            polygon_points = [(p['x'], p['y']) for p in coords['points']]
            polygon_name = polygon_config['name']
            polygon_id = polygon_config['id']

            print(f"\n✅ Polygon Configuration:")
            print(f"   ID: {polygon_id}")
            print(f"   Name: {polygon_name}")
            print(f"   Points: {len(polygon_points)}")
            print(f"   Description: {polygon_config['description']}")

    else:
        print("\n" + "=" * 70)
        print("⚠️ NO POLYGONS FOUND IN DATABASE!")
        print("=" * 70)
        print("\nYou have 3 options:")
        print("  [1] Create polygon using GUI Editor (RECOMMENDED)")
        print("  [2] Use default polygon (for testing)")
        print("  [3] Exit and create polygon manually")
        print("=" * 70)

        while True:
            choice = input("\nSelect option [1-3]: ").strip()

            if choice == '1':
                print("\n🎨 Launching Polygon Editor...")
                print("=" * 70)
                print("INSTRUCTIONS:")
                print("1. Click on the video frame to add polygon points")
                print("2. Right-click to remove last point")
                print("3. Press 'c' or ENTER when done (minimum 3 points)")
                print("4. Enter polygon name and description")
                print("5. Polygon will be saved to database")
                print("=" * 70)

                input("\nPress ENTER to launch editor...")

                try:
                    from tools.polygon_editor import PolygonEditor
                    editor = PolygonEditor(video_source=config.VIDEO_SOURCE)
                    editor.run()

                    print("\n🔄 Reloading polygons from database...")

                    # Reload polygons after editor closes
                    cursor = db.connection.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT id, name, coordinates, description
                        FROM polygon_areas
                        WHERE is_active = TRUE
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    polygon_config = cursor.fetchone()
                    cursor.close()

                    if polygon_config:
                        import json
                        coords = json.loads(polygon_config['coordinates'])
                        polygon_points = [(p['x'], p['y']) for p in coords['points']]
                        polygon_name = polygon_config['name']
                        polygon_id = polygon_config['id']
                        print(f"✅ Polygon loaded: {polygon_name}")
                        break
                    else:
                        print("⚠️ No polygon created. Trying again...")
                        continue

                except ImportError as e:
                    print(f"❌ Error importing polygon editor: {e}")
                    print("   Make sure tools/polygon_editor.py exists")
                    continue
                except Exception as e:
                    print(f"❌ Error running polygon editor: {e}")
                    continue

            elif choice == '2':
                print("\n⚠️ Using default polygon (for testing only)")
                polygon_points = config.DEFAULT_POLYGON
                polygon_name = "Default Test Area"
                polygon_id = None
                print(f"✅ Default polygon loaded: {len(polygon_points)} points")
                break

            elif choice == '3':
                print("\n📝 To create polygon manually, run:")
                print("   python tools/polygon_editor.py")
                print("\n👋 Exiting...")
                db.close()
                return

            else:
                print("⚠️ Invalid option. Please select 1, 2, or 3")

    if not polygon_points or len(polygon_points) < 3:
        print("\n❌ ERROR: Invalid polygon configuration!")
        print("   Polygon must have at least 3 points")
        db.close()
        return

    print("\n" + "=" * 70)
    print(f"✅ POLYGON READY: {polygon_name}")
    print(f"   Total Points: {len(polygon_points)}")
    print("=" * 70)

    polygon_checker = PolygonChecker(polygon_points)

    counter = PeopleCounter(polygon_checker)


    print(f"\n🎥 Opening video stream...")
    print(f"📡 Source: {config.VIDEO_SOURCE[:60]}...")

    cap = cv2.VideoCapture(config.VIDEO_SOURCE)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("❌ Failed to open video stream!")
        return

    print("✅ Video stream opened")
    print("\n" + "=" * 70)
    print("🚀 STARTING DETECTION & TRACKING...")
    print("Press 'q' to quit | 's' to save screenshot")
    print("=" * 70 + "\n")

    frame_count = 0
    fps_start_time = time.time()
    fps = 0

    try:
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
                conf=config.CONFIDENCE_THRESHOLD,  # Now 0.25
                iou=config.IOU_THRESHOLD,  # Now 0.3
                imgsz=640,  # High resolution processing
                max_det=30,  # Allow more detections
                verbose=False,
                agnostic_nms=True  # ← TAMBAHKAN: Better NMS for crowded scenes
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

                    if frame_count % 30 == 0:
                        db.save_detection(
                            tracking_id=int(track_id),
                            polygon_area_id=polygon_id,
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            centroid=centroid,
                            confidence=float(conf),
                            is_inside=is_inside,
                            frame_number=frame_count,
                            video_source=config.VIDEO_SOURCE
                        )

                    if event:
                        db.save_counting_event(
                            polygon_area_id=polygon_id,
                            tracking_id=int(track_id),
                            event_type=event,
                            frame_number=frame_count,
                            video_source=config.VIDEO_SOURCE
                        )

                    active_track_ids.append(track_id)

                    color = (0, 255, 0) if is_inside else (0, 0, 255)
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

                    label = f"ID:{track_id} {conf:.2f}"
                    cv2.putText(frame, label, (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    cv2.circle(frame, centroid, 5, color, -1)

                counter.cleanup_old_tracks(active_track_ids)

            frame = polygon_checker.draw_polygon(frame, color=(255, 0, 255), thickness=3)

            stats = counter.get_stats()

            if frame_count % 100 == 0:
                db.update_summary(
                    polygon_area_id=polygon_id,
                    total_entered=stats['total_entered'],
                    total_exited=stats['total_exited'],
                    current_count=stats['current_inside']
                )

            fps_end_time = time.time()
            time_diff = fps_end_time - fps_start_time
            if time_diff > 0:
                fps = 1 / time_diff
            fps_start_time = fps_end_time

            info_height = 180
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (400, info_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            y_offset = 35
            cv2.putText(frame, f"FPS: {fps:.1f}", (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 30
            cv2.putText(frame, f"Frame: {frame_count}", (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
            cv2.putText(frame, f"Entered: {stats['total_entered']}", (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 30
            cv2.putText(frame, f"Exited: {stats['total_exited']}", (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_offset += 30
            cv2.putText(frame, f"Inside: {stats['current_inside']}", (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            display_frame = cv2.resize(frame, (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT))

            cv2.imshow('People Counting - YOLOv11 + BoT-SORT', display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n🛑 Stopping...")
                break
            elif key == ord('s'):
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(filename, frame)
                print(f"📸 Screenshot saved: {filename}")

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()

        print("\n" + "=" * 70)
        print("📊 FINAL STATISTICS")
        print("=" * 70)
        final_stats = counter.get_stats()
        print(f"Total Entered: {final_stats['total_entered']}")
        print(f"Total Exited: {final_stats['total_exited']}")
        print(f"Currently Inside: {final_stats['current_inside']}")
        print(f"Total Tracked Objects: {final_stats['total_tracked']}")
        print(f"Total Frames Processed: {frame_count}")
        print("=" * 70)
        print("✅ System stopped successfully")


if __name__ == "__main__":
    main()
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'people_counting_db')
    DB_USER = os.getenv('DB_USER', 'cv_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'cvpassword123')

    # Video Source
    VIDEO_SOURCE = os.getenv('VIDEO_SOURCE',
                             'https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8')

    # YOLO Configuration
    YOLO_MODEL = 'yolo11m.pt'  # YOLOv11 Medium
    CONFIDENCE_THRESHOLD = 0.25
    IOU_THRESHOLD = 0.45

    # Tracking Configuration
    TRACKER_TYPE = 'botsort'  # botsort, bytetrack
    TRACKER_CONFIG = None  # Use default ultralytics config

    # Polygon Area (default - bisa diambil dari database)
    DEFAULT_POLYGON = [
        [200, 300],  # Top-left
        [800, 300],  # Top-right
        [800, 600],  # Bottom-right
        [200, 600]  # Bottom-left
    ]

    # Processing
    FRAME_SKIP = 1  # Process every N frames (1 = no skip)
    DISPLAY_WIDTH = 1280
    DISPLAY_HEIGHT = 720

    # Classes to detect (COCO dataset)
    DETECT_CLASSES = [0]  # 0 = person only
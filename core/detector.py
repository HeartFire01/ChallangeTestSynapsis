import cv2
from ultralytics import YOLO
import numpy as np
class PersonDetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.model = YOLO(model_path)
    def detect(self, frame):
        result = self.model(frame)[0]
        boxes = []
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            clss = int(box.cls[0])
            if clss == 0 and conf > 0.3:
                boxes.append((x1, y1, x2, y2, conf))
        return boxes
    def draw_boxes(self, frame, boxes):
        for (x1, y1, x2, y2, conf) in boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(frame, f"{conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
        return frame

import cv2
import numpy as np


class PolygonChecker:
    """
    Class untuk mengecek apakah point berada di dalam polygon
    """

    def __init__(self, polygon_points):
        """
        Args:
            polygon_points: List of [x, y] coordinates
        """
        self.polygon = np.array(polygon_points, dtype=np.int32)

    def is_inside(self, point):
        """
        Cek apakah point (x, y) berada di dalam polygon

        Args:
            point: Tuple (x, y)

        Returns:
            bool: True jika di dalam polygon
        """
        result = cv2.pointPolygonTest(self.polygon, point, False)
        return result >= 0

    def draw_polygon(self, frame, color=(0, 255, 0), thickness=2):
        """
        Gambar polygon di frame
        """
        cv2.polylines(frame, [self.polygon], True, color, thickness)
        return frame

    def get_centroid(self):
        """
        Dapatkan centroid dari polygon
        """
        M = cv2.moments(self.polygon)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            return (cx, cy)
        return None
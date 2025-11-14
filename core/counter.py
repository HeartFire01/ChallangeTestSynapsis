from collections import defaultdict
from datetime import datetime


class PeopleCounter:
    """
    Class untuk tracking dan counting orang masuk/keluar polygon
    """

    def __init__(self, polygon_checker):
        self.polygon_checker = polygon_checker

        # Track status setiap object
        self.tracked_objects = {}  # {track_id: {'inside': bool, 'last_centroid': (x,y)}}

        # Counters
        self.total_entered = 0
        self.total_exited = 0
        self.current_inside = 0

        # Events log
        self.events = []  # List of events untuk disimpan ke database

    def update(self, track_id, centroid, frame_number):
        """
        Update status tracking object

        Args:
            track_id: ID tracking dari tracker
            centroid: (x, y) centroid dari bounding box
            frame_number: Frame number saat ini

        Returns:
            event: 'ENTER', 'EXIT', or None
        """
        is_inside = self.polygon_checker.is_inside(centroid)
        event = None

        # Jika object baru
        if track_id not in self.tracked_objects:
            self.tracked_objects[track_id] = {
                'inside': is_inside,
                'last_centroid': centroid
            }

            # Jika object pertama kali muncul di dalam polygon
            if is_inside:
                self.current_inside += 1

        else:
            # Object sudah ada, cek perubahan status
            prev_status = self.tracked_objects[track_id]['inside']

            # Deteksi boundary crossing
            if not prev_status and is_inside:
                # Outside -> Inside = ENTER
                self.total_entered += 1
                self.current_inside += 1
                event = 'ENTER'

                self.events.append({
                    'track_id': track_id,
                    'event_type': 'ENTER',
                    'timestamp': datetime.now(),
                    'frame_number': frame_number,
                    'centroid': centroid
                })

                print(f"✅ ENTER: Track ID {track_id} | Total Entered: {self.total_entered}")

            elif prev_status and not is_inside:
                # Inside -> Outside = EXIT
                self.total_exited += 1
                self.current_inside -= 1
                event = 'EXIT'

                self.events.append({
                    'track_id': track_id,
                    'event_type': 'EXIT',
                    'timestamp': datetime.now(),
                    'frame_number': frame_number,
                    'centroid': centroid
                })

                print(f"⬅️ EXIT: Track ID {track_id} | Total Exited: {self.total_exited}")

            # Update status
            self.tracked_objects[track_id]['inside'] = is_inside
            self.tracked_objects[track_id]['last_centroid'] = centroid

        return event

    def get_stats(self):
        """
        Dapatkan statistik counting
        """
        return {
            'total_entered': self.total_entered,
            'total_exited': self.total_exited,
            'current_inside': self.current_inside,
            'total_tracked': len(self.tracked_objects)
        }

    def get_pending_events(self):
        """
        Dapatkan events yang belum disimpan ke database
        """
        events = self.events.copy()
        self.events.clear()
        return events

    def cleanup_old_tracks(self, active_track_ids):
        """
        Hapus tracking object yang sudah tidak aktif
        """
        inactive_ids = set(self.tracked_objects.keys()) - set(active_track_ids)
        for track_id in inactive_ids:
            # Jika object hilang saat masih di dalam, kurangi counter
            if self.tracked_objects[track_id]['inside']:
                self.current_inside -= 1
            del self.tracked_objects[track_id]
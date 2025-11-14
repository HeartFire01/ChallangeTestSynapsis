import cv2
import time
import threading
from queue import Queue


class LiveStreamReader:
    """
    Thread-safe stream reader untuk real-time playback
    """

    def __init__(self, url, queue_size=1):
        self.url = url
        self.queue = Queue(maxsize=queue_size)
        self.stopped = False
        self.cap = None

    def start(self):
        """Start thread untuk membaca frame"""
        self.cap = cv2.VideoCapture(self.url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            print("❌ Gagal membuka stream!")
            return self

        # Start background thread
        threading.Thread(target=self._read_frames, daemon=True).start()
        return self

    def _read_frames(self):
        """Background thread untuk membaca frame"""
        while not self.stopped:
            if not self.cap.isOpened():
                self.stopped = True
                break

            ret, frame = self.cap.read()

            if not ret:
                # Reconnect jika gagal
                print("⚠️ Reconnecting...")
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue

            # Clear queue dan masukkan frame terbaru (untuk live streaming)
            if not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except:
                    pass

            self.queue.put(frame)

    def read(self):
        """Baca frame dari queue"""
        if self.queue.empty():
            return False, None
        return True, self.queue.get()

    def stop(self):
        """Stop thread"""
        self.stopped = True
        if self.cap:
            self.cap.release()

    def get_fps(self):
        """Get FPS dari stream"""
        if self.cap:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            return fps if fps > 0 and fps <= 60 else 25
        return 25


def realtime_viewer_threaded(url):
    """
    Real-time viewer menggunakan threading
    """
    print("🔄 Memulai stream dengan threading...")

    # Start stream reader
    stream = LiveStreamReader(url, queue_size=1).start()
    time.sleep(2)  # Tunggu buffer awal

    # Get FPS
    target_fps = stream.get_fps()
    frame_delay = 1.0 / target_fps

    print(f"✅ Target FPS: {target_fps}")
    print(f"✅ Frame delay: {frame_delay:.3f}s")
    print("✅ Stream dimulai! Tekan 'q' untuk keluar.\n")

    frame_count = 0
    start_time = time.time()
    last_time = time.time()

    while True:
        loop_start = time.time()

        # Baca frame
        ret, frame = stream.read()

        if not ret:
            time.sleep(0.01)
            continue

        frame_count += 1

        # Hitung actual FPS
        current_time = time.time()
        actual_fps = 1 / (current_time - last_time) if (current_time - last_time) > 0 else 0
        last_time = current_time

        # Resize
        display_frame = cv2.resize(frame, (1280, 720))

        # Info overlay
        cv2.putText(display_frame, f"Target FPS: {target_fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Actual FPS: {actual_fps:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Frame: {frame_count}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display
        cv2.imshow("CCTV Real-Time (Threaded)", display_frame)

        # Hitung waktu yang sudah digunakan
        elapsed = time.time() - loop_start

        # Sleep untuk mencapai target FPS
        sleep_time = max(0, frame_delay - elapsed)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Sleep sisanya
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Cleanup
    stream.stop()
    cv2.destroyAllWindows()

    total_time = time.time() - start_time
    avg_fps = frame_count / total_time if total_time > 0 else 0

    print(f"\n✅ Stream selesai")
    print(f"📊 Total frame: {frame_count}")
    print(f"📊 Durasi: {total_time:.1f}s")
    print(f"📊 Average FPS: {avg_fps:.2f}")


if __name__ == "__main__":
    cctv_url = "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8"

    print("=" * 70)
    print("🎥 CCTV REAL-TIME VIEWER (THREADED)")
    print("=" * 70)
    print("\nPilih mode:")
    print("1. Simple (tanpa threading)")
    print("2. Threaded (lebih smooth)")

    choice = input("\nPilihan (1/2): ").strip()

    if choice == "2":
        realtime_viewer_threaded(cctv_url)
    else:
        get_realtime_stream(cctv_url, "CCTV Malioboro - Real Time")
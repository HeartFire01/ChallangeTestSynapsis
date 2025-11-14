import cv2

video_path = '/home/purba/Cars.mp4'
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error : Tidak dapat membuka video")
else:
    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        print("Error : FPS tidak bisa dibaca dengan benar")
    else:
        print(f"FPS yang terdeteksi : {fps}")

        while True:
            ret, frame = cap.read()

            if not ret:
                print("Video selesai atau gagal membaca frame")
                break


            cv2.imshow('Video Playback', frame)
            delay = int(1000 / fps)
            if cv2.waitKey(delay) & 0XFF == ord('q'):
                break

cap.release()
cv2.destroyAllWindows()
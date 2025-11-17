# Project Challenge Overview

## Challenge #1 - DONE
- ERD sudah disimpan dalam bentuk `.png`

## Challenge #2 - DONE
- Untuk tahapan ini, penulis menggunakan video live CCTV streaming di Pasar Beringharjo - Malioboro - D.I.Y Jogjakarta (https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8)

## Challenge #3 - DONE
- Untuk deteksi orang, penulis menggunakan **YOLOv5** dengan medium model.
- Tracking objek menggunakan **BOT-SORT** (centroid).

## Challenge #4 - DONE
- Fitur **polygon** sudah dibuat (lebih dari satu titik).
- Counter untuk deteksi sudah dibuat.

## Challenge #5 - DONE
- Fitur **polygon** sudah dibuat (lebih dari satu titik).
- Counter untuk deteksi sudah dibuat.

## Challenge #6 - DONE
- API sudah diimplementasikan.
- Adanya fitur **dashboard** untuk menunjukkan grafik deteksi orang.

## Challenge #7 - DONE
- Penulis menggunakan metode **local**.
- Requirements dan lain sebagainya sudah disiapkan.

---

## Setup Instructions


# Perintah untuk install library
pip install -r requirements.txt

# Login ke MySQL
mysql -u root -p

# Import schema
source database/schema.sql

# Atau
mysql -u root -p < database/schema.sql

cp .env.example .env
# Edit .env dengan kredensial Anda
nano .env



# Cara menjalankan di Terminal :


uvicorn api_app:app --reload --> Start Server

http://localhost:8000/docs --> akses dashboard
http://localhost:8000/video_feed --> akses live video playback


python tools/polygon_editor.py --> Run untuk konfigurasi edit polygon
streamlit run tools/streamlit1.py --> Run untuk melihat statistik

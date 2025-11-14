import streamlit as st
import requests
import time
import pandas as pd

STATS_URL = 'http://localhost:8000/api/stats/live'
GRAPH_URL = 'http://localhost:8000/api/stats/history'
VIDEO_FEED_URL = 'http://localhost:8000/video_feed'
STATS_HISTORY_URL = "http://localhost:8000/api/stats/history"


st.title("Live Statistik: Grafik Jumlah Orang Masuk Area")
minutes = st.slider("Lama waktu histori (menit)", 10, 180, 60)
params = {"minutes": minutes}
# Fetch data dari API stats/history
res = requests.get(STATS_HISTORY_URL, params=params)
data = res.json()
if "times" in data and len(data["times"]) > 0:
    df = pd.DataFrame({"count": data["counts"]}, index=pd.to_datetime(data["times"]))
    st.line_chart(df)
    st.dataframe(df.tail(10))
else:
    st.info("Belum ada data summary statistik di database.")
st.title("Live People Counting Dashboard")

col1, col2 = st.columns(2)

with col1:
    st.header("Live Video")
    st.image(VIDEO_FEED_URL)

with col2:
    st.header("Statistik Real Time")
    live_json = requests.get(STATS_URL).json()
    st.metric("Orang Terhitung Sekarang", live_json.get("jumlah_orang_terdeteksi",0))
    st.markdown(f"Update terakhir: *{live_json.get('waktu_update','-')}*")


place = st.empty()
while True:
    graph_json = requests.get(GRAPH_URL).json()
    if "times" in graph_json:
        df = pd.DataFrame({"COUNT": graph_json['counts']}, index=pd.to_datetime(graph_json['times']))
        place.line_chart(df)
    time.sleep(5)
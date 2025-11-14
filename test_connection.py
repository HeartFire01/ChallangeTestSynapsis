import mysql.connector
from mysql.connector import Error


def test_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='people_counting_db',
            user='cv_user',
            password='cvpassword123'  # Ganti dengan password yang Anda buat
        )

        if connection.is_connected():
            print("✅ Berhasil terhubung ke MySQL!")

            cursor = connection.cursor()

            # Test query
            cursor.execute("SELECT DATABASE();")
            db = cursor.fetchone()
            print(f"✅ Database aktif: {db[0]}")

            # Lihat semua tabel
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print("\n📋 Daftar tabel:")
            for table in tables:
                print(f"   - {table[0]}")

            # Lihat data polygon_areas
            cursor.execute("SELECT * FROM polygon_areas;")
            areas = cursor.fetchall()
            print(f"\n✅ Jumlah polygon areas: {len(areas)}")

            cursor.close()
            connection.close()
            print("\n✅ Koneksi ditutup")

    except Error as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_connection()
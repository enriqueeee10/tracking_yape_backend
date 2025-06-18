import psycopg2

try:
    conn = psycopg2.connect(
        "postgresql://postgres:admin12345@localhost:5432/YAPEtracking"
    )
    print("✅ Conexión exitosa a PostgreSQL")
    conn.close()
except Exception as e:
    print("❌ Error al conectar:")
    print(e)

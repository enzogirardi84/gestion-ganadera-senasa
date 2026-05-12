import psycopg2

hosts = [
    ("db.tfdgaxowacbxqtuvhhdp.supabase.co", 5432, "postgres"),
    ("aws-0-sa-east-1.pooler.supabase.com", 6543, "postgres.tfdgaxowacbxqtuvhhdp"),
    ("tfdgaxowacbxqtuvhhdp.supabase.co", 5432, "postgres"),
]

password = "Enzo37108100"

for host, port, user in hosts:
    try:
        conn = psycopg2.connect(host=host, port=port, dbname="postgres", user=user, password=password, connect_timeout=10)
        print(f"CONECTADO! {host}:{port} as {user}")
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' LIMIT 10")
        for r in cur.fetchall():
            print(f"  Tabla: {r[0]}")
        conn.close()
        break
    except Exception as e:
        print(f"Fallo {host}:{port} as {user}: {str(e)[:100]}")

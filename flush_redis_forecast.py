import redis

def flush_forecast_cache():
    try:
        r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
        keys = r.keys("forecast_*")
        if keys:
            r.delete(*keys)
            print(f"✅ Borradas {len(keys)} claves de forecast de Redis.")
        else:
            print("ℹ️ No hay claves de forecast activas en Redis.")
    except Exception as e:
        print(f"❌ Error al conectar o borrar Redis: {e}")

if __name__ == "__main__":
    flush_forecast_cache()

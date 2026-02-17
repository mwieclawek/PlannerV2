
try:
    from app import schemas
    print("Schemas imported successfully")
except Exception as e:
    import traceback
    traceback.print_exc()

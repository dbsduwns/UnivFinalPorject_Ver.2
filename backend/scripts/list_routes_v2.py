from app.main import app

print("--- Registered Routes ---")
for route in app.routes:
    path = getattr(route, "path", "N/A")
    methods = getattr(route, "methods", "N/A")
    print(f"Path: {path}, Methods: {methods}")

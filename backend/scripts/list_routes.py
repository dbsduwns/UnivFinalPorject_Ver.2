from app.main import app

print("--- Registered Routes ---")
for route in app.routes:
    # Check if it's an APIRoute
    if hasattr(route, "path"):
        print(f"Path: {route.path}, Methods: {route.methods}")

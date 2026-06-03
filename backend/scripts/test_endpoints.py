import requests

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(path):
    url = f"{BASE_URL}{path}"
    print(f"Checking {url}...")
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_endpoint("/health")
    check_endpoint("/auth/notification-settings") # This should return 401 if it exists, or 404 if it doesn't

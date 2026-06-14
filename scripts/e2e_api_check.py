"""Simple end-to-end API check script.

Performs:
 - POST /auth/login (seeded user)
 - POST /games (create a test game)
 - POST /reviews (try to create a review for an existing game)
 - GET /dashboard

Prints status codes and JSON/text responses for diagnosis.
"""
import requests
import json

BASE = "http://localhost:8000/api/v1"

def pretty_print_resp(resp):
    print(f"URL: {resp.request.method} {resp.url}")
    print(f"STATUS: {resp.status_code}")
    ctype = resp.headers.get("content-type","")
    if "application/json" in ctype:
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
    else:
        print(resp.text)
    print("---")

if __name__ == '__main__':
    s = requests.Session()
    try:
        print("Logging in as alex@example.com / password123")
        r = s.post(f"{BASE}/auth/login", json={"email":"alex@example.com","password":"password123"}, timeout=10)
        pretty_print_resp(r)
        r.raise_for_status()
        token = r.json().get("access_token")
        if not token:
            print("No access token in login response; aborting")
            raise SystemExit(1)
    except Exception as exc:
        print("Login failed:", exc)
        raise

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create a test game
    try:
        print("Creating a test game")
        r = s.post(f"{BASE}/games", headers=headers, json={"title": "Test Game from E2E", "external_id": "ext-e2e-1234"}, timeout=10)
        pretty_print_resp(r)
    except Exception as exc:
        print("Create game failed:", exc)

    # Try to create a review for a seeded game id (may already exist)
    try:
        print("Creating a review for seeded game id 21103413-916a-471b-8ba4-80e6d15aed74")
        r = s.post(f"{BASE}/reviews", headers=headers, json={"game_id":"21103413-916a-471b-8ba4-80e6d15aed74","rating":8,"review_text":"fun"}, timeout=10)
        pretty_print_resp(r)
    except Exception as exc:
        print("Create review failed:", exc)

    # Fetch dashboard
    try:
        print("Fetching dashboard")
        r = s.get(f"{BASE}/dashboard", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        pretty_print_resp(r)
    except Exception as exc:
        print("Dashboard fetch failed:", exc)

    print("E2E script finished")

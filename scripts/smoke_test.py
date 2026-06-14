import requests

API = "http://localhost:8000/api/v1"

print('Logging in...')
resp = requests.post(f"{API}/auth/login", json={"email": "alex@example.com", "password": "password123"})
resp.raise_for_status()
body = resp.json()
access = body["access_token"]
print('Access token obtained')

headers = {"Authorization": f"Bearer {access}"}
print('Fetching dashboard...')
d = requests.get(f"{API}/dashboard", headers=headers)
d.raise_for_status()
print('Dashboard:', d.json())

# get groups
groups = d.json().get('groups')
if not groups:
    print('No groups found')
    raise SystemExit(1)
gid = groups[0]['id']
print('Generating recommendations for group', gid)
rg = requests.post(f"{API}/groups/{gid}/recommendations/generate", headers=headers)
rg.raise_for_status()
print('Generated:', rg.json())

print('Listing recommendations')
list_r = requests.get(f"{API}/groups/{gid}/recommendations", headers=headers)
list_r.raise_for_status()
print('Recommendations:', list_r.json())

print('Smoke test completed')

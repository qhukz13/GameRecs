import requests, os
API = os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:8000/api/v1')
email='alex@example.com'
password='password123'
r = requests.post(f'{API}/auth/login', json={'email':email,'password':password})
print('login', r.status_code)
if r.status_code==200:
    token=r.json()['access_token']
    h={'Authorization':f'Bearer {token}'}
    g = requests.get(f'{API}/games', headers=h, timeout=5)
    print('/games', g.status_code)
    print(g.text[:2000])
else:
    print(r.text)

import requests
API='http://localhost:8000/api/v1'
email='alex@example.com'
password='password123'
r = requests.post(f'{API}/auth/login', json={'email':email,'password':password})
print('login', r.status_code)
if r.status_code==200:
    token=r.json()['access_token']
    h={'Authorization':f'Bearer {token}'}
    q='portal'
    r = requests.get(f'{API}/external/steam/search', params={'q':q}, headers=h, timeout=10)
    print('search', r.status_code)
    print(r.text[:4000])
else:
    print(r.text)

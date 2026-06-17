import requests, os
API = os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:8000/api/v1')
email='alex@example.com'
password='password123'
r = requests.post(f'{API}/auth/login', json={'email':email,'password':password})
print('login', r.status_code)
if r.status_code==200:
    token=r.json()['access_token']
    h={'Authorization':f'Bearer {token}'}
    gu = requests.get(f'{API}/groups', headers=h, timeout=5)
    print('/groups', gu.status_code)
    print(gu.text)
    try:
        u = requests.get(f'{API}/users', headers=h, timeout=5)
        print('/users', u.status_code)
        print(u.text[:1000])
    except Exception as e:
        print('users failed', e)
else:
    print(r.text)

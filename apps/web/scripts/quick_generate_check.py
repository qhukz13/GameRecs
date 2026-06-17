import requests, sys, time, os
API = os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:8000/api/v1')
# demo creds
email='alex@example.com'
password='password123'

def call(method, url, **kwargs):
    start=time.time()
    try:
        r = requests.request(method, url, timeout=15, **kwargs)
    except Exception as e:
        print(f'ERROR {method} {url} -> {e}')
        return None
    dt=time.time()-start
    print(f'{method} {url} -> {r.status_code} ({dt:.2f}s)')
    return r

# login
r = call('POST', f'{API}/auth/login', json={'email':email,'password':password})
if not r or r.status_code!=200:
    print('login failed')
    sys.exit(1)

token = r.json()['access_token']
headers={'Authorization':f'Bearer {token}'}
# get groups
r = call('GET', f'{API}/groups', headers=headers)
if not r or r.status_code!=200:
    print('groups failed')
    sys.exit(1)

groups=r.json()
if not groups:
    print('no groups')
    sys.exit(0)

group_id=groups[0]['id']
print('using group', group_id)
# generate
r = call('POST', f'{API}/groups/{group_id}/recommendations/generate', headers=headers)
if not r:
    print('generate errored')
else:
    print('generate response len', len(r.text))
    try:
        print('json', r.json())
    except Exception as e:
        print('no json', e)
# list
r = call('GET', f'{API}/groups/{group_id}/recommendations', headers=headers)
if r:
    print('list len', len(r.text))
    try:
        print('list json sample', r.json()[:2])
    except Exception as e:
        print('no json in list', e)

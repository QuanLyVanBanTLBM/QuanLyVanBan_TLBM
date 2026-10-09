import requests
url = 'http://127.0.0.1:8000/api/documents/export/?loai=DEN'
# use same token printed earlier
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwMjQyNTU0LCJpYXQiOjE3OTAyMTM3NTQsImp0aSI6ImE5YTZiODljODNhMDRjZjY4N2IxYWY1YTY2Y2MxMGUzIiwidXNlcl9pZCI6IjEifQ.0Gjy1D5TItfsZLSVyGk2I8RTWe27eTgXDLX6lQA00Q'
headers = {'Authorization': f'Bearer {token}'}
try:
    r = requests.get(url, headers=headers, timeout=10)
    print('STATUS', r.status_code)
    print('CONTENT-TYPE', r.headers.get('content-type'))
    try:
        print('JSON:', r.json())
    except Exception:
        print('TEXT:', r.text[:500])
except Exception as e:
    print('EXCEPTION', e)

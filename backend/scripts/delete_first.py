import requests
from pprint import pprint
BASE='http://127.0.0.1:8000'
# Use access token created earlier. Replace if needed.
TOKEN='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwMjQyNTU0LCJpYXQiOjE3OTAyMTM3NTQsImp0aSI6ImE5YTZiODljODNhMDRjZjY4N2IxYWY1YTY2Y2MxMGUzIiwidXNlcl9pZCI6IjEifQ.0Gjy1D5TItfsZLSVyGk2I8RTWe27eTgXDLX6lQA00Q'
HEADERS={'Authorization':f'Bearer {TOKEN}'}

try:
    r = requests.get(f"{BASE}/api/documents/?loai=DEN", headers=HEADERS, timeout=10)
    print('LIST', r.status_code)
    try:
        data = r.json()
        pprint(data)
    except Exception:
        print(r.text[:400])

    if r.ok:
        items = data.get('results', data) if isinstance(data, dict) else data
        if items:
            first = items[0]
            doc_id = first.get('id')
            print('Deleting id', doc_id)
            dr = requests.delete(f"{BASE}/api/documents/{doc_id}/", headers=HEADERS, timeout=10)
            print('DELETE', dr.status_code)
            try:
                print(dr.json())
            except Exception:
                print(dr.text[:400])
        else:
            print('No items')
except Exception as e:
    print('ERROR', e)

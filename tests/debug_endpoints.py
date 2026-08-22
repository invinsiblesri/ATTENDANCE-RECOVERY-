import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from agent.api import app

client = TestClient(app)

print("=== EXPORT ENDPOINTS ===")
for fmt in ['pdf', 'xml', 'json', 'csv']:
    res = client.get(f'/api/export/S001/{fmt}')
    ct = res.headers.get('content-type', 'MISSING')
    cd = res.headers.get('content-disposition', 'MISSING')
    print(f"{fmt.upper()}: status={res.status_code} len={len(res.content)} type={ct} disp={cd}")

print("\n=== AGENT QUERY ===")
res2 = client.post('/agent/query', json={'student_id': 'S001', 'message': 'give my attendance as a pdf'})
j = res2.json()
print("Status:", res2.status_code)

def safe(v):
    return str(v).encode('ascii', 'replace').decode()

print("active_agent:", safe(j.get('active_agent')))
print("action_type:", safe(j.get('action_type')))
print("download_url:", safe(j.get('download_url')))
print("answer:", safe(str(j.get('answer',''))[:300]))

print("\n=== API ROUTES ===")
for r in app.routes:
    print(str(getattr(r, 'methods', '-')).ljust(10), getattr(r, 'path', '-'))

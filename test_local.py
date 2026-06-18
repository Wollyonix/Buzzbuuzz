import os, json
os.environ['SESSION_SECRET']='test'
from app import app
client = app.test_client()
headers={'Authorization':'Bearer fakekey','Content-Type':'application/json'}
body={
  'model':'deepseek/deepseek-v4-flash',
  'messages':[{'role':'system','content':'You are a test.'},{'role':'user','content':'Hello'}],
  'stream': False
}
resp = client.post('/v1/chat/completions', headers=headers, data=json.dumps(body))
print('STATUS', resp.status_code)
print('BODY', resp.get_data(as_text=True)[:2000])

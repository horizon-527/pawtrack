import tempfile
import time
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import HTTPException
from server.production import create_app
from server.storage import digest

class Production(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        async def login(code):
            if code=='bad': raise HTTPException(401,'invalid code')
            return 'wx-'+code
        self.app=create_app(Path(self.tmp.name)/'service.sqlite3',login)
        self.store=self.app.state.store
        self.client=TestClient(self.app)
        self.hardware=self.store.provision('pet-one')
        self.other_hardware=self.store.provision('pet-two')
        self.owner=self.auth('owner')
        self.other=self.auth('other')
        self.device={'Authorization':'Bearer '+self.hardware['deviceToken']}
        self.client.post('/v1/devices/bind',headers=self.owner,json={'code':self.hardware['bindingCode'],'name':'团团'})
    def tearDown(self): self.client.close();self.tmp.cleanup()
    def auth(self,code):
        result=self.client.post('/v1/auth/wechat',json={'code':code})
        self.assertEqual(result.status_code,200,result.text)
        return {'Authorization':'Bearer '+result.json()['token']}
    def point(self,sequence=0,boot='boot'):
        return {'bootId':boot,'sequence':sequence,'capturedAt':time.time(),'latitude':31.2,
                'longitude':121.4,'coordinateSystem':'wgs84','battery':80}
    def test_ownership_and_secrets(self):
        self.assertEqual(self.client.get('/v1/devices/pet-one/snapshot',headers=self.other).status_code,404)
        listed=self.client.get('/v1/devices',headers=self.owner).json()
        self.assertEqual(listed,[{'id':'pet-one','name':'团团'}])
        self.assertNotIn('secret',str(listed))
        self.assertEqual(self.client.post('/v1/device/positions',headers=self.owner,json=self.point()).status_code,401)
    def test_binding_once_and_expired(self):
        self.assertEqual(self.client.post('/v1/devices/bind',headers=self.other,json={'code':self.hardware['bindingCode']}).status_code,400)
        with self.store.connection() as con: con.execute('UPDATE devices SET binding_expires=0 WHERE id=?',('pet-two',))
        self.assertEqual(self.client.post('/v1/devices/bind',headers=self.other,json={'code':self.other_hardware['bindingCode']}).status_code,400)
    def test_restart_duplicate_conflict_and_delayed_fix(self):
        point=self.point()
        self.assertEqual(self.client.post('/v1/device/positions',headers=self.device,json=point).status_code,201)
        self.assertTrue(self.client.post('/v1/device/positions',headers=self.device,json=point).json()['duplicate'])
        changed=dict(point,battery=70)
        self.assertEqual(self.client.post('/v1/device/positions',headers=self.device,json=changed).status_code,409)
        older=dict(self.point(0,'second'),capturedAt=point['capturedAt']-100)
        self.assertEqual(self.client.post('/v1/device/positions',headers=self.device,json=older).status_code,201)
        snapshot=self.client.get('/v1/devices/pet-one/snapshot',headers=self.owner).json()
        self.assertEqual(snapshot['latest']['bootId'],'boot')
        self.assertFalse(snapshot['online'])
    def test_mode_acknowledgement(self):
        response=self.client.post('/v1/devices/pet-one/mode',headers=self.owner,json={'mode':'finding'})
        self.assertEqual(response.json()['status'],'pending-device-ack')
        heartbeat={'battery':50,'fixValid':False,'appliedMode':'normal','firmware':'0.1'}
        result=self.client.post('/v1/device/heartbeat',headers=self.device,json=heartbeat)
        self.assertEqual(result.json()['desiredMode'],'finding')
        snapshot=self.client.get('/v1/devices/pet-one/snapshot',headers=self.owner).json()
        self.assertTrue(snapshot['online']); self.assertFalse(snapshot['fixValid'])
        self.assertEqual(snapshot['appliedMode'],'normal')
        heartbeat['appliedMode']='finding'
        self.client.post('/v1/device/heartbeat',headers=self.device,json=heartbeat)
        self.assertEqual(self.client.get('/v1/devices/pet-one/snapshot',headers=self.owner).json()['appliedMode'],'finding')
    def test_logout_and_expiration(self):
        self.assertEqual(self.client.post('/v1/auth/logout',headers=self.owner).status_code,204)
        self.assertEqual(self.client.get('/v1/devices',headers=self.owner).status_code,401)
        with self.store.connection() as con: con.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get('/v1/devices',headers=self.other).status_code,401)
    def test_invalid_payload_and_oversize(self):
        for key,value in [('sequence',True),('latitude',91),('capturedAt',time.time()+500),('coordinateSystem','bd09')]:
            point=self.point();point[key]=value
            self.assertEqual(self.client.post('/v1/device/positions',headers=self.device,json=point).status_code,422)
        self.assertEqual(self.client.post('/v1/auth/wechat',content='x'*9000).status_code,413)
    def test_track_range_and_isolation(self):
        now=time.time();point=self.point()
        self.client.post('/v1/device/positions',headers=self.device,json=point)
        path=f'/v1/devices/pet-one/track?start={now-100}&end={now+100}'
        self.assertEqual(len(self.client.get(path,headers=self.owner).json()['points']),1)
        self.assertEqual(self.client.get(path,headers=self.other).status_code,404)
        self.assertEqual(self.client.get('/v1/devices/pet-one/track?start=1&end=100000',headers=self.owner).status_code,400)
    def test_account_deletion(self):
        self.client.post('/v1/device/positions',headers=self.device,json=self.point())
        self.assertEqual(self.client.delete('/v1/account',headers=self.owner).status_code,204)
        self.assertEqual(self.client.get('/v1/devices',headers=self.owner).status_code,401)
        self.assertEqual(self.client.post('/v1/device/positions',headers=self.device,json=self.point()).status_code,401)
        with self.store.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM points').fetchone()[0],0)
            self.assertIsNone(con.execute('SELECT binding_digest FROM devices WHERE id=?',('pet-one',)).fetchone()[0])
    def test_login_failure_is_not_mocked(self):
        self.assertEqual(self.client.post('/v1/auth/wechat',json={'code':'bad'}).status_code,401)
        isolated=create_app(Path(self.tmp.name)/'unconfigured.sqlite3')
        with TestClient(isolated) as client:
            self.assertEqual(client.post('/v1/auth/wechat',json={'code':'anything'}).status_code,503)
    def test_unbound_device_does_not_collect_location(self):
        headers={'Authorization':'Bearer '+self.other_hardware['deviceToken']}
        self.assertEqual(self.client.post('/v1/device/positions',headers=headers,json=self.point()).status_code,409)
    def test_pagination_keeps_delayed_points(self):
        from server.production import Point
        now=time.time()
        for index in range(1001):
            self.store.insert('pet-one',Point(bootId='pagination',sequence=index,capturedAt=now-index,latitude=31.2,longitude=121.4))
        path=f'/v1/devices/pet-one/track?start={now-2000}&end={now+1}'
        first=self.client.get(path,headers=self.owner).json()
        self.assertEqual(len(first['points']),1000)
        self.assertIsNotNone(first['nextCursor'])
        second=self.client.get(path+'&after='+str(first['nextCursor']),headers=self.owner).json()
        self.assertEqual(len(second['points']),1)
        self.assertIsNone(second['nextCursor'])

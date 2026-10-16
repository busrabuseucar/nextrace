"""Real local HTTP requests against an isolated SQLite database."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import socket
        cls.temp = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.process = subprocess.Popen([sys.executable, 'backend/server.py', str(cls.port)], cwd=ROOT,
            env={**os.environ, 'NEXTRACE_DB_PATH': str(Path(cls.temp.name)/'http.db')}, stdout=subprocess.DEVNULL)
        for _ in range(100):
            try:
                cls.request('GET', '/api/health')
                break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('Server failed to start')
        status, body, headers = cls.request('POST', '/api/auth/setup', {'email':'admin@example.test','password':'ExamplePass123!'})
        assert status == 201, body
        cls.admin = headers['Set-Cookie'].split(';')[0]

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.temp.cleanup()

    @classmethod
    def request(cls, method, path, payload=None, cookie=None, extra=None):
        connection = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=5)
        headers = {'Content-Type':'application/json'}
        if cookie: headers['Cookie'] = cookie
        headers.update(extra or {})
        connection.request(method, path, json.dumps(payload) if payload is not None else None, headers)
        response = connection.getresponse()
        data = response.read()
        result = (response.status, json.loads(data) if data and response.getheader('Content-Type','').startswith('application/json') else data, dict(response.getheaders()))
        connection.close()
        return result

    def test_private_files_and_traversal_get_head(self):
        for method in ('GET', 'HEAD'):
            for path in ('/backend/server.py','/.env','/backend/data/nextrace.db','/assets/../backend/auth.py','/docs/%2e%2e/backend/storage.py'):
                with self.subTest(method=method,path=path):
                    self.assertEqual(self.request(method,path)[0],404)

    def test_unauthenticated_and_cross_origin(self):
        self.assertEqual(self.request('GET','/api/projects')[0],401)
        self.assertEqual(self.request('POST','/api/analyze',{},self.admin,{'Origin':'https://other.example'})[0],403)

    def test_analysis_version_is_persisted_and_invalid_csv_does_not_create_version(self):
        status, result, _ = self.request('POST','/api/analyze',{'changed_node_id':'SYS-REQ-142'},self.admin)
        self.assertEqual(status,200)
        self.assertEqual(result['impact_count'],8)
        self.assertEqual(result['path_count'],8)
        self.assertEqual(result['metadata_coverage'],100)
        self.assertTrue(result['created_at'])
        versions = self.request('GET','/api/projects/versions?project_id=demo',cookie=self.admin)[1]['versions']
        self.assertEqual(result['graph_version'],versions[0]['id'])
        status, result, _ = self.request('POST','/api/projects/import',{'project_id':'demo','nodes_csv':'id,label,type,owner,criticality\nX,short','edges_csv':'source,target,relation,reason'},self.admin)
        self.assertEqual(status,400)
        self.assertEqual(self.request('GET','/api/projects/versions?project_id=demo',cookie=self.admin)[1]['versions'],versions)

    def test_viewer_cannot_analyze_and_password_gate_is_enforced(self):
        _, user, _ = self.request('POST','/api/users',{'email':'viewer@example.test','password':'Temporary123!'},self.admin)
        _, _, headers = self.request('POST','/api/auth/login',{'email':'viewer@example.test','password':'Temporary123!'})
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('GET','/api/projects',cookie=cookie)[0],403)
        status, _, headers = self.request('POST','/api/auth/password',{'current_password':'Temporary123!','new_password':'Replacement123!'},cookie)
        self.assertEqual(status,200)
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('POST','/api/projects/access',{'project_id':'demo','user_id':user['user']['id'],'access_level':'viewer'},self.admin)[0],200)
        self.assertEqual(self.request('GET','/api/projects',cookie=cookie)[0],200)
        self.assertEqual(self.request('POST','/api/analyze',{'changed_node_id':'SYS-REQ-142'},cookie)[0],403)
        self.assertEqual(self.request('POST','/api/projects/import',{},cookie)[0],403)
        self.assertEqual(self.request('POST','/api/auth/logout',{},cookie)[0],200)
        self.assertEqual(self.request('GET','/api/projects',cookie=cookie)[0],401)

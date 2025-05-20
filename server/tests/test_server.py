# Server Test Example
# tests/test_server.py

import unittest
import json
from server.app import create_app
from server.app.config import Config

class TestConfig(Config):
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/test_db'

class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_health_endpoint(self):
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'ok')

    def test_info_endpoint(self):
        response = self.client.get('/api/info')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', data)
        self.assertIn('version', data)
        self.assertIn('features', data)

if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sqlite3
import os
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

DB_PATH = os.path.join(os.path.dirname(__file__), 'hawaa_data.db')
connections = {}

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.close()

class HawaaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "alive"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}
        except:
            data = {}

        path = self.path
        if path == '/connect':
            conn_id = str(uuid.uuid4())
            conn = sqlite3.connect(DB_PATH, isolation_level=None)
            conn.row_factory = sqlite3.Row
            connections[conn_id] = conn
            self._send_json({"connection_id": conn_id})

        elif path == '/disconnect':
            conn_id = data.get('conn_id') or self._get_param('conn_id')
            if conn_id in connections:
                connections[conn_id].close()
                del connections[conn_id]
            self._send_json({"status": "ok"})

        elif path == '/execute':
            conn_id = data.get('connection_id')
            sql = data.get('sql')
            params = data.get('params', [])
            if conn_id not in connections:
                self._send_error("Connection not found", 404)
                return
            conn = connections[conn_id]
            try:
                cursor = conn.execute(sql, params)
                rows = None
                if sql.strip().upper().startswith("SELECT"):
                    rows = [dict(row) for row in cursor.fetchall()]
                self._send_json({
                    "success": True,
                    "rows": rows,
                    "rowcount": cursor.rowcount,
                    "lastrowid": cursor.lastrowid
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})

        elif path == '/commit':
            conn_id = data.get('conn_id') or self._get_param('conn_id')
            if conn_id in connections:
                connections[conn_id].commit()
            self._send_json({"status": "ok"})

        elif path == '/rollback':
            conn_id = data.get('conn_id') or self._get_param('conn_id')
            if conn_id in connections:
                connections[conn_id].rollback()
            self._send_json({"status": "ok"})

        else:
            self.send_response(404)
            self.end_headers()

    def _get_param(self, key):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        return params.get(key, [None])[0]

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, msg, code=500):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def log_message(self, format, *args):
        pass

def create_server():
    init_db()
    server = HTTPServer(('0.0.0.0', 8000), HawaaHandler)
    return server

if __name__ == '__main__':
    server = create_server()
    print("✅ خادم Hawaa يعمل على http://0.0.0.0:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 إيقاف الخادم...")
        server.shutdown()

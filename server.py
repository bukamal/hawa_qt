# -*- coding: utf-8 -*-
import sqlite3
import os
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import uvicorn

app = FastAPI(title="Hawaa SQLite Server")

connections: Dict[str, sqlite3.Connection] = {}

class ExecuteRequest(BaseModel):
    connection_id: str
    sql: str
    params: List[Any] = []

class ExecuteResponse(BaseModel):
    success: bool
    rows: Optional[List[Dict]] = None
    rowcount: Optional[int] = None
    lastrowid: Optional[int] = None
    error: Optional[str] = None

@app.post("/connect")
def connect():
    conn_id = str(uuid.uuid4())
    db_path = os.path.join(os.path.dirname(__file__), 'hawaa_data.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    connections[conn_id] = conn
    return {"connection_id": conn_id}

@app.post("/disconnect")
def disconnect(conn_id: str):
    if conn_id in connections:
        connections[conn_id].close()
        del connections[conn_id]
    return {"status": "ok"}

@app.post("/execute", response_model=ExecuteResponse)
def execute(req: ExecuteRequest):
    if req.connection_id not in connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn = connections[req.connection_id]
    try:
        cursor = conn.execute(req.sql, req.params)
        rows = None
        if req.sql.strip().upper().startswith("SELECT"):
            rows = [dict(row) for row in cursor.fetchall()]
        return ExecuteResponse(
            success=True,
            rows=rows,
            rowcount=cursor.rowcount,
            lastrowid=cursor.lastrowid
        )
    except Exception as e:
        return ExecuteResponse(success=False, error=str(e))

@app.post("/commit")
def commit(conn_id: str):
    if conn_id not in connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    connections[conn_id].commit()
    return {"status": "ok"}

@app.post("/rollback")
def rollback(conn_id: str):
    if conn_id not in connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    connections[conn_id].rollback()
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "alive"}

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

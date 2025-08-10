from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import logging
import subprocess
import os
import time
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class Peer(BaseModel):
    host: str
    port: int

class FileInfo(BaseModel):
    file_name: str
    chunk_count: int
    peer: Peer

class FileListEntry(BaseModel):
    file_name: str
    chunk_count: int
    peers: List[Peer]

class ChunkUpdate(BaseModel):
    file_name: str
    chunk_id: int
    peer: Peer

# In-memory storage
peers: List[Peer] = []
files: Dict[str, Dict[int, List[Peer]]] = {}  # file_name -> {chunk_id: [peers]}

# Store running processes
running_processes: Dict[int, subprocess.Popen] = {}

@app.post("/register")
async def register_peer(peer: Peer):
    for existing_peer in peers:
        if existing_peer.host == peer.host and existing_peer.port == peer.port:
            logger.info(f"Peer {peer.host}:{peer.port} already registered")
            return {"message": f"Peer {peer.host}:{peer.port} already registered"}
    
    try:
        launch_process = subprocess.Popen([sys.executable, "launch.py", str(peer.port)])
        time.sleep(2)
        running_processes[peer.port] = launch_process
        
        peers.append(peer)
        logger.info(f"Registered new peer: {peer.host}:{peer.port} with HTTP on {peer.port + 1}")
        return {"message": f"Peer {peer.host}:{peer.port} registered with HTTP server on {peer.port + 1}"}
    except Exception as e:
        logger.error(f"Failed to start processes for peer {peer.host}:{peer.port}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start peer processes: {str(e)}")

@app.get("/peers")
async def get_peers():
    return peers

@app.post("/announce_file")
async def announce_file(file_info: FileInfo):
    try:
        if file_info.file_name not in files:
            files[file_info.file_name] = {}
        for i in range(file_info.chunk_count):
            if i not in files[file_info.file_name]:
                files[file_info.file_name][i] = []
            if file_info.peer not in files[file_info.file_name][i]:
                files[file_info.file_name][i].append(file_info.peer)
        logger.info(f"Announced file {file_info.file_name} with {file_info.chunk_count} chunks on peer {file_info.peer.port}")
        return {"message": f"File {file_info.file_name} announced with {file_info.chunk_count} chunks"}
    except Exception as e:
        logger.error(f"Error announcing file: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid file info: {str(e)}")

@app.post("/update_chunk")
async def update_chunk(chunk_update: ChunkUpdate):
    try:
        file_name = chunk_update.file_name
        chunk_id = chunk_update.chunk_id
        peer = chunk_update.peer
        if file_name not in files:
            files[file_name] = {}
        if chunk_id not in files[file_name]:
            files[file_name][chunk_id] = []
        if peer not in files[file_name][chunk_id]:
            files[file_name][chunk_id].append(peer)
        logger.info(f"Updated chunk {chunk_id} of {file_name} on peer {peer.port}")
        return {"message": f"Chunk {chunk_id} of {file_name} updated on peer {peer.port}"}
    except Exception as e:
        logger.error(f"Error updating chunk: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid chunk update: {str(e)}")

@app.get("/get_file/{file_name}")
async def get_file(file_name: str):
    if file_name not in files:
        return {"error": "File not found"}
    return {file_name: files[file_name]}

@app.get("/list_files")
async def list_files():
    file_list = []
    for file_name, chunks in files.items():
        unique_peers = set()
        for peer_list in chunks.values():
            for peer in peer_list:
                unique_peers.add(f"{peer.host}:{peer.port}")
        file_list.append(FileListEntry(
            file_name=file_name,
            chunk_count=len(chunks),
            peers=[Peer(host=p.split(":")[0], port=int(p.split(":")[1])) for p in unique_peers]
        ))
    return file_list

@app.get("/health")
async def health_check():
    return {"status": "healthy", "peers": len(peers), "files": len(files)}

@app.post("/shutdown/{port}")
async def shutdown_peer(port: int):
    if port in running_processes:
        running_processes[port].terminate()
        running_processes[port].wait()
        del running_processes[port]
        peers[:] = [p for p in peers if p.port != port]
        logger.info(f"Shutdown peer processes on port {port}")
        return {"message": f"Shutdown peer on port {port} successfully"}
    raise HTTPException(status_code=404, detail=f"No peer running on port {port}")

if __name__ == "__main__":
    logger.info("Starting central server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
from typing import Dict
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory chunk storage
chunks: Dict[str, Dict[int, bytes]] = {}

app = FastAPI()

# Enable CORS for all origins (safer for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/chunk/{file_name}/{chunk_id}")
async def serve_chunk(file_name: str, chunk_id: int):
    if file_name in chunks and chunk_id in chunks[file_name]:
        # Return the binary data directly
        return Response(content=chunks[file_name][chunk_id], media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail="Chunk not found")

@app.post("/upload_chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    file_name: str = Form(...), 
    chunk_id: str = Form(...)
):
    try:
        chunk_data = await chunk.read()
        chunk_id_int = int(chunk_id)  # Convert chunk_id to int
        
        if not file_name or not chunk_data:
            raise HTTPException(status_code=400, detail="Missing file_name or chunk data")
        
        if file_name not in chunks:
            chunks[file_name] = {}
        
        chunks[file_name][chunk_id_int] = chunk_data
        logger.info(f"Stored chunk {chunk_id_int} for {file_name} ({len(chunk_data)} bytes)")
        
        return {"message": f"Chunk {chunk_id_int} uploaded for {file_name}", "size": len(chunk_data)}
    
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid chunk_id: must be an integer")
    except Exception as e:
        logger.error(f"Error processing chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    logger.info(f"Starting HTTP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
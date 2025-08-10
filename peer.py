import asyncio
import logging
from aioquic.asyncio import QuicConnectionProtocol, QuicListener
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived
import os
import json
import certifi
import ssl
from typing import Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PeerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, peer_port: int, central_server: str = "localhost:8000", **kwargs):
        super().__init__(*args, **kwargs)
        self.peer_port = peer_port
        self.chunks: Dict[str, Dict[int, bytes]] = {}  # file_name -> {chunk_id: chunk_data}
        self.central_server = central_server

    async def handle_stream(self, stream_id: int) -> None:
        while True:
            event = await self._wait_stream_event(stream_id)
            if not isinstance(event, StreamDataReceived):
                break
            data = event.data.decode()
            try:
                message = json.loads(data)
                if message.get("command") == "GET_CHUNK":
                    file_name = message["file_name"]
                    chunk_id = message["chunk_id"]
                    if file_name in self.chunks and chunk_id in self.chunks[file_name]:
                        chunk = self.chunks[file_name][chunk_id]
                        await self.send_stream_data(stream_id, json.dumps({"status": "OK", "chunk": chunk.hex()}).encode())
                    else:
                        await self.send_stream_data(stream_id, json.dumps({"status": "ERROR", "message": "Chunk not found"}).encode())
                elif message.get("command") == "STORE_CHUNK":
                    file_name = message["file_name"]
                    chunk_id = message["chunk_id"]
                    chunk_data = bytes.fromhex(message["chunk"])
                    if file_name not in self.chunks:
                        self.chunks[file_name] = {}
                    self.chunks[file_name][chunk_id] = chunk_data
                    logger.info(f"Stored chunk {chunk_id} of {file_name} on peer {self.peer_port}")
                    await self.send_stream_data(stream_id, json.dumps({"status": "OK"}).encode())
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received on peer {self.peer_port}")
                await self.send_stream_data(stream_id, json.dumps({"status": "ERROR", "message": "Invalid request"}).encode())

    async def send_stream_data(self, stream_id: int, data: bytes) -> None:
        self._quic.send_stream_data(stream_id, data)
        await self._quic.next_event()

async def main(peer_port: int):
    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=["p2p-file-transfer"],
        certificate=os.path.join("certs", "cert.pem"),
        private_key=os.path.join("certs", "key.pem"),
    )
    configuration.load_verify_locations(certifi.where())

    listener = await QuicListener.create(
        host="0.0.0.0",
        port=peer_port,
        configuration=configuration,
        create_protocol=lambda *args, **kwargs: PeerProtocol(*args, peer_port=peer_port, **kwargs)
    )
    logger.info(f"Peer listening on {listener.host}:{peer_port}")
    async with listener:
        await listener.serve_forever()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python peer.py <port>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1])))
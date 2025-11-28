"""
Cluster Mesh Router
===================

A unified RPC router for the entire cluster.
All subsystems communicate through this file.

Handles:
- Gossip messages
- RAFT replication
- Distributed Storage KV/Object calls
- Event Bus forwarding
- Task Queue commands
- WASM/VM/JIT execution calls
- Execution Graph node RPCs
- Debugger hooks
- Distributed Orchestrator calls
"""

import asyncio
import json
from typing import Dict, Any, Callable, Awaitable


class MeshRouter:
    """
    Central event-driven RPC router.
    """

    def __init__(self, port: int):
        self.port = port

        # Dynamic command table
        self.handlers: Dict[str, Callable[[dict], Awaitable[Any]]] = {}

        # Start async listener
        asyncio.create_task(self._server_loop())

    # ---------------------------------------------------------
    # REGISTER HANDLER
    # ---------------------------------------------------------

    def register(self, cmd: str, handler: Callable[[dict], Awaitable[Any]]):
        """
        Register an async handler for a command.
        """
        self.handlers[cmd] = handler

    # ---------------------------------------------------------
    # SEND MESSAGE
    # ---------------------------------------------------------

    async def send(self, port: int, payload: dict) -> Any:
        """
        Simple RPC call:
            await router.send(port, {"cmd": "...", ... })
        """
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(json.dumps(payload).encode())
            await writer.drain()
            data = await reader.read(65536)
            writer.close()

            if not data:
                return None

            return json.loads(data.decode())
        except:
            return None

    # ---------------------------------------------------------
    # SERVER LOOP
    # ---------------------------------------------------------

    async def _server_loop(self):
        server = await asyncio.start_server(self._handle_conn, "0.0.0.0", self.port)
        async with server:
            await server.serve_forever()

    # ---------------------------------------------------------
    # HANDLE INCOMING CONNECTIONS
    # ---------------------------------------------------------

    async def _handle_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            raw = await reader.read(65536)
            if not raw:
                writer.close()
                return

            msg = json.loads(raw.decode())
            cmd = msg.get("cmd")

            handler = self.handlers.get(cmd)
            if not handler:
                writer.write(json.dumps({"error": f"Unknown cmd {cmd}"}).encode())
                await writer.drain()
                writer.close()
                return

            result = await handler(msg)
            writer.write(json.dumps(result).encode())
            await writer.drain()

        except Exception as e:
            writer.write(json.dumps({"error": str(e)}).encode())
            await writer.drain()
        finally:
            writer.close()


# ============================================================
# FACTORY
# ============================================================

def create_mesh_router(port: int) -> MeshRouter:
    return MeshRouter(port)

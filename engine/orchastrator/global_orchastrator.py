"""
Global Orchestrator Integration Layer
=====================================

This is the central integration component of the entire engine.
It wires together:

- Gossip (membership)
- RAFT (consensus + strong writes)
- Distributed Storage (KV + Object Store)
- Manifest DB (versioned metadata)
- Distributed Task Queue
- Event Bus (pub/sub)
- Workflow State Engine
- Execution Graph Engine (DAG runtime)
- Fiber Scheduler (local concurrency)
- VM/WASM/JIT backend interfaces
- Cluster-RPC message router

This file creates ONE ORCHESTRATOR INSTANCE per node.

Other components talk through this orchestrator.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable

from engine.cluster.gossip import GossipEngine
from engine.cluster.raft import RaftEngine
from engine.cluster.distributed_storage import create_distributed_storage
from engine.cluster.manifest_db import create_manifest_db
from engine.cluster.task_queue import create_task_queue
from engine.cluster.event_bus import create_event_bus
from engine.cluster.workflow_state import create_workflow_state_api
from engine.cluster.execution_graph import create_execution_graph_engine

from engine.scheduler.fibers import scheduler


# ============================================================
# ORCHESTRATOR
# ============================================================

class GlobalOrchestrator:

    def __init__(self, cfg: dict):
        self.cfg = cfg

        port = cfg["port"]
        peers = cfg.get("peers", [])

        # ------------------------------
        # Start Gossip Engine (membership)
        # ------------------------------
        self.gossip = GossipEngine(port=port, known_peers=peers)

        # ------------------------------
        # Start RAFT (consensus)
        # ------------------------------
        self.raft = RaftEngine(port=port, peers=peers)

        # ------------------------------
        # Distributed Storage Layer
        # ------------------------------
        self.storage = create_distributed_storage(self.raft, self.gossip)

        # ------------------------------
        # Manifest Database
        # ------------------------------
        self.manifest_db = create_manifest_db(self.storage)

        # ------------------------------
        # Distributed Task Queue
        # ------------------------------
        self.task_queue = create_task_queue(self.raft, self.gossip)

        # ------------------------------
        # Event Bus (cluster-wide pub/sub)
        # ------------------------------
        self.event_bus = create_event_bus(self.raft, self.gossip, self.storage)

        # ------------------------------
        # Workflow State Engine
        # ------------------------------
        self.workflow_state = create_workflow_state_api(self.raft, self.gossip)

        # ------------------------------
        # Execution Graph Engine (DAG runtime)
        # ------------------------------
        self.exec_engine = create_execution_graph_engine(self.task_queue.dist_api)

        # ------------------------------
        # Register Protocol Handlers (RPC)
        # ------------------------------
        asyncio.create_task(self._run_rpc_listener())

        print(f"[ORCHESTRATOR] Node running on port {port}")

    # ---------------------------------------------------------
    # RPC Listener (compact universal protocol)
    # ---------------------------------------------------------

    async def _run_rpc_listener(self):
        server = await asyncio.start_server(self._handle_rpc, "0.0.0.0", self.cfg["port"])
        async with server:
            await server.serve_forever()

    async def _handle_rpc(self, reader, writer):
        try:
            raw = await reader.read(65536)
            msg = json.loads(raw.decode())
            cmd = msg.get("cmd")

            # ----------------------------------------
            # Distributed Storage RPC
            # ----------------------------------------
            if cmd == "kv_get":
                key = msg["key"]
                val = self.storage.shard.kv_read(key)
                writer.write(json.dumps({"value": val}).encode())

            elif cmd == "object_put":
                key = msg["key"]
                data = bytes(msg["data"])
                self.storage.shard.obj_write(key, data)
                writer.write(b"OK")

            elif cmd == "object_get":
                key = msg["key"]
                data = self.storage.shard.obj_read(key)
                writer.write(json.dumps({"data": list(data or b"")}).encode())

            # ----------------------------------------
            # Event Bus Forwarding
            # ----------------------------------------
            elif cmd == "event_forward":
                await self.event_bus.handle_forwarded_event(msg["event"])
                writer.write(b"OK")

            # ----------------------------------------
            # RAFT Internal Commands
            # ----------------------------------------
            elif cmd == "raft_append":
                ok = await self.raft.handle_append_entries(msg)
                writer.write(json.dumps({"ok": ok}).encode())

            elif cmd == "raft_request_vote":
                ok = await self.raft.handle_vote_request(msg)
                writer.write(json.dumps({"ok": ok}).encode())

            # ----------------------------------------
            # Task Queue Commands
            # ----------------------------------------
            elif cmd == "task_submit":
                fut = await self.task_queue.submit_task(msg["payload"])
                writer.write(json.dumps({"task_id": fut.task_id}).encode())

            # ----------------------------------------
            # WASM/VM/JIT Execution Hooks
            # (This will be expanded by Phase 4 & 5)
            # ----------------------------------------
            elif cmd == "execute_vm":
                out = await self._execute_vm(msg["code"])
                writer.write(json.dumps({"result": out}).encode())

            elif cmd == "execute_wasm":
                out = await self._execute_wasm(msg["module"])
                writer.write(json.dumps({"result": out}).encode())

            elif cmd == "execute_jit":
                out = await self._execute_jit(msg["ir"])
                writer.write(json.dumps({"result": out}).encode())


        except Exception as e:
            print("[ORCHESTRATOR RPC ERROR]", e)
        finally:
            await writer.drain()
            writer.close()

    # ---------------------------------------------------------
    # VM/WASM/JIT hooks (stubs for later phases)
    # ---------------------------------------------------------

    async def _execute_vm(self, code: str) -> Any:
        print("[VM] Executing VM code (stub)")
        return {"ok": True, "output": "<vm-out>"}

    async def _execute_wasm(self, wasm_bytes: bytes) -> Any:
        print("[WASM] Executing WASM module (stub)")
        return {"ok": True, "output": "<wasm-out>"}

    async def _execute_jit(self, ir: dict) -> Any:
        print("[JIT] Running JIT IR (stub)")
        return {"ok": True, "output": "<jit-out>"}


# ============================================================
# FACTORY
# ============================================================

def create_orchestrator(cfg: dict) -> GlobalOrchestrator:
    return GlobalOrchestrator(cfg)

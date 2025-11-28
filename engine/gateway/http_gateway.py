"""
Distributed HTTP Gateway
========================

Provides:
- REST API for entire cluster
- WebSocket streaming for events, logs, debugger
- Task + Workflow submission API
- Manifest DB API
- Distributed storage API
- WASM/JIT/VM execution endpoints
- Cluster info endpoints

Based on aiohttp for universal compatibility.
"""

import json
import asyncio
from aiohttp import web
from typing import Dict, Any

from engine.cluster.mesh_router import MeshRouter


# ============================================================
# HELPER: RPC Wrapper
# ============================================================

async def rpc(router: MeshRouter, port: int, payload: dict):
    return await router.send(port, payload)


# ============================================================
# HTTP GATEWAY
# ============================================================

class HTTPGateway:

    def __init__(self, router: MeshRouter, port: int, target_port: int):
        """
        router: MeshRouter for RPC
        port:   HTTP port for gateway
        target_port: orchestrator node to talk to
        """
        self.router = router
        self.port = port
        self.target = target_port
        self.app = web.Application()

        # Register Routes
        self._register_routes()

    # ---------------------------------------------------------
    # ROUTES
    # ---------------------------------------------------------

    def _register_routes(self):
        # Cluster
        self.app.router.add_get("/cluster/info", self.route_cluster_info)
        self.app.router.add_get("/cluster/members", self.route_cluster_members)
        self.app.router.add_get("/raft/status", self.route_raft_status)

        # Tasks
        self.app.router.add_post("/task/submit", self.route_submit_task)

        # Workflows
        self.app.router.add_post("/workflow/submit", self.route_submit_workflow)

        # Storage (KV)
        self.app.router.add_get("/kv/{key}", self.route_kv_get)
        self.app.router.add_post("/kv/{key}", self.route_kv_put)

        # Manifest DB
        self.app.router.add_get("/manifest/{key}", self.route_manifest_get)
        self.app.router.add_post("/manifest/{key}", self.route_manifest_set)

        # Debugger
        self.app.router.add_get("/debug/state", self.route_debug_state)
        self.app.router.add_post("/debug/pause", self.route_debug_pause)
        self.app.router.add_post("/debug/resume", self.route_debug_resume)
        self.app.router.add_post("/debug/eval", self.route_debug_eval)

        # Execution Endpoints
        self.app.router.add_post("/execute/vm", self.route_execute_vm)
        self.app.router.add_post("/execute/wasm", self.route_execute_wasm)
        self.app.router.add_post("/execute/jit", self.route_execute_jit)

        # WebSocket Streams
        self.app.router.add_get("/ws/events", self.route_stream_events)

    # ---------------------------------------------------------
    # ROUTE HANDLERS
    # ---------------------------------------------------------

    async def route_cluster_info(self, request):
        resp = await rpc(self.router, self.target, {"cmd": "cluster.info"})
        return web.json_response(resp)

    async def route_cluster_members(self, request):
        resp = await rpc(self.router, self.target, {"cmd": "gossip.members"})
        return web.json_response(resp)

    async def route_raft_status(self, request):
        resp = await rpc(self.router, self.target, {"cmd": "raft.status"})
        return web.json_response(resp)

    # Tasks
    async def route_submit_task(self, request):
        body = await request.json()
        job = body.get("job")
        resp = await rpc(self.router, self.target, {
            "cmd": "task_submit",
            "payload": {"job": job}
        })
        return web.json_response(resp)

    # Workflows
    async def route_submit_workflow(self, request):
        dag = await request.json()
        resp = await rpc(self.router, self.target, {
            "cmd": "workflow.submit",
            "dag": dag
        })
        return web.json_response(resp)

    # KV storage
    async def route_kv_get(self, request):
        key = request.match_info["key"]
        resp = await rpc(self.router, self.target, {"cmd": "kv_get", "key": key})
        return web.json_response(resp)

    async def route_kv_put(self, request):
        key = request.match_info["key"]
        data = await request.json()
        resp = await rpc(self.router, self.target, {"cmd": "kv_put", "key": key, "value": data})
        return web.json_response(resp)

    # Manifest DB
    async def route_manifest_get(self, request):
        key = request.match_info["key"]
        resp = await rpc(self.router, self.target, {"cmd": "manifest.get", "key": key})
        return web.json_response(resp)

    async def route_manifest_set(self, request):
        key = request.match_info["key"]
        data = await request.json()
        resp = await rpc(self.router, self.target, {
            "cmd": "manifest.set",
            "key": key,
            "data": data
        })
        return web.json_response(resp)

    # Debugger
    async def route_debug_state(self, request):
        resp = await rpc(self.router, self.target, {"cmd": "dbg.state"})
        return web.json_response(resp)

    async def route_debug_pause(self, request):
        await rpc(self.router, self.target, {"cmd": "dbg.pause"})
        return web.json_response({"ok": True})

    async def route_debug_resume(self, request):
        await rpc(self.router, self.target, {"cmd": "dbg.resume"})
        return web.json_response({"ok": True})

    async def route_debug_eval(self, request):
        body = await request.json()
        expr = body.get("expr")
        resp = await rpc(self.router, self.target, {"cmd": "dbg.eval", "expr": expr})
        return web.json_response(resp)

    # Execution Endpoints
    async def route_execute_vm(self, request):
        body = await request.json()
        code = body.get("code")
        resp = await rpc(self.router, self.target, {"cmd": "execute_vm", "code": code})
        return web.json_response(resp)

    async def route_execute_wasm(self, request):
        data = await request.read()
        wasm_bytes = list(data)
        resp = await rpc(self.router, self.target, {"cmd": "execute_wasm", "module": wasm_bytes})
        return web.json_response(resp)

    async def route_execute_jit(self, request):
        body = await request.json()
        resp = await rpc(self.router, self.target, {"cmd": "execute_jit", "ir": body})
        return web.json_response(resp)

    # WebSocket Event Stream
    async def route_stream_events(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        await ws.send_str("CONNECTED TO EVENT STREAM")

        while True:
            events = await rpc(self.router, self.target, {"cmd": "get_event_sample"})
            if events:
                for e in events.get("events", []):
                    ws.send_str(json.dumps(e))
            await asyncio.sleep(1)

    # ---------------------------------------------------------
    # START SERVER
    # ---------------------------------------------------------

    def start(self):
        web.run_app(self.app, port=self.port)

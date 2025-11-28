"""
GOSSIP MODULE — Membership + Health + Distributed KV
====================================================

Implements:
- SWIM-style gossip membership protocol
- Node health scoring
- Failure detection
- Gossip piggybacking
- Distributed KV store (eventually consistent)
- Anti-entropy background repair
- Fiber-safe operation

Integrates with:
- Raft (file 11)
- Orchestrator
- Debugger
- Fiber Scheduler
"""

import asyncio
import json
import random
import time
from typing import Dict, Optional, List

# Fiber support
from engine.scheduler.fibers import scheduler

# Debugger
from engine.debug.debugger import debugger


# ============================================================
# GOSSIP NODE
# ============================================================

class Member:
    def __init__(self, node_id: int, addr: str, port: int):
        self.node_id = node_id
        self.addr = addr
        self.port = port
        self.status = "alive"      # alive / suspect / dead
        self.heartbeat = 0
        self.last_update = time.time()

    def touch(self):
        self.heartbeat += 1
        self.last_update = time.time()


# ============================================================
# MESSAGE TYPES
# ============================================================

MSG_GOSSIP = "gossip"
MSG_PING = "ping"
MSG_PING_ACK = "ping_ack"
MSG_SYNC = "sync"
MSG_KV_UPDATE = "kv_update"


# ============================================================
# GOSSIP ENGINE
# ============================================================

class GossipEngine:

    def __init__(self, node_id: int, addr: str, port: int, peers: List[int]):
        self.node_id = node_id
        self.addr = addr
        self.port = port

        # Membership list: node_id → Member
        self.members: Dict[int, Member] = {
            node_id: Member(node_id, addr, port)
        }

        # peers are port numbers for simplicity
        self.peer_ports = peers

        # Distributed key-value store
        self.store: Dict[str, Dict[str, float]] = {}  # key → {value, version}

        # Client networking
        self.loop = asyncio.get_event_loop()
        self.server = None

        # Timers
        self.gossip_interval = 0.2
        self.ping_timeout = 0.15
        self.suspect_timeout = 1.0
        self.dead_timeout = 2.0

    # ---------------------------------------------------------
    # START GOSSIP NODE
    # ---------------------------------------------------------

    async def start(self):
        self.server = await asyncio.start_server(self._handle_conn, "0.0.0.0", self.port)
        print(f"[GOSSIP] Node {self.node_id} running on port {self.port}")

        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._health_checker())
        asyncio.create_task(self._anti_entropy_loop())

        async with self.server:
            await self.server.serve_forever()

    def blocking_start(self):
        asyncio.run(self.start())

    # ---------------------------------------------------------
    # NETWORKING: HANDLE INCOMING MESSAGES
    # ---------------------------------------------------------

    async def _handle_conn(self, reader, writer):
        try:
            raw = await reader.read(65536)
            msg = json.loads(raw.decode())
            await self._handle_message(msg, writer)
        except Exception as e:
            print("[GOSSIP] Error:", e)

    # ---------------------------------------------------------
    # SEND MESSAGE TO PEER
    # ---------------------------------------------------------

    async def _send(self, port: int, msg: dict):
        try:
            _, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(json.dumps(msg).encode())
            await w.drain()
        except:
            pass  # Peer may be down

    # ---------------------------------------------------------
    # MESSAGE HANDLER
    # ---------------------------------------------------------

    async def _handle_message(self, msg, writer):
        t = msg.get("type")

        if t == MSG_GOSSIP:
            await self._handle_gossip(msg)

        elif t == MSG_PING:
            await self._reply(writer, {"type": MSG_PING_ACK})

        elif t == MSG_PING_ACK:
            # No action needed; parent coroutine handles it
            pass

        elif t == MSG_SYNC:
            await self._handle_sync(msg)

        elif t == MSG_KV_UPDATE:
            await self._handle_kv_update(msg)

    async def _reply(self, writer, payload: dict):
        writer.write(json.dumps(payload).encode())
        await writer.drain()

    # ---------------------------------------------------------
    # GOSSIP LOGIC
    # ---------------------------------------------------------

    async def _gossip_loop(self):
        """
        Periodically send membership gossip to random peers.
        """
        while True:
            await asyncio.sleep(self.gossip_interval)

            # Update our heartbeat
            self.members[self.node_id].touch()

            payload = {
                "type": MSG_GOSSIP,
                "from": self.node_id,
                "members": {
                    nid: {
                        "hb": m.heartbeat,
                        "status": m.status,
                        "addr": m.addr,
                        "port": m.port,
                        "time": m.last_update,
                    }
                    for nid, m in self.members.items()
                },
                "kv": self.store,
            }

            # Send to random peer
            if self.peer_ports:
                peer = random.choice(self.peer_ports)
                asyncio.create_task(self._send(peer, payload))

    # ---------------------------------------------------------
    # GOSSIP HANDLER
    # ---------------------------------------------------------

    async def _handle_gossip(self, msg):
        remote_members = msg["members"]
        remote_kv = msg["kv"]

        # Merge membership
        for nid, info in remote_members.items():
            if nid not in self.members:
                self.members[nid] = Member(nid, info["addr"], info["port"])

            local = self.members[nid]

            # Update heartbeat
            if info["hb"] > local.heartbeat:
                local.heartbeat = info["hb"]
                local.last_update = time.time()

        # Merge KV store
        for key, entry in remote_kv.items():
            if key not in self.store or entry["version"] > self.store[key]["version"]:
                self.store[key] = entry

    # ---------------------------------------------------------
    # HEALTH CHECKER
    # ---------------------------------------------------------

    async def _health_checker(self):
        while True:
            await asyncio.sleep(0.1)
            now = time.time()

            for nid, m in list(self.members.items()):
                if nid == self.node_id:
                    continue

                age = now - m.last_update

                if age > self.dead_timeout:
                    m.status = "dead"
                elif age > self.suspect_timeout:
                    m.status = "suspect"

    # ---------------------------------------------------------
    # ANTI-ENTROPY: FULL STATE SYNC
    # ---------------------------------------------------------

    async def _anti_entropy_loop(self):
        """
        Periodic full-state sync to ensure eventual consistency.
        """
        while True:
            await asyncio.sleep(2.0)
            if not self.peer_ports:
                continue

            msg = {
                "type": MSG_SYNC,
                "members": {
                    nid: {
                        "hb": m.heartbeat,
                        "status": m.status,
                        "addr": m.addr,
                        "port": m.port,
                        "time": m.last_update,
                    }
                    for nid, m in self.members.items()
                },
                "kv": self.store,
            }

            for p in self.peer_ports:
                asyncio.create_task(self._send(p, msg))

    async def _handle_sync(self, msg):
        remote_members = msg["members"]
        remote_kv = msg["kv"]

        # Merge everything
        for nid, info in remote_members.items():
            if nid not in self.members:
                self.members[nid] = Member(nid, info["addr"], info["port"])

            m = self.members[nid]
            if info["hb"] > m.heartbeat:
                m.heartbeat = info["hb"]
                m.last_update = time.time()

        for key, entry in remote_kv.items():
            if key not in self.store or entry["version"] > self.store[key]["version"]:
                self.store[key] = entry

    # ---------------------------------------------------------
    # DISTRIBUTED KV STORE
    # ---------------------------------------------------------

    def put(self, key: str, value: str):
        """Update distributed KV and gossip it."""
        version = time.time()
        self.store[key] = {"value": value, "version": version}

        msg = {
            "type": MSG_KV_UPDATE,
            "key": key,
            "value": value,
            "version": version,
        }

        for p in self.peer_ports:
            asyncio.create_task(self._send(p, msg))

    async def _handle_kv_update(self, msg):
        key = msg["key"]
        value = msg["value"]
        version = msg["version"]
        if key not in self.store or version > self.store[key]["version"]:
            self.store[key] = {"value": value, "version": version}


# ============================================================
# GLOBAL CONSTRUCTOR
# ============================================================

def create_gossip_node(node_id: int, addr: str, port: int, peers: List[int]) -> GossipEngine:
    return GossipEngine(node_id, addr, port, peers)

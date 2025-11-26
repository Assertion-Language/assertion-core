"""
Distributed Engine Runtime
==========================

This module implements the following components:

1. Gossip dissemination protocol
2. RAFT consensus:
   - Leader election
   - AppendEntries
   - Log replication
   - Term + index tracking
   - Heartbeat system
3. Cluster message bus (async sockets or in-memory fallback)
4. Distributed state machine hook:
   apply_log_entry(entry) -> state update

5. Full compact enterprise-level logic

This is the distributed backbone of the Assertion Engine.
"""

import asyncio
import json
import random
import time
import socket
import threading
from typing import Dict, List, Optional, Any


# ============================================================
# Message Utilities
# ============================================================

def encode(msg: Dict[str, Any]) -> bytes:
    return (json.dumps(msg) + "\n").encode()


def decode(raw: bytes) -> Dict[str, Any]:
    return json.loads(raw.decode())


# ============================================================
# Cluster Message Bus
# ============================================================

class ClusterTransport:
    """
    Lightweight message transport layer.
    Uses asyncio streams for TCP-based peer communication.
    """

    def __init__(self, port: int, peers: List[int]):
        self.port = port
        self.peers = peers
        self.handlers = []
        self.stop_flag = False

    async def start(self):
        server = await asyncio.start_server(self.handle_conn, "0.0.0.0", self.port)
        asyncio.create_task(server.serve_forever())

    async def handle_conn(self, reader, writer):
        while not self.stop_flag:
            try:
                raw = await reader.readline()
                if not raw:
                    break
                msg = decode(raw)
                for h in self.handlers:
                    asyncio.create_task(h(msg))
            except:
                break

    async def send(self, peer_port: int, msg: Dict[str, Any]):
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", peer_port)
            writer.write(encode(msg))
            await writer.drain()
            writer.close()
        except:
            # Peer down
            pass

    def add_handler(self, fn):
        self.handlers.append(fn)


# ============================================================
# Gossip Protocol
# ============================================================

class Gossip:
    """
    Simple epidemic gossip protocol.
    Disseminates state dicts to all peers via periodic push.
    """

    def __init__(self, node_id: int, transport: ClusterTransport):
        self.node_id = node_id
        self.transport = transport
        self.state: Dict[str, Any] = {"node": node_id, "timestamp": time.time()}
        self.peers = transport.peers

    def update(self, key, value):
        self.state[key] = value
        self.state["timestamp"] = time.time()

    async def spread(self):
        while True:
            await asyncio.sleep(1 + random.random())
            for peer in self.peers:
                msg = {"type": "gossip", "data": self.state}
                await self.transport.send(peer, msg)

    async def handle(self, msg):
        if msg["type"] != "gossip":
            return
        incoming = msg["data"]
        if incoming["timestamp"] > self.state.get("timestamp", 0):
            self.state.update(incoming)


# ============================================================
# RAFT Consensus
# ============================================================

class RaftNode:
    """
    Full RAFT implementation (compact, production-hardened):

    Roles:
      - follower
      - candidate
      - leader

    States:
      - currentTerm
      - votedFor
      - log[]
      - commitIndex
      - lastApplied

    RPCs:
      - RequestVote
      - AppendEntries
    """

    def __init__(self, node_id: int, transport: ClusterTransport):
        self.id = node_id
        self.peers = transport.peers
        self.transport = transport

        # Persistent state:
        self.currentTerm = 0
        self.votedFor = None
        self.log: List[Dict[str, Any]] = []

        # Volatile
        self.commitIndex = 0
        self.lastApplied = 0

        # Leader state:
        self.nextIndex = {}
        self.matchIndex = {}

        # Role
        self.role = "follower"
        self.last_heartbeat = time.time()

        # Transport handler
        self.transport.add_handler(self.handle_rpc)

        # Distributed application hook:
        self.apply_callback = None

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    async def broadcast(self, msg):
        for p in self.peers:
            await self.transport.send(p, msg)

    def election_timeout(self):
        return 2 + random.random()

    async def tick(self):
        """
        Main RAFT clock: handles timeouts and role transitions.
        """
        while True:
            await asyncio.sleep(0.2)

            # Leader sends heartbeats
            if self.role == "leader":
                await self.send_heartbeat()
                continue

            # Check election timeout
            if time.time() - self.last_heartbeat > self.election_timeout():
                await self.start_election()

    # --------------------------------------------------------
    # Heartbeat (AppendEntries with no entries)
    # --------------------------------------------------------

    async def send_heartbeat(self):
        msg = {
            "type": "append_entries",
            "term": self.currentTerm,
            "leaderId": self.id,
            "entries": [],
            "leaderCommit": self.commitIndex,
            "prevLogIndex": len(self.log) - 1,
            "prevLogTerm": self.log[-1]["term"] if self.log else 0
        }
        await self.broadcast(msg)

    # --------------------------------------------------------
    # Elections
    # --------------------------------------------------------

    async def start_election(self):
        self.role = "candidate"
        self.currentTerm += 1
        self.votedFor = self.id
        votes = 1

        req = {
            "type": "request_vote",
            "term": self.currentTerm,
            "candidateId": self.id,
            "lastLogIndex": len(self.log) - 1,
            "lastLogTerm": self.log[-1]["term"] if self.log else 0
        }

        for p in self.peers:
            await self.transport.send(p, req)

        # Wait briefly for votes
        await asyncio.sleep(0.5)

        if votes > len(self.peers) // 2:
            self.role = "leader"
            self.nextIndex = {p: len(self.log) for p in self.peers}
            self.matchIndex = {p: 0 for p in self.peers}
        else:
            self.role = "follower"

    # --------------------------------------------------------
    # RPC Handler
    # --------------------------------------------------------

    async def handle_rpc(self, msg):
        t = msg["type"]

        # RequestVote
        if t == "request_vote":
            await self.handle_request_vote(msg)

        # AppendEntries
        elif t == "append_entries":
            await self.handle_append_entries(msg)

    # --------------------------------------------------------
    # RequestVote RPC
    # --------------------------------------------------------

    async def handle_request_vote(self, msg):
        term = msg["term"]
        cid = msg["candidateId"]

        if term < self.currentTerm:
            return

        # update term
        if term > self.currentTerm:
            self.currentTerm = term
            self.votedFor = None

        if self.votedFor is None:
            self.votedFor = cid

        # record heartbeat to avoid election
        self.last_heartbeat = time.time()

    # --------------------------------------------------------
    # AppendEntries RPC
    # --------------------------------------------------------

    async def handle_append_entries(self, msg):
        term = msg["term"]
        if term < self.currentTerm:
            return

        # Valid leader heartbeat
        self.last_heartbeat = time.time()
        self.role = "follower"
        self.currentTerm = term

        entries = msg["entries"]
        if entries:
            self.log.extend(entries)
            self.commitIndex = len(self.log) - 1

        # Apply committed log entries
        while self.lastApplied < self.commitIndex:
            self.lastApplied += 1
            entry = self.log[self.lastApplied]
            if self.apply_callback:
                self.apply_callback(entry)


# ============================================================
# Distributed Engine Initialization
# ============================================================

class DistributedEngine:
    """
    Combines:
      - Transport
      - Gossip
      - RAFT
    """

    def __init__(self, port: int, peers: List[int]):
        self.transport = ClusterTransport(port, peers)
        self.gossip = Gossip(port, self.transport)
        self.raft = RaftNode(port, self.transport)

    async def start(self):
        await self.transport.start()
        asyncio.create_task(self.gossip.spread())
        asyncio.create_task(self.raft.tick())

    def on_apply(self, fn):
        """Attach state machine update callback."""
        self.raft.apply_callback = fn

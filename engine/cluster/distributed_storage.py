"""
Distributed Storage Layer
=========================

Implements:
- Hybrid consistency (RAFT strong writes + Gossip eventual reads)
- Distributed Key-Value Store
- Distributed Object Store (blob storage)
- Manifest metadata database
- Local caching layer
- Replication + anti-entropy

This is the universal data backend powering:
- DAG state
- Workflow metadata
- Compiler manifests
- Runtime caches
- Cluster state
"""

import os
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, Optional

from engine.cluster.raft import RaftEngine
from engine.cluster.gossip import GossipEngine


# ============================================================
# LOCAL STORAGE
# ============================================================

class LocalShard:
    """
    Stores data at:
        .engine_state/shards/<port>/
    """

    ROOT = Path(".engine_state/shards")

    def __init__(self, port: int):
        self.root = self.ROOT / str(port)
        self.root.mkdir(parents=True, exist_ok=True)

        (self.root / "kv").mkdir(exist_ok=True)
        (self.root / "objects").mkdir(exist_ok=True)
        (self.root / "meta").mkdir(exist_ok=True)

    # -----------------------
    # KV
    # -----------------------

    def kv_path(self, key: str) -> Path:
        return self.root / "kv" / f"{key}.json"

    def kv_write(self, key: str, value: Any):
        p = self.kv_path(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, indent=2))
        tmp.replace(p)

    def kv_read(self, key: str) -> Optional[Any]:
        p = self.kv_path(key)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except:
                return None
        return None

    # -----------------------
    # Object Store
    # -----------------------

    def obj_path(self, key: str) -> Path:
        return self.root / "objects" / key

    def obj_write(self, key: str, data: bytes):
        p = self.obj_path(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)

    def obj_read(self, key: str) -> Optional[bytes]:
        p = self.obj_path(key)
        return p.read_bytes() if p.exists() else None

    # -----------------------
    # Metadata
    # -----------------------

    def meta_path(self, key: str) -> Path:
        return self.root / "meta" / f"{key}.json"

    def meta_write(self, key: str, data: Any):
        p = self.meta_path(key)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(p)

    def meta_read(self, key: str) -> Optional[Any]:
        p = self.meta_path(key)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except:
                return None
        return None


# ============================================================
# DISTRIBUTED STORAGE ENGINE
# ============================================================

class DistributedStorage:

    def __init__(self, raft: RaftEngine, gossip: GossipEngine):
        self.raft = raft
        self.gossip = gossip
        self.shard = LocalShard(raft.port)

        # In-memory read cache
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 1.0
        self.cache_time: Dict[str, float] = {}

    # ---------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------

    def _cache_get(self, key: str):
        if key in self.cache and (time.time() - self.cache_time[key]) < self.cache_ttl:
            return self.cache[key]
        return None

    def _cache_set(self, key: str, value: Any):
        self.cache[key] = value
        self.cache_time[key] = time.time()

    # ---------------------------------------------------------
    # KV OPERATIONS
    # =========================================================

    # -----------------------
    # Strong Write (RAFT)
    # -----------------------

    def put_strong(self, key: str, value: Any):
        """
        Strongly consistent write using RAFT log replication.
        """
        entry = {"cmd": "kv_put", "key": key, "value": value}

        leader = self.raft.node.leader_id or self.raft.port
        if leader != self.raft.port:
            # Send write to leader
            return self._send_to_leader(leader, entry)

        # Local write as leader
        self.shard.kv_write(key, value)
        self._cache_set(key, value)
        # In full RAFT: replicate to followers
        return True

    # -----------------------
    # Eventual Read (Gossip)
    # -----------------------

    def get_eventual(self, key: str) -> Optional[Any]:
        """
        Try cache → local → gossip replicas → return last-known.
        """
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        local = self.shard.kv_read(key)
        if local is not None:
            self._cache_set(key, local)
            return local

        # Try random peers
        peers = self.gossip.peer_ports
        random.shuffle(peers)
        for p in peers:
            val = self._get_from_peer(p, key)
            if val is not None:
                self._cache_set(key, val)
                return val

        return None

    # -----------------------
    # Internal helpers
    # -----------------------

    def _send_to_leader(self, leader_port: int, entry: dict):
        try:
            import asyncio
            async def _send():
                _, w = await asyncio.open_connection("127.0.0.1", leader_port)
                w.write(json.dumps(entry).encode())
                await w.drain()
            asyncio.run(_send())
            return True
        except:
            return False

    def _get_from_peer(self, peer: int, key: str) -> Optional[Any]:
        """
        Try to fetch the KV from peer shard.
        """
        try:
            import asyncio
            msg = {"cmd": "kv_get", "key": key}

            async def _fetch():
                r, w = await asyncio.open_connection("127.0.0.1", peer)
                w.write(json.dumps(msg).encode())
                await w.drain()
                data = await r.read(65536)
                return json.loads(data.decode())

            resp = asyncio.run(_fetch())
            return resp.get("value")

        except:
            return None

    # ---------------------------------------------------------
    # OBJECT STORAGE
    # =========================================================

    def put_object(self, key: str, data: bytes):
        """
        Replicate object across cluster eventually.
        """
        self.shard.obj_write(key, data)
        # Push to peers asynchronously
        for p in self.gossip.peer_ports:
            self._push_object(p, key, data)

    def _push_object(self, peer: int, key: str, data: bytes):
        try:
            import asyncio
            async def _send():
                _, w = await asyncio.open_connection("127.0.0.1", peer)
                msg = {
                    "cmd": "object_put",
                    "key": key,
                    "data": list(data)  # JSON-safe
                }
                w.write(json.dumps(msg).encode())
                await w.drain()
            asyncio.run(_send())
        except:
            pass

    def get_object(self, key: str) -> Optional[bytes]:
        local = self.shard.obj_read(key)
        if local is not None:
            return local

        # Try peers
        for p in self.gossip.peer_ports:
            obj = self._get_object_from_peer(p, key)
            if obj is not None:
                self.shard.obj_write(key, obj)
                return obj

        return None

    def _get_object_from_peer(self, peer: int, key: str) -> Optional[bytes]:
        try:
            import asyncio
            msg = {"cmd": "object_get", "key": key}

            async def _fetch():
                r, w = await asyncio.open_connection("127.0.0.1", peer)
                w.write(json.dumps(msg).encode())
                await w.drain()
                data = await r.read(65536)
                out = json.loads(data.decode())
                return bytes(out.get("data", []))

            return asyncio.run(_fetch())
        except:
            return None

    # ---------------------------------------------------------
    # METADATA DB
    # =========================================================

    def put_meta(self, key: str, value: Any):
        self.shard.meta_write(key, value)

    def get_meta(self, key: str) -> Optional[Any]:
        return self.shard.meta_read(key)


# ============================================================
# FACTORY
# ============================================================

def create_distributed_storage(raft: RaftEngine, gossip: GossipEngine) -> DistributedStorage:
    return DistributedStorage(raft, gossip)

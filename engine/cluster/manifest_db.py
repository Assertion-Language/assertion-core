"""
Distributed Manifest Database
=============================

Built on top of:
- DistributedStorage (file 17)
- RAFT (strong writes)
- Gossip (cluster availability)

Provides:
- Versioned manifests
- Integrity hashing
- Strong-write updates
- Fast eventual reads
- Rollback support
- Manifest signing (HMAC)
- Cluster-wide replication

Manifests include:
- DSL specs
- Compiler metadata
- VM/JIT/WASM build manifests
- Configuration profiles
"""

import time
import json
import hmac
import hashlib
from typing import Dict, Any, Optional

from engine.cluster.distributed_storage import DistributedStorage


# ============================================================
# MANIFEST SIGNING (HMAC)
# ============================================================

class ManifestSigner:
    SECRET = b"ASSERTION_MANIFEST_SECURE_V1"

    @staticmethod
    def sign(data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True).encode()
        return hmac.new(ManifestSigner.SECRET, raw, hashlib.sha256).hexdigest()

    @staticmethod
    def verify(data: Dict[str, Any], sig: str) -> bool:
        raw = json.dumps(data, sort_keys=True).encode()
        expected = hmac.new(ManifestSigner.SECRET, raw, hashlib.sha256).hexdigest()
        return expected == sig


# ============================================================
# MANIFEST ENTRY
# ============================================================

class ManifestEntry:
    def __init__(self, key: str, version: float, data: dict, signature: str):
        self.key = key
        self.version = version
        self.data = data
        self.signature = signature

    def to_dict(self):
        return {
            "key": self.key,
            "version": self.version,
            "data": self.data,
            "signature": self.signature,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ManifestEntry":
        return ManifestEntry(
            key=d["key"],
            version=d["version"],
            data=d["data"],
            signature=d["signature"],
        )


# ============================================================
# MANIFEST DB ENGINE
# ============================================================

class ManifestDB:

    def __init__(self, storage: DistributedStorage):
        self.storage = storage
        self.cache: Dict[str, ManifestEntry] = {}
        self.cache_ttl = 1.0
        self.cache_time: Dict[str, float] = {}

    # ---------------------------------------------------------
    # Cache helpers
    # ---------------------------------------------------------

    def _cache_get(self, key: str) -> Optional[ManifestEntry]:
        if key in self.cache:
            if (time.time() - self.cache_time[key]) < self.cache_ttl:
                return self.cache[key]
        return None

    def _cache_set(self, key: str, entry: ManifestEntry):
        self.cache[key] = entry
        self.cache_time[key] = time.time()

    # ---------------------------------------------------------
    # Strong write using RAFT
    # ---------------------------------------------------------

    def put_strong(self, key: str, data: Dict[str, Any]) -> ManifestEntry:
        """
        Writes a versioned manifest:
        - Bumps version timestamp
        - Signs with HMAC
        - Writes via RAFT strong-write
        """

        version = time.time()
        signature = ManifestSigner.sign(data)

        entry = ManifestEntry(
            key=key,
            version=version,
            data=data,
            signature=signature
        )

        # Strong write (RAFT)
        stored = entry.to_dict()
        self.storage.put_strong(f"manifest:{key}", stored)

        # Cache
        self._cache_set(key, entry)

        return entry

    # ---------------------------------------------------------
    # Eventual-consistent read using Gossip
    # ---------------------------------------------------------

    def get_eventual(self, key: str) -> Optional[ManifestEntry]:
        """
        Fast read using local cache → local shard → gossip peers.
        """

        cached = self._cache_get(key)
        if cached:
            return cached

        raw = self.storage.get_eventual(f"manifest:{key}")
        if not raw:
            return None

        entry = ManifestEntry.from_dict(raw)

        # Verify integrity
        if not ManifestSigner.verify(entry.data, entry.signature):
            print(f"[MANIFEST] Tampered manifest detected: {key}")
            return None

        self._cache_set(key, entry)
        return entry

    # ---------------------------------------------------------
    # Rollback to previous version
    # ---------------------------------------------------------

    def rollback(self, key: str, to_version: float):
        """
        Replace current manifest with an older version.
        Only allowed on RAFT leader.
        """

        # Fetch manifest history list
        hist_key = f"manifest_history:{key}"
        history = self.storage.get_eventual(hist_key) or []

        # Find matching version
        for item in history:
            if abs(item["version"] - to_version) < 1e-9:
                restored = ManifestEntry.from_dict(item)
                self.put_strong(key, restored.data)
                return restored

        raise KeyError(f"No manifest version {to_version} for key {key}")

    # ---------------------------------------------------------
    # Append to history log
    # ---------------------------------------------------------

    def push_history(self, entry: ManifestEntry):
        hist_key = f"manifest_history:{entry.key}"

        hist = self.storage.get_eventual(hist_key) or []
        hist.append(entry.to_dict())

        # Strong-write updated history
        self.storage.put_strong(hist_key, hist)

    # ---------------------------------------------------------
    # Master operation: safe put + history
    # ---------------------------------------------------------

    def put(self, key: str, data: Dict[str, Any]) -> ManifestEntry:
        """
        High-level write:
        • version bump
        • strong write
        • history tracking
        """
        entry = self.put_strong(key, data)
        self.push_history(entry)
        return entry


# ============================================================
# FACTORY
# ============================================================

def create_manifest_db(storage: DistributedStorage) -> ManifestDB:
    return ManifestDB(storage)

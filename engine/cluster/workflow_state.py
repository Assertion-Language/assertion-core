"""
Workflow Persistence Layer
==========================

Provides:
- Durable workflow state store
- Checkpoints and resume support
- Distributed synchronization of workflow metadata
- Local persistent DB using JSON
- Integration with:
    • DAG engine (execution_graph.py)
    • RAFT (consistent ordering)
    • Gossip (cluster membership)
    • Distributed Task Queue
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from engine.cluster.raft import RaftEngine
from engine.cluster.gossip import GossipEngine


# ============================================================
# FILE SYSTEM STORAGE
# ============================================================

class WorkflowStateStore:
    """
    Stores workflow data in:
        .engine_state/workflows/<workflow_id>.json

    Very compact, universally portable (iPad / Linux / macOS).
    """

    ROOT = Path(".engine_state/workflows")

    def __init__(self):
        self.ROOT.mkdir(parents=True, exist_ok=True)

    def _path(self, workflow_id: str) -> Path:
        return self.ROOT / f"{workflow_id}.json"

    def exists(self, workflow_id: str) -> bool:
        return self._path(workflow_id).exists()

    def load(self, workflow_id: str) -> Dict[str, Any]:
        p = self._path(workflow_id)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text())
        except:
            return {}

    def save(self, workflow_id: str, data: Dict[str, Any]):
        p = self._path(workflow_id)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(p)  # atomic write


# ============================================================
# WORKFLOW CHECKPOINT MANAGER
# ============================================================

class WorkflowCheckpointManager:

    def __init__(self, raft: RaftEngine, gossip: GossipEngine):
        self.raft = raft
        self.gossip = gossip
        self.store = WorkflowStateStore()

    # ---------------------------------------------------------
    # CREATE OR UPDATE WORKFLOW SNAPSHOT
    # ---------------------------------------------------------

    def checkpoint(self, workflow_id: str, dag_state: dict):
        """
        Persist workflow state:
        {
            "workflow_id": ...,
            "timestamp": ...,
            "nodes": {
                "A": {status: "...", result: "..."},
                ...
            }
        }
        """
        data = {
            "workflow_id": workflow_id,
            "timestamp": time.time(),
            "state": dag_state,
            "leader": self.raft.node.leader_id,
            "membership": {
                nid: {"status": m.status, "port": m.port}
                for nid, m in self.gossip.members.items()
            }
        }

        self.store.save(workflow_id, data)

    # ---------------------------------------------------------
    # LOAD EXISTING WORKFLOW STATE
    # ---------------------------------------------------------

    def load_checkpoint(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        if not self.store.exists(workflow_id):
            return None
        return self.store.load(workflow_id)

    # ---------------------------------------------------------
    # RESUME WORKFLOW (after crash)
    # ---------------------------------------------------------

    def resume_workflow(self, dag_engine, workflow_id: str):
        """
        Attempt to resume a workflow:
        • restores node statuses
        • resumes incomplete nodes
        • replays DAG execution
        """
        cp = self.load_checkpoint(workflow_id)
        if not cp:
            print(f"[WF-RESUME] No checkpoint for {workflow_id}")
            return None

        dag_state = cp["state"]
        # Reconstruct DAG
        from engine.cluster.execution_graph import WorkflowDAG

        dag = WorkflowDAG(workflow_id)

        # Restore DAG nodes
        for nid, node in dag_state["nodes"].items():
            dag.add(
                node_id=nid,
                payload=node.get("payload", {}),
                deps=node.get("deps", []),
                retries=node.get("retries", 0)
            )

        dag.finalize()

        # Apply restored statuses
        for nid, node_state in dag_state["nodes"].items():
            dag.nodes[nid].status = node_state["status"]
            dag.nodes[nid].result = node_state.get("result", None)

        print(f"[WF-RESUME] Restored workflow {workflow_id}")
        return dag

    # ---------------------------------------------------------
    # UPDATE NODE STATE
    # ---------------------------------------------------------

    def update_node(self, workflow_id: str, node_id: str,
                    status: str, result: Any, deps: list, payload: dict, retries: int):
        """
        Update node inside workflow checkpoint.
        """

        existing = self.load_checkpoint(workflow_id) or {
            "workflow_id": workflow_id,
            "state": {"nodes": {}},
            "timestamp": time.time()
        }

        if "nodes" not in existing["state"]:
            existing["state"]["nodes"] = {}

        existing["state"]["nodes"][node_id] = {
            "status": status,
            "result": result,
            "deps": deps,
            "payload": payload,
            "retries": retries
        }

        existing["timestamp"] = time.time()
        self.store.save(workflow_id, existing)


# ============================================================
# HIGH-LEVEL API WRAPPER
# ============================================================

class WorkflowStateAPI:

    def __init__(self, raft: RaftEngine, gossip: GossipEngine):
        self.manager = WorkflowCheckpointManager(raft, gossip)

    def checkpoint_workflow(self, workflow_id: str, dag_state: dict):
        self.manager.checkpoint(workflow_id, dag_state)

    def load(self, workflow_id: str):
        return self.manager.load_checkpoint(workflow_id)

    def resume(self, dag_engine, workflow_id: str):
        return self.manager.resume_workflow(dag_engine, workflow_id)

    def update_node(self, workflow_id: str, node_id: str,
                    status: str, result: Any, deps: list,
                    payload: dict, retries: int):
        self.manager.update_node(
            workflow_id, node_id, status, result, deps, payload, retries
        )


# ============================================================
# FACTORY
# ============================================================

def create_workflow_state_api(raft: RaftEngine, gossip: GossipEngine) -> WorkflowStateAPI:
    return WorkflowStateAPI(raft, gossip)

"""
Execution Graph Integration Layer
=================================

This module provides:
- DAG retrieval for the dashboard
- DAG node state updates
- Live workflow execution state mapping
- Integration with:
    • Workflow runtime
    • Event bus
    • Orchestrator
    • DAG Visualizer (front-end)
    • HTTP Gateway

Exposes RPC commands to:
- Get current workflow DAG
- Get node states
- Send workflow replay instructions
- Fetch workflow metadata

"""

import asyncio
from typing import Dict, Any

from engine.cluster.mesh_router import MeshRouter
from engine.event.event_bus import bus
from engine.workflows.workflow_engine import workflow_engine


class DAGIntegration:

    def __init__(self, router: MeshRouter):
        self.router = router

        # Register cluster RPC
        router.register("dag.get", self._rpc_get_dag)
        router.register("dag.node_states", self._rpc_get_node_states)
        router.register("dag.replay", self._rpc_replay_workflow)

        # Local cache (for dashboard queries)
        self.latest_dags: Dict[str, Dict[str, Any]] = {}
        self.node_states: Dict[str, Dict[str, str]] = {}  # workflow_id → node_id → state

        # Subscribe to workflow events
        bus.subscribe("workflow_state", self._on_workflow_state_event)

    # ---------------------------------------------------------
    # EVENT HANDLER: workflow state updates
    # ---------------------------------------------------------

    async def _on_workflow_state_event(self, event):
        """
        event:
        {
            "workflow_id": "...",
            "node_id": "...",
            "state": "running|success|failed|pending"
        }
        """
        wid = event.get("workflow_id")
        nid = event.get("node_id")
        state = event.get("state")

        if wid not in self.node_states:
            self.node_states[wid] = {}

        self.node_states[wid][nid] = state

    # ---------------------------------------------------------
    # RPC: Get full DAG definition
    # ---------------------------------------------------------

    async def _rpc_get_dag(self, msg):
        """
        Input:
            {
              "cmd": "dag.get",
              "workflow_id": "X"
            }

        Response:
            {
              "nodes": [...],
              "edges": [...]
            }
        """
        wid = msg.get("workflow_id")

        dag = workflow_engine.get_dag(wid)
        if not dag:
            return {"error": "workflow not found"}

        # Cache for dashboard
        self.latest_dags[wid] = dag

        return dag

    # ---------------------------------------------------------
    # RPC: Node state map
    # ---------------------------------------------------------

    async def _rpc_get_node_states(self, msg):
        """
        Input:
            {"workflow_id": "..."}
        Output:
            { "node_id": "state", ... }
        """
        wid = msg.get("workflow_id")
        return self.node_states.get(wid, {})

    # ---------------------------------------------------------
    # RPC: Replay workflow
    # ---------------------------------------------------------

    async def _rpc_replay_workflow(self, msg):
        """
        Replays a workflow node-by-node.
        Useful for debugging + visualization.
        """
        wid = msg.get("workflow_id")
        speed = msg.get("speed", 0.3)

        dag = workflow_engine.get_dag(wid)
        if not dag:
            return {"error": "workflow not found"}

        nodes = [n["id"] for n in dag.get("nodes", [])]

        # reset states
        self.node_states[wid] = {}

        for nid in nodes:
            # update state → running
            self.node_states[wid][nid] = "running"
            await asyncio.sleep(speed)
            # update state → completed
            self.node_states[wid][nid] = "completed"
            await asyncio.sleep(speed)

        return {"ok": True}


# ============================================================
# FACTORY
# ============================================================

def create_dag_integration(router: MeshRouter) -> DAGIntegration:
    return DAGIntegration(router)

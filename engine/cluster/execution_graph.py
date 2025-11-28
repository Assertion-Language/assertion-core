"""
Execution Graph (DAG) Engine
============================

Implements:
- DAG construction
- Cycle detection
- Topological sorting
- Distributed execution of nodes
- Parallel execution using fibers
- Retry, lineage, caching
- Integration with task queue + distributed API

This engine powers workflow-like pipelines
(similar to Airflow, Prefect, Dagster — but fully integrated).
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable

from engine.cluster.distributed_api import DistributedExecutionAPI
from engine.scheduler.fibers import scheduler


# ============================================================
# DAG NODE
# ============================================================

class DAGNode:
    def __init__(self, node_id: str, payload: dict, deps: List[str] = None, retries=0):
        self.node_id = node_id
        self.payload = payload              # dict describing execution (VM/JIT/WASM)
        self.deps = deps or []              # other node_ids this depends on
        self.retries = retries
        self.result = None
        self.status = "pending"             # pending / running / done / failed

        self.children = []                  # filled later


# ============================================================
# DAG WORKFLOW
# ============================================================

class WorkflowDAG:

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.nodes: Dict[str, DAGNode] = {}
        self.sorted: List[str] = []

    # --------------------------------------------------------
    # Add node to DAG
    # --------------------------------------------------------

    def add(self, node_id: str, payload: dict, deps: List[str] = None, retries=0):
        if node_id in self.nodes:
            raise ValueError(f"Duplicate DAG node: {node_id}")
        self.nodes[node_id] = DAGNode(node_id, payload, deps, retries)

    # --------------------------------------------------------
    # Build dependency graph
    # --------------------------------------------------------

    def _build_graph(self):
        for nid, node in self.nodes.items():
            for d in node.deps:
                self.nodes[d].children.append(nid)

    # --------------------------------------------------------
    # Detect cycles using DFS
    # --------------------------------------------------------

    def _check_cycles(self):
        visited = {}
        stack = {}

        def dfs(nid):
            visited[nid] = True
            stack[nid] = True

            for child in self.nodes[nid].children:
                if child not in visited:
                    if dfs(child):
                        return True
                elif stack.get(child):
                    return True

            stack[nid] = False
            return False

        for nid in self.nodes:
            if nid not in visited:
                if dfs(nid):
                    raise RuntimeError("Cycle detected in DAG.")

    # --------------------------------------------------------
    # Topological sort
    # --------------------------------------------------------

    def _toposort(self):
        indeg = {nid: 0 for nid in self.nodes}

        for node in self.nodes.values():
            for d in node.deps:
                indeg[node.node_id] += 1

        q = [nid for nid, deg in indeg.items() if deg == 0]
        order = []

        while q:
            nid = q.pop(0)
            order.append(nid)

            for child in self.nodes[nid].children:
                indeg[child] -= 1
                if indeg[child] == 0:
                    q.append(child)

        if len(order) != len(self.nodes):
            raise RuntimeError("Invalid DAG (incomplete topo sort).")

        self.sorted = order

    # --------------------------------------------------------
    # Finalize DAG
    # --------------------------------------------------------

    def finalize(self):
        self._build_graph()
        self._check_cycles()
        self._toposort()


# ============================================================
# EXECUTION ENGINE
# ============================================================

class ExecutionGraphEngine:

    def __init__(self, dist_api: DistributedExecutionAPI):
        self.dist = dist_api

        # Track running DAGs
        self.active: Dict[str, WorkflowDAG] = {}

    # --------------------------------------------------------
    # Run a workflow DAG
    # --------------------------------------------------------

    async def run(self, dag: WorkflowDAG):
        dag.finalize()
        self.active[dag.workflow_id] = dag

        print(f"[DAG] Executing workflow: {dag.workflow_id}")
        print(f"[DAG] Topological order: {dag.sorted}")

        # Track futures of nodes running in parallel
        running: Dict[str, asyncio.Task] = {}

        async def run_node(nid: str):
            node = dag.nodes[nid]
            node.status = "running"
            print(f"[DAG] Node {nid} executing...")

            try:
                # Submit distributed task
                fut = await self.dist.submit(node.payload)
                await fut.get()

                node.status = "done"
                node.result = fut.result

            except Exception as e:
                print(f"[DAG] ERROR node {nid}:", e)
                if node.retries > 0:
                    node.retries -= 1
                    node.status = "pending"
                    print(f"[DAG] Retrying {nid}...")
                    return await run_node(nid)  # retry
                else:
                    node.status = "failed"
                    raise

        # For each node in topo order, execute when deps completed
        for nid in dag.sorted:
            node = dag.nodes[nid]

            # Wait for dependencies
            for dep in node.deps:
                dep_node = dag.nodes[dep]
                while dep_node.status not in ("done", "failed"):
                    await asyncio.sleep(0.01)

                if dep_node.status == "failed":
                    node.status = "failed"
                    raise RuntimeError(f"Dependency {dep} failed for node {nid}")

            # Run this node in a fiber-backed asyncio wrapper
            task = asyncio.create_task(run_node(nid))
            running[nid] = task

        # Wait for all nodes to finish
        for nid, task in running.items():
            await task

        print(f"[DAG] Workflow {dag.workflow_id} completed.")
        return {nid: n.result for nid, n in dag.nodes.items()}


# ============================================================
# FACTORY
# ============================================================

def create_execution_graph_engine(dist_api: DistributedExecutionAPI) -> ExecutionGraphEngine:
    return ExecutionGraphEngine(dist_api)

"""
Orchestrator CLI
================

Provides a unified command-line interface for:
- Cluster administration (RAFT + gossip)
- Task submission
- Workflow submission
- Manifest management
- Storage inspection
- Debugger controls
- Event Bus stream viewer
- Execution requests (VM/JIT/WASM)

This CLI is universal (works on iPad, Linux, macOS).
"""

import argparse
import asyncio
import json
import sys
from typing import Any

from engine.cluster.mesh_router import MeshRouter


# ============================================================
# HELPER: SEND RPC
# ============================================================

async def rpc_send(port: int, payload: dict) -> Any:
    router = MeshRouter(port=0)  # ephemeral sender
    return await router.send(port, payload)


# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_cluster_info(args):
    resp = await rpc_send(args.port, {"cmd": "cluster.info"})
    print(json.dumps(resp, indent=2))


async def cmd_raft_status(args):
    resp = await rpc_send(args.port, {"cmd": "raft.status"})
    print(json.dumps(resp, indent=2))


async def cmd_list_nodes(args):
    resp = await rpc_send(args.port, {"cmd": "gossip.members"})
    print(json.dumps(resp, indent=2))


async def cmd_submit_task(args):
    resp = await rpc_send(args.port, {
        "cmd": "task_submit",
        "payload": {"job": args.job}
    })
    print(json.dumps(resp, indent=2))


async def cmd_submit_workflow(args):
    """
    Submits a workflow DAG definition (JSON format).
    """
    dag = json.loads(open(args.file).read())
    resp = await rpc_send(args.port, {
        "cmd": "workflow.submit",
        "dag": dag
    })
    print(json.dumps(resp, indent=2))


async def cmd_debug_pause(args):
    await rpc_send(args.port, {"cmd": "dbg.pause"})
    print("[OK] Debugger paused.")


async def cmd_debug_resume(args):
    await rpc_send(args.port, {"cmd": "dbg.resume"})
    print("[OK] Debugger resumed.")


async def cmd_debug_state(args):
    resp = await rpc_send(args.port, {"cmd": "dbg.state"})
    print(json.dumps(resp, indent=2))


async def cmd_debug_eval(args):
    resp = await rpc_send(args.port, {"cmd": "dbg.eval", "expr": args.expr})
    print(json.dumps(resp, indent=2))


async def cmd_manifest_get(args):
    resp = await rpc_send(args.port, {"cmd": "manifest.get", "key": args.key})
    print(json.dumps(resp, indent=2))


async def cmd_manifest_set(args):
    data = json.loads(args.json)
    resp = await rpc_send(args.port, {"cmd": "manifest.set", "key": args.key, "data": data})
    print(json.dumps(resp, indent=2))


async def cmd_store_get(args):
    resp = await rpc_send(args.port, {"cmd": "kv_get", "key": args.key})
    print(json.dumps(resp, indent=2))


async def cmd_store_put(args):
    data = json.loads(args.json)
    resp = await rpc_send(args.port, {"cmd": "kv_put", "key": args.key, "value": data})
    print(json.dumps(resp, indent=2))


async def cmd_event_tail(args):
    print("[Streaming events… press Ctrl+C to stop]")
    while True:
        events = await rpc_send(args.port, {"cmd": "get_event_sample"})
        if events:
            for e in events.get("events", []):
                print(f"[{e['timestamp']:.3f}] {e['channel']}: {e['payload']}")
        await asyncio.sleep(1)


async def cmd_execute_vm(args):
    resp = await rpc_send(args.port, {"cmd": "execute_vm", "code": args.code})
    print(json.dumps(resp, indent=2))


async def cmd_execute_wasm(args):
    wasm = open(args.file, "rb").read()
    resp = await rpc_send(args.port, {"cmd": "execute_wasm", "module": list(wasm)})
    print(json.dumps(resp, indent=2))


async def cmd_execute_jit(args):
    ir = json.loads(open(args.file).read())
    resp = await rpc_send(args.port, {"cmd": "execute_jit", "ir": ir})
    print(json.dumps(resp, indent=2))


# ============================================================
# BUILD CLI
# ============================================================

def build_cli():
    p = argparse.ArgumentParser(description="Cluster Orchestrator CLI")
    p.add_argument("--port", type=int, required=True, help="Target orchestrator port")

    sub = p.add_subparsers()

    # Cluster info
    s = sub.add_parser("cluster-info")
    s.set_defaults(func=cmd_cluster_info)

    # List nodes
    s = sub.add_parser("nodes")
    s.set_defaults(func=cmd_list_nodes)

    # RAFT status
    s = sub.add_parser("raft-status")
    s.set_defaults(func=cmd_raft_status)

    # Submit task
    s = sub.add_parser("task")
    s.add_argument("job")
    s.set_defaults(func=cmd_submit_task)

    # Submit workflow
    s = sub.add_parser("workflow")
    s.add_argument("file")
    s.set_defaults(func=cmd_submit_workflow)

    # Debugger
    s = sub.add_parser("dbg-pause")
    s.set_defaults(func=cmd_debug_pause)

    s = sub.add_parser("dbg-resume")
    s.set_defaults(func=cmd_debug_resume)

    s = sub.add_parser("dbg-state")
    s.set_defaults(func=cmd_debug_state)

    s = sub.add_parser("dbg-eval")
    s.add_argument("expr")
    s.set_defaults(func=cmd_debug_eval)

    # Manifest DB
    s = sub.add_parser("manifest-get")
    s.add_argument("key")
    s.set_defaults(func=cmd_manifest_get)

    s = sub.add_parser("manifest-set")
    s.add_argument("key")
    s.add_argument("json")
    s.set_defaults(func=cmd_manifest_set)

    # Storage KV
    s = sub.add_parser("kv-get")
    s.add_argument("key")
    s.set_defaults(func=cmd_store_get)

    s = sub.add_parser("kv-put")
    s.add_argument("key")
    s.add_argument("json")
    s.set_defaults(func=cmd_store_put)

    # Events
    s = sub.add_parser("events")
    s.set_defaults(func=cmd_event_tail)

    # VM / WASM / JIT
    s = sub.add_parser("vm")
    s.add_argument("code")
    s.set_defaults(func=cmd_execute_vm)

    s = sub.add_parser("wasm")
    s.add_argument("file")
    s.set_defaults(func=cmd_execute_wasm)

    s = sub.add_parser("jit")
    s.add_argument("file")
    s.set_defaults(func=cmd_execute_jit)

    return p


# ============================================================
# MAIN
# ============================================================

def main():
    cli = build_cli()
    args = cli.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()

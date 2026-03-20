from __future__ import annotations

import math
from pathlib import Path

import yaml


def default_runtime_root() -> Path:
    return Path.home() / "fyp_runtime_data"


def default_scene_points_file() -> Path:
    return default_runtime_root() / "gnss" / "current_scene" / "scene_points.yaml"


def load_scene_points(scene_points_file: str | Path) -> dict:
    path = Path(scene_points_file).expanduser()
    with open(path, "r", encoding="utf-8") as scene_file:
        data = yaml.safe_load(scene_file) or {}

    raw_nodes = data.get("nodes", {})
    if not isinstance(raw_nodes, dict) or not raw_nodes:
        raise RuntimeError(f"scene points file has no nodes: {path}")

    nodes: dict[int, dict] = {}
    name_to_id: dict[str, int] = {}
    for raw_id, raw_node in raw_nodes.items():
        node_id = int(raw_id)
        node = {
            "id": node_id,
            "name": str(raw_node["name"]),
            "lat": float(raw_node["lat"]),
            "lon": float(raw_node["lon"]),
            "alt": float(raw_node.get("alt", 0.0)),
            "x": float(raw_node["x"]),
            "y": float(raw_node["y"]),
            "z": float(raw_node.get("z", 0.0)),
            "anchor": bool(raw_node.get("anchor", False)),
            "dest": bool(raw_node.get("dest", False)),
        }
        nodes[node_id] = node
        name_to_id[node["name"]] = node_id

    return {
        "scene_name": str(data.get("scene_name", "unknown_scene")),
        "fixed_origin": dict(data.get("fixed_origin", {})),
        "nodes": nodes,
        "name_to_id": name_to_id,
        "edges": [list(edge) for edge in data.get("edges", [])],
        "anchor_ids": [int(node_id) for node_id, node in nodes.items() if node["anchor"]],
        "destination_ids": [int(node_id) for node_id, node in nodes.items() if node["dest"]],
        "destination_names": {
            node["name"]: node_id for node_id, node in nodes.items() if node["dest"]
        },
    }


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)

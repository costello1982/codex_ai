"""Topology generation from design object."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from graphviz import Source

from app.models.design_models import FabricDesign
from app.utils.graph_utils import graph_to_dot


class TopologyService:
    def build_graph(self, design: FabricDesign) -> nx.Graph:
        g = nx.Graph()
        for d in design.devices:
            g.add_node(d.name, role=d.role.value)
        for link in design.underlay_links:
            g.add_edge(link.local_device, link.peer_device)
        if design.interconnect.enabled:
            g.add_node("remote-dc", role="remote")
            for d in design.devices:
                if d.role.value == "border_leaf":
                    g.add_edge(d.name, "remote-dc")
        return g

    def render(self, design: FabricDesign, output_dir: Path) -> tuple[str, str | None, str]:
        g = self.build_graph(design)
        dot = graph_to_dot(g)
        dot_path = output_dir / "topology.dot"
        dot_path.write_text(dot, encoding="utf-8")
        img_path = None
        try:
            src = Source(dot)
            src.format = "png"
            img_path = src.render(str(output_dir / "topology"), cleanup=True)
        except Exception:
            img_path = None
        topo_json = json.dumps({"nodes": list(g.nodes(data=True)), "edges": list(g.edges())}, indent=2)
        (output_dir / "topology.json").write_text(topo_json, encoding="utf-8")
        return dot, img_path, topo_json

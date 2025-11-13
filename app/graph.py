from __future__ import annotations
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Node:
    # keeping node info simple for now; can attach more metadata later if needed
    id: str
    health_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class DAG:
    nodes: Dict[str, Node]
    # outgoing edges: source -> [targets]
    edges: Dict[str, List[str]]
    # incoming edges: target -> [sources]
    rev_edges: Dict[str, List[str]]

    @classmethod
    def from_json(cls, payload: dict) -> "DAG":
        # turn the raw node dicts into Node objects keyed by id
        nodes = {n["id"]: Node(**{**n}) for n in payload.get("nodes", [])}

        edges = defaultdict(list)
        rev = defaultdict(list)

        for e in payload.get("edges", []):
            s, t = e["from"], e["to"]

            # basic sanity: no edge should reference a node we don't have
            if s not in nodes or t not in nodes:
                raise ValueError(f"edge references unknown node: {s}->{t}")

            edges[s].append(t)
            rev[t].append(s)

            # ensure we have entries for both directions so lookups don't blow up
            edges.setdefault(t, edges.get(t, []))
            rev.setdefault(s, rev.get(s, []))

        # some nodes may not have any edges at all, that's fine
        for nid in nodes:
            edges.setdefault(nid, edges.get(nid, []))
            rev.setdefault(nid, rev.get(nid, []))

        # quick cycle check using a Kahn-style indegree peeling
        indeg = {n: len(rev[n]) for n in nodes}
        q = deque([n for n, d in indeg.items() if d == 0])
        seen = 0

        while q:
            u = q.popleft()
            seen += 1
            for v in edges[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)

        # if we didn't visit all nodes, something is looping
        if seen != len(nodes):
            raise ValueError("graph is not acyclic")

        return cls(nodes=dict(nodes), edges=dict(edges), rev_edges=dict(rev))

    def roots(self) -> List[str]:
        # roots: nodes with no incoming edges
        return [n for n, preds in self.rev_edges.items() if not preds]

    def bfs_levels(self) -> List[List[str]]:
        """
        Group nodes by "levels" so that dependencies always appear
        before the nodes that depend on them.
        """
        indeg = {n: len(self.rev_edges[n]) for n in self.nodes}
        q = deque(self.roots())
        levels: List[List[str]] = []

        while q:
            size = len(q)
            level = []

            for _ in range(size):
                u = q.popleft()
                level.append(u)

                for v in self.edges[u]:
                    indeg[v] -= 1
                    if indeg[v] == 0:
                        q.append(v)

            levels.append(level)

        return levels

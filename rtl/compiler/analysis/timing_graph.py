"""Timing graph primitives and DAG critical-path helpers."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimingEdge:
    src: str
    dst: str
    delay: float


@dataclass
class TimingGraph:
    edges: list[TimingEdge] = field(default_factory=list)

    def add_edge(self, src: str, dst: str, delay: float) -> None:
        self.edges.append(TimingEdge(src=src, dst=dst, delay=delay))

    def longest_path(self) -> tuple[float, list[str]]:
        nodes: set[str] = set()
        incoming: dict[str, int] = defaultdict(int)
        outgoing: dict[str, list[TimingEdge]] = defaultdict(list)
        for edge in self.edges:
            nodes.add(edge.src)
            nodes.add(edge.dst)
            incoming[edge.dst] += 1
            outgoing[edge.src].append(edge)
            incoming.setdefault(edge.src, 0)

        queue = deque(sorted(node for node in nodes if incoming[node] == 0))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for edge in outgoing[node]:
                incoming[edge.dst] -= 1
                if incoming[edge.dst] == 0:
                    queue.append(edge.dst)

        distance = {node: 0.0 for node in order}
        predecessor: dict[str, str | None] = {node: None for node in order}
        for node in order:
            for edge in outgoing[node]:
                candidate = distance[node] + edge.delay
                if candidate > distance.get(edge.dst, float("-inf")):
                    distance[edge.dst] = candidate
                    predecessor[edge.dst] = node

        if not distance:
            return 0.0, []

        end = max(distance, key=distance.get)
        path: list[str] = []
        cursor: str | None = end
        while cursor is not None:
            path.append(cursor)
            cursor = predecessor[cursor]
        path.reverse()
        return distance[end], path

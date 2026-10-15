import collections
import itertools
from typing import Union
import networkx as nx
from engine.models import ImpactResult, NormalizedChange


def analyze_impact(
    graph: nx.DiGraph,
    entry_nodes: Union[list[str], NormalizedChange],
    uncovered: list[str] | None = None,
    resolved_references: int = 0,
    depth_cap: int = 6,
    node_cap: int = 500,
) -> ImpactResult:
    """
    Computes the blast radius of a change using breadth-first search along
    outgoing edges (provider -> consumer).

    - Excludes entry nodes from affected_nodes.
    - Caps traversal at depth_cap (default 6).
    - Caps total affected nodes at node_cap (default 500).
    - If depth_cap or node_cap cuts off nodes with unvisited successors, flags
      'truncated:depth_cap' or 'truncated:node_cap' in uncovered.
    - Missing entry nodes are recorded in uncovered as 'unknown_entry:<id>'.
    - Uses itertools.islice with nx.all_simple_paths for up to 3 paths per target.
    - Calculates coverage as:
      coverage = resolved_references / (resolved_references + len(uncovered))
      (1.0 when both are zero).
    """
    if isinstance(entry_nodes, NormalizedChange):
        raw_entries = list(entry_nodes.affected_resources)
    else:
        raw_entries = list(entry_nodes)

    uncovered_list: list[str] = list(uncovered) if uncovered is not None else []

    # Validate entry nodes against graph
    valid_entry_nodes: list[str] = []
    for entry in raw_entries:
        if entry in graph:
            valid_entry_nodes.append(entry)
        else:
            unknown_flag = f"unknown_entry:{entry}"
            if unknown_flag not in uncovered_list:
                uncovered_list.append(unknown_flag)

    affected_nodes: list[str] = []
    # Entry nodes are excluded from affected_nodes
    visited = set(raw_entries)
    queue: collections.deque[tuple[str, int]] = collections.deque(
        (node, 0) for node in valid_entry_nodes
    )

    while queue:
        curr, depth = queue.popleft()

        successors = list(graph.successors(curr)) if curr in graph else []
        unvisited_succs = [s for s in successors if s not in visited]

        if depth >= depth_cap:
            if unvisited_succs:
                if "truncated:depth_cap" not in uncovered_list:
                    uncovered_list.append("truncated:depth_cap")
            continue

        for succ in unvisited_succs:
            if len(affected_nodes) >= node_cap:
                if "truncated:node_cap" not in uncovered_list:
                    uncovered_list.append("truncated:node_cap")
                break

            visited.add(succ)
            affected_nodes.append(succ)
            queue.append((succ, depth + 1))

    # Record up to 3 simple paths per target across all valid entries
    paths: dict[str, list[list[str]]] = {}
    for target in affected_nodes:
        target_paths: list[list[str]] = []
        for entry in valid_entry_nodes:
            remaining = 3 - len(target_paths)
            if remaining <= 0:
                break
            try:
                for p in itertools.islice(
                    nx.all_simple_paths(graph, source=entry, target=target, cutoff=depth_cap),
                    remaining,
                ):
                    target_paths.append(list(p))
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

        if target_paths:
            paths[target] = target_paths

    # Calculate coverage
    total_refs = resolved_references + len(uncovered_list)
    if total_refs == 0:
        coverage = 1.0
    else:
        coverage = resolved_references / total_refs

    return ImpactResult(
        entry_nodes=raw_entries,
        affected_nodes=affected_nodes,
        paths=paths,
        coverage=coverage,
        uncovered=uncovered_list,
    )

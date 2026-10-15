import networkx as nx
from engine.models import GraphEdge, GraphNode


def add_node(graph: nx.DiGraph, node: GraphNode) -> None:
    """Adds a GraphNode to the NetworkX DiGraph with its attributes."""
    graph.add_node(
        node.id,
        type=node.type,
        name=node.name,
        provenance=node.provenance.value if hasattr(node.provenance, "value") else str(node.provenance),
        criticality=node.criticality,
        meta=node.meta,
    )


def add_edge(graph: nx.DiGraph, edge: GraphEdge) -> None:
    """
    Adds a GraphEdge from provider (source) to consumer (target).
    Raises ValueError if either endpoint does not exist in the graph.
    """
    if edge.source not in graph:
        raise ValueError(f"Unknown edge source endpoint: '{edge.source}'")
    if edge.target not in graph:
        raise ValueError(f"Unknown edge target endpoint: '{edge.target}'")

    graph.add_edge(
        edge.source,
        edge.target,
        relationship=edge.relationship,
        provenance=edge.provenance.value if hasattr(edge.provenance, "value") else str(edge.provenance),
    )


def build_graph(nodes: list[GraphNode], edges: list[GraphEdge]) -> nx.DiGraph:
    """
    Constructs a NetworkX DiGraph from provided nodes and edges.
    Nodes are added first, then edges are added with endpoint validation.
    """
    graph = nx.DiGraph()
    for node in nodes:
        add_node(graph, node)
    for edge in edges:
        add_edge(graph, edge)
    return graph

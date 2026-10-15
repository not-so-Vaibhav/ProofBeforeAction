import pytest
from engine.graph import add_edge, add_node, build_graph
from engine.impact import analyze_impact
from engine.models import GraphEdge, GraphNode, Provenance


def make_node(node_id: str, criticality: int = 50) -> GraphNode:
    return GraphNode(
        id=node_id,
        type="table",
        name=node_id,
        provenance=Provenance.extracted,
        criticality=criticality,
    )


def make_edge(source: str, target: str) -> GraphEdge:
    return GraphEdge(
        source=source,
        target=target,
        relationship="references",
        provenance=Provenance.extracted,
    )


def test_linear_chain() -> None:
    """Test A -> B -> C -> D downstream impact and paths."""
    nodes = [make_node(nid) for nid in ["A", "B", "C", "D"]]
    edges = [
        make_edge("A", "B"),
        make_edge("B", "C"),
        make_edge("C", "D"),
    ]
    graph = build_graph(nodes, edges)

    result = analyze_impact(graph, entry_nodes=["A"])

    assert result.entry_nodes == ["A"]
    # Entry node A is excluded from affected_nodes
    assert result.affected_nodes == ["B", "C", "D"]
    assert "A" not in result.affected_nodes
    assert result.paths["D"] == [["A", "B", "C", "D"]]
    assert result.coverage == 1.0
    assert result.uncovered == []


def test_branching_graph() -> None:
    """Test branching paths A -> B -> D and A -> C -> D."""
    nodes = [make_node(nid) for nid in ["A", "B", "C", "D"]]
    edges = [
        make_edge("A", "B"),
        make_edge("A", "C"),
        make_edge("B", "D"),
        make_edge("C", "D"),
    ]
    graph = build_graph(nodes, edges)

    result = analyze_impact(graph, entry_nodes=["A"])

    assert set(result.affected_nodes) == {"B", "C", "D"}
    assert "D" in result.paths
    assert len(result.paths["D"]) == 2
    assert ["A", "B", "D"] in result.paths["D"]
    assert ["A", "C", "D"] in result.paths["D"]


def test_cycle_safety() -> None:
    """Test cycle safety with A -> B -> C -> A and B -> D."""
    nodes = [make_node(nid) for nid in ["A", "B", "C", "D"]]
    edges = [
        make_edge("A", "B"),
        make_edge("B", "C"),
        make_edge("C", "A"),
        make_edge("B", "D"),
    ]
    graph = build_graph(nodes, edges)

    result = analyze_impact(graph, entry_nodes=["A"])

    # Must terminate without infinite loop
    assert "A" not in result.affected_nodes
    assert set(result.affected_nodes) == {"B", "C", "D"}
    assert "D" in result.affected_nodes


def test_depth_cap() -> None:
    """
    Test depth cap of 6 on N0 -> N1 -> ... -> N8.
    Assert N6 is included, and N7/N8 are excluded and flagged with truncated:depth_cap.
    """
    node_ids = [f"N{i}" for i in range(9)]  # N0 to N8
    nodes = [make_node(nid) for nid in node_ids]
    edges = [make_edge(f"N{i}", f"N{i+1}") for i in range(8)]
    graph = build_graph(nodes, edges)

    result = analyze_impact(graph, entry_nodes=["N0"], depth_cap=6)

    # N0 is entry (excluded)
    # N1..N6 are at depth 1..6 (included)
    # N7, N8 are at depth 7, 8 (excluded)
    assert "N6" in result.affected_nodes
    assert "N7" not in result.affected_nodes
    assert "N8" not in result.affected_nodes
    assert result.affected_nodes == [f"N{i}" for i in range(1, 7)]
    assert "truncated:depth_cap" in result.uncovered


def test_node_cap() -> None:
    """Test node cap limits total affected nodes and flags truncated:node_cap."""
    node_ids = [f"N{i}" for i in range(7)]  # N0 to N6
    nodes = [make_node(nid) for nid in node_ids]
    edges = [make_edge(f"N{i}", f"N{i+1}") for i in range(6)]
    graph = build_graph(nodes, edges)

    result = analyze_impact(graph, entry_nodes=["N0"], node_cap=3)

    assert len(result.affected_nodes) == 3
    assert result.affected_nodes == ["N1", "N2", "N3"]
    assert "truncated:node_cap" in result.uncovered


def test_max_three_paths_per_target() -> None:
    """Test that at most 3 simple paths are returned per target."""
    # Create 5 alternate parallel paths from A to Target:
    # A -> P1 -> Target, A -> P2 -> Target, ..., A -> P5 -> Target
    nodes = [make_node("A"), make_node("Target")]
    edges = []
    for i in range(1, 6):
        p_node = f"P{i}"
        nodes.append(make_node(p_node))
        edges.append(make_edge("A", p_node))
        edges.append(make_edge(p_node, "Target"))

    graph = build_graph(nodes, edges)
    result = analyze_impact(graph, entry_nodes=["A"])

    assert "Target" in result.paths
    assert len(result.paths["Target"]) == 3


def test_coverage_calculation() -> None:
    """
    Test coverage formula:
    coverage = resolved / (resolved + len(uncovered)), 1.0 when both are zero.
    """
    nodes = [make_node("A"), make_node("B")]
    edges = [make_edge("A", "B")]
    graph = build_graph(nodes, edges)

    # Both zero -> 1.0
    r1 = analyze_impact(graph, entry_nodes=["A"], resolved_references=0)
    assert r1.coverage == 1.0

    # With unresolved reference
    r2 = analyze_impact(
        graph,
        entry_nodes=["A"],
        uncovered=["pipeline:dynamic_sql"],
        resolved_references=3,
    )
    # 3 / (3 + 1) = 0.75
    assert r2.coverage == 0.75
    assert "pipeline:dynamic_sql" in r2.uncovered


def test_unknown_entry_node() -> None:
    """Test missing entry node is flagged in uncovered as unknown_entry:<id>."""
    nodes = [make_node("A")]
    graph = build_graph(nodes, [])

    result = analyze_impact(graph, entry_nodes=["A", "missing_node"])

    assert "unknown_entry:missing_node" in result.uncovered
    assert result.affected_nodes == []


def test_add_edge_unknown_endpoints_raises() -> None:
    """Test that add_edge raises ValueError when endpoints are missing."""
    graph = build_graph([make_node("A")], [])

    with pytest.raises(ValueError, match="Unknown edge target endpoint"):
        add_edge(graph, make_edge("A", "B"))

    with pytest.raises(ValueError, match="Unknown edge source endpoint"):
        add_edge(graph, make_edge("B", "A"))

import networkx as nx
from typing import Dict, Any, List, Optional, Set
from backend.app.schemas.graph import GraphResponse, GraphNode, GraphEdge

def graph_to_cytoscape_dict(G_sub: nx.MultiDiGraph, focal_node_id: Optional[str] = None) -> GraphResponse:
    """
    Converts a NetworkX subgraph into a Cytoscape.js compatible response format.
    """
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    for node_id, data in G_sub.nodes(data=True):
        node_type = data.get("type", "UNKNOWN")
        label = data.get("label", str(node_id))
        risk_score = data.get("risk_score", 0)
        anomaly_score = data.get("anomaly_score", 0.0)
        is_focal = (node_id == focal_node_id)

        clean_props = {k: v for k, v in data.items() if k not in ("id", "type", "label", "risk_score", "anomaly_score")}
        nodes.append(
            GraphNode(
                id=str(node_id),
                label=label,
                type=node_type,
                risk_score=risk_score,
                anomaly_score=anomaly_score,
                is_focal=is_focal,
                properties=clean_props
            )
        )

    edge_idx = 0
    for u, v, k, data in G_sub.edges(data=True, keys=True):
        edge_type = data.get("type", "CONNECTED")
        label = data.get("label")
        amount = data.get("amount")
        ts = data.get("timestamp")
        edge_id = f"e_{u}_{v}_{k}_{edge_idx}"
        edge_idx += 1

        clean_props = {key: val for key, val in data.items() if key not in ("type", "label", "amount", "timestamp")}
        edges.append(
            GraphEdge(
                id=edge_id,
                source=str(u),
                target=str(v),
                type=edge_type,
                label=label,
                amount=amount,
                timestamp=ts,
                properties=clean_props
            )
        )

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
        focal_node_id=focal_node_id,
        metadata={
            "focal_node": focal_node_id,
            "density": round(nx.density(G_sub), 4) if len(G_sub) > 1 else 0.0
        }
    )

def extract_k_hop_subgraph(G: nx.MultiDiGraph, focal_id: str, k: int = 2, max_nodes: int = 150) -> GraphResponse:
    """
    Extracts a k-hop ego network around focal_id, respecting max_nodes budget.
    """
    if not G.has_node(focal_id):
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0, focal_node_id=focal_id)

    # Convert to undirected for distance discovery
    G_undirected = G.to_undirected(as_view=True)
    lengths = nx.single_source_shortest_path_length(G_undirected, focal_id, cutoff=k)

    # Sort nodes by distance and degree
    sorted_nodes = sorted(lengths.keys(), key=lambda n: (lengths[n], -G.degree(n)))
    selected_nodes = sorted_nodes[:max_nodes]

    subgraph = G.subgraph(selected_nodes).copy()
    return graph_to_cytoscape_dict(subgraph, focal_node_id=focal_id)

def find_shortest_path_subgraph(G: nx.MultiDiGraph, source_id: str, target_id: str) -> GraphResponse:
    """
    Finds the shortest directed (or undirected) path between two entities and returns the path subgraph.
    """
    if not G.has_node(source_id) or not G.has_node(target_id):
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0, focal_node_id=source_id)

    path_nodes: Set[str] = set()
    try:
        # Try directed first
        path = nx.shortest_path(G, source=source_id, target=target_id)
        path_nodes.update(path)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        try:
            # Fallback to undirected path
            G_und = G.to_undirected(as_view=True)
            path = nx.shortest_path(G_und, source=source_id, target=target_id)
            path_nodes.update(path)
        except Exception:
            return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0, focal_node_id=source_id)

    # Include 1-hop neighbors of path nodes for context
    context_nodes = set(path_nodes)
    for n in list(path_nodes):
        context_nodes.update(list(G.neighbors(n))[:5])

    subgraph = G.subgraph(context_nodes).copy()
    return graph_to_cytoscape_dict(subgraph, focal_node_id=source_id)

def get_overall_subgraph(G: nx.MultiDiGraph, limit: int = 100) -> GraphResponse:
    """
    Returns high-level graph snapshot (e.g. top highest degree / highest risk nodes).
    """
    if len(G) == 0:
        return GraphResponse(nodes=[], edges=[], node_count=0, edge_count=0)

    # Sort nodes by degree and risk
    sorted_nodes = sorted(
        G.nodes(),
        key=lambda n: (G.nodes[n].get("risk_score", 0), G.degree(n)),
        reverse=True
    )[:limit]

    subgraph = G.subgraph(sorted_nodes).copy()
    return graph_to_cytoscape_dict(subgraph)

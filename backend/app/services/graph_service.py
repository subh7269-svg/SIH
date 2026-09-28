import networkx as nx
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.graph.builder import build_networkx_graph_from_db
from backend.app.graph.queries import (
    extract_k_hop_subgraph,
    find_shortest_path_subgraph,
    get_overall_subgraph
)
from backend.app.schemas.graph import GraphResponse
from backend.app.core.logging import logger

# Cached in-memory graph per dataset or global
_GRAPH_CACHE: Dict[str, nx.MultiDiGraph] = {}

def get_or_build_graph(db: Session, dataset_id: Optional[str] = None, force_rebuild: bool = False) -> nx.MultiDiGraph:
    cache_key = dataset_id or "GLOBAL"
    if force_rebuild or cache_key not in _GRAPH_CACHE:
        logger.debug(f"[GRAPH_SERVICE] Building graph for cache_key={cache_key} (force={force_rebuild})")
        G = build_networkx_graph_from_db(db, dataset_id=dataset_id)
        _GRAPH_CACHE[cache_key] = G
        logger.debug(f"[GRAPH_SERVICE] Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return _GRAPH_CACHE[cache_key]

def invalidate_graph_cache(dataset_id: Optional[str] = None):
    logger.debug(f"[GRAPH_SERVICE] Invalidating graph cache: dataset_id={dataset_id}")
    if dataset_id and dataset_id in _GRAPH_CACHE:
        del _GRAPH_CACHE[dataset_id]
    _GRAPH_CACHE.pop("GLOBAL", None)

def query_entity_subgraph(db: Session, entity_id: str, k: int = 2, dataset_id: Optional[str] = None) -> GraphResponse:
    G = get_or_build_graph(db, dataset_id=dataset_id)
    return extract_k_hop_subgraph(G, focal_id=entity_id, k=k)

def query_shortest_path(db: Session, source_id: str, target_id: str, dataset_id: Optional[str] = None) -> GraphResponse:
    G = get_or_build_graph(db, dataset_id=dataset_id)
    return find_shortest_path_subgraph(G, source_id=source_id, target_id=target_id)

def query_global_graph_overview(db: Session, limit: int = 80, dataset_id: Optional[str] = None) -> GraphResponse:
    G = get_or_build_graph(db, dataset_id=dataset_id)
    return get_overall_subgraph(G, limit=limit)

"""
Heterogeneous Graph Generation Service.
Constructs multi-relational graphs linking Wallets, Transactions, and IP observations.
Outputs graph_edges.csv and Cytoscape/NetworkX-compatible subgraphs with k-hop expansion.
"""
from typing import Dict, List, Set, Any, Optional
import networkx as nx
import pandas as pd
from pathlib import Path

class GraphService:
    """
    In-memory graph manager supporting Cytoscape formatting and k-hop neighborhood queries.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self.edges_records: List[Dict[str, str]] = []

    def add_transaction_edges(
        self,
        txid: str,
        input_wallets: List[str],
        output_wallets: List[str],
        src_ip: Optional[str] = None
    ):
        """Adds wallet inputs, wallet outputs, and IP observation edges for a transaction."""
        # Add TX node
        self.graph.add_node(txid, node_type="transaction", label=f"TX: {txid[:8]}...")

        # Wallet -> TX (input_to)
        for w in input_wallets:
            if not w:
                continue
            self.graph.add_node(w, node_type="wallet", label=f"W: {w[:8]}...")
            self.graph.add_edge(w, txid, relationship="input_to", source_type="wallet", target_type="transaction")
            self.edges_records.append({
                "source": w,
                "target": txid,
                "source_type": "wallet",
                "target_type": "transaction",
                "relationship": "input_to"
            })

        # TX -> Wallet (output_to)
        for w in output_wallets:
            if not w:
                continue
            self.graph.add_node(w, node_type="wallet", label=f"W: {w[:8]}...")
            self.graph.add_edge(txid, w, relationship="output_to", source_type="transaction", target_type="wallet")
            self.edges_records.append({
                "source": txid,
                "target": w,
                "source_type": "transaction",
                "target_type": "wallet",
                "relationship": "output_to"
            })

        # IP -> TX (network_observation)
        if src_ip and src_ip not in ("None", "nan", ""):
            self.graph.add_node(src_ip, node_type="ip", label=f"IP: {src_ip}")
            self.graph.add_edge(src_ip, txid, relationship="network_observation", source_type="ip", target_type="transaction")
            self.edges_records.append({
                "source": src_ip,
                "target": txid,
                "source_type": "ip",
                "target_type": "transaction",
                "relationship": "network_observation"
            })

    def export_edges_csv(self, output_path: Path):
        """Writes graph_edges.csv."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.edges_records)
        if df.empty:
            df = pd.DataFrame(columns=["source", "target", "source_type", "target_type", "relationship"])
        df.drop_duplicates().to_csv(output_path, index=False)

    def get_subgraph_cytoscape(self, center_id: str, hops: int = 1) -> Dict[str, Any]:
        """
        Extracts k-hop neighborhood around center_id (transaction, wallet, or IP)
        formatted for Cytoscape.js and D3.js.
        """
        if center_id not in self.graph:
            return {
                "nodes": [
                    {
                        "data": {
                            "id": center_id,
                            "label": center_id[:12],
                            "type": "transaction",
                            "score": 50
                        }
                    }
                ],
                "edges": []
            }

        # Ego graph k-hops (undirected view for multi-hop expansion)
        undirected = self.graph.to_undirected()
        sub_nodes = set(nx.single_source_shortest_path_length(undirected, center_id, cutoff=hops).keys())

        cytoscape_nodes = []
        for n in sub_nodes:
            attrs = self.graph.nodes.get(n, {})
            node_type = attrs.get("node_type", "unknown")
            label = attrs.get("label", n[:12])
            cytoscape_nodes.append({
                "data": {
                    "id": n,
                    "label": label,
                    "type": node_type,
                    "is_center": (n == center_id)
                }
            })

        cytoscape_edges = []
        for u, v, data in self.graph.edges(data=True):
            if u in sub_nodes and v in sub_nodes:
                edge_id = f"{u}_{v}_{data.get('relationship', 'rel')}"
                cytoscape_edges.append({
                    "data": {
                        "id": edge_id,
                        "source": u,
                        "target": v,
                        "relationship": data.get("relationship", "related_to")
                    }
                })

        return {
            "nodes": cytoscape_nodes,
            "edges": cytoscape_edges,
            "metadata": {
                "center_id": center_id,
                "hops": hops,
                "total_nodes": len(cytoscape_nodes),
                "total_edges": len(cytoscape_edges)
            }
        }

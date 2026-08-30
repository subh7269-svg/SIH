import pytest
from backend.app.services.dataset_service import create_dataset_record
from backend.app.ingestion.pipeline import process_dataset_stream
from backend.app.graph.builder import build_networkx_graph_from_db
from backend.app.graph.queries import extract_k_hop_subgraph, find_shortest_path_subgraph

def test_graph_builder_and_queries(db):
    csv_data = (
        "txid,timestamp,fee,script_type,input_addresses,input_amounts,output_addresses,output_amounts,src_ip,geo_country,asn\n"
        "TX_G1,2026-08-20T10:00:00Z,0.001,P2PKH,bc1q_nodeA,1.0,bc1q_nodeB,0.999,8.8.8.8,US,AS15169\n"
        "TX_G2,2026-08-20T10:05:00Z,0.001,P2PKH,bc1q_nodeB,0.999,bc1q_nodeC,0.998,1.1.1.1,AU,AS13335\n"
    ).encode("utf-8")

    ds = create_dataset_record(db, "graph_test.csv", "csv", len(csv_data))
    process_dataset_stream(db, ds.id, csv_data, "csv")

    G = build_networkx_graph_from_db(db, dataset_id=ds.id)
    assert G.has_node("bc1q_nodeA")
    assert G.has_node("TX_G1")
    assert G.has_node("bc1q_nodeB")
    assert G.has_node("8.8.8.8")

    # k-hop
    k_hop = extract_k_hop_subgraph(G, "bc1q_nodeA", k=2)
    assert k_hop.node_count > 0
    assert any(n.id == "bc1q_nodeA" for n in k_hop.nodes)

    # Path
    path_res = find_shortest_path_subgraph(G, "bc1q_nodeA", "bc1q_nodeC")
    assert path_res.node_count >= 3

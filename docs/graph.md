# TraceX Graph Engine & Link Analysis

---

## 1. NetworkX MultiDiGraph Construction

The graph engine constructs an in-memory directed multi-graph $G = (V, E)$ from ingested relational records.

### Node Attributes
- `WALLET`: Bitcoin address string, cumulative incoming/outgoing volume, tx count, priority risk score, ML anomaly score.
- `TRANSACTION`: 64-character TXID hash, timestamp, fee, total input/output BTC, script type.
- `IP`: IPv4 / IPv6 address, resolved country, resolved ASN, observation count.
- `ASN`: Autonomous System Number, network name.
- `COUNTRY`: ISO 3166-1 alpha-2 country jurisdiction code.

### Edge Semantics
- `INPUT_OF`: Directed from `WALLET` $\to$ `TRANSACTION` with `amount` payload.
- `OUTPUT_TO`: Directed from `TRANSACTION` $\to$ `WALLET` with `amount` payload.
- `OBSERVED_IN`: Directed from `IP` $\to$ `TRANSACTION` with timestamp and relay port (records network broadcast provenance).
- `BELONGS_TO_ASN`: Directed from `IP` $\to$ `ASN`.
- `LOCATED_IN`: Directed from `IP` $\to$ `COUNTRY`.

---

## 2. Graph Traversal Algorithms

1. **k-Hop Ego Network**:
   $$\text{SubGraph}(v, k) = \{ u \in V \mid d(u, v) \le k \}$$
   Extracts bounded neighborhood around focal entities with degree-based node capping to prevent visual clutter.

2. **Shortest Path & Transaction Flow**:
   Computes the minimal directed or undirected path connecting Entity $A$ and Entity $B$ to expose multi-hop intermediary laundering or peeling chains.

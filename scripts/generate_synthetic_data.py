import os
import json
import csv
import random
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

def generate_btc_address(prefix: str = "bc1q") -> str:
    chars = "023456789acdefghjklmnpqrstuvwxyz"
    rand_part = "".join(random.choices(chars, k=38))
    return f"{prefix}{rand_part}"

def generate_txid() -> str:
    raw = f"{random.random()}-{datetime.now().isoformat()}".encode()
    return hashlib.sha256(raw).hexdigest()

def generate_synthetic_dataset(num_normal_txs: int = 80, seed: int = 42) -> dict:
    """
    Generates a deterministic synthetic Bitcoin transaction and network observation dataset
    containing both normal background baseline traffic and controlled anomalous behavioral patterns.
    """
    random.seed(seed)
    base_time = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)

    countries = ["US", "DE", "NL", "RU", "IN", "SG", "CH", "PA", "GB", "AU"]
    asns = ["AS15169 Google", "AS16509 AWS", "AS13335 Cloudflare", "AS200052 Zwiebelfreunde", "AS49981 WorldStream", "AS48282 Hostkey", "AS24940 Hetzner", "AS12345 Swiss Relays"]
    ips = [
        "8.8.8.8", "1.1.1.1", "185.220.101.5", "185.195.23.10", "194.26.29.44",
        "103.21.244.12", "116.202.40.18", "198.51.100.77", "203.0.113.88", "192.0.2.19"
    ]

    records = []
    benchmark_labels = {}  # wallet -> 1 for anomaly, 0 for normal

    # -------------------------------------------------------------
    # 1. Normal Baseline Transactions (80 transactions)
    # -------------------------------------------------------------
    normal_wallets = [generate_btc_address() for _ in range(30)]
    for w in normal_wallets:
        benchmark_labels[w] = 0

    for i in range(num_normal_txs):
        src = random.choice(normal_wallets)
        dst = random.choice(normal_wallets)
        while dst == src:
            dst = random.choice(normal_wallets)

        tx_time = base_time + timedelta(hours=i * 2, minutes=random.randint(5, 55))
        amt = round(random.uniform(0.01, 1.5), 4)
        fee = round(random.uniform(0.0001, 0.0005), 5)
        ip = random.choice(ips)
        asn_str = random.choice(asns).split()[0]
        country = random.choice(countries)

        records.append({
            "txid": generate_txid(),
            "timestamp": tx_time.isoformat(),
            "input_addresses": [src],
            "input_amounts": [amt + fee],
            "output_addresses": [dst],
            "output_amounts": [amt],
            "fee": fee,
            "script_type": "P2WPKH",
            "src_ip": ip,
            "dst_ip": "127.0.0.1",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": country,
            "asn": asn_str
        })

    # -------------------------------------------------------------
    # 2. Anomalous Pattern 1: Rapid Multi-Hop Peeling Chain
    # (Wallet_Peel_A -> Wallet_Peel_B -> Wallet_Peel_C -> Wallet_Peel_D)
    # Rapid timestamps (< 3 mins), high velocity, changing IPs
    # -------------------------------------------------------------
    peel_a = "bc1q_peel_chain_alpha_9901_investigate"
    peel_b = "bc1q_peel_chain_bravo_9902_investigate"
    peel_c = "bc1q_peel_chain_charlie_9903_investigate"
    peel_d = "bc1q_peel_chain_delta_9904_investigate"
    peel_sink = "bc1q_peel_chain_final_sink_9905_target"

    for pw in [peel_a, peel_b, peel_c, peel_d, peel_sink]:
        benchmark_labels[pw] = 1

    peel_time = base_time + timedelta(days=2, hours=4)
    peel_steps = [
        (peel_a, peel_b, 10.5, "185.220.101.5", "DE", "AS200052"),
        (peel_b, peel_c, 10.4, "194.26.29.44", "RU", "AS48282"),
        (peel_c, peel_d, 10.3, "185.195.23.10", "NL", "AS49981"),
        (peel_d, peel_sink, 10.2, "192.0.2.19", "PA", "AS99999"),
    ]

    for step_idx, (s_w, d_w, v_amt, s_ip, s_geo, s_asn) in enumerate(peel_steps):
        t_time = peel_time + timedelta(minutes=step_idx * 3)
        records.append({
            "txid": f"TX_PEEL_CHAIN_{step_idx+1}_{generate_txid()[:12]}",
            "timestamp": t_time.isoformat(),
            "input_addresses": [s_w],
            "input_amounts": [v_amt],
            "output_addresses": [d_w, generate_btc_address()],
            "output_amounts": [v_amt - 0.1, 0.099],
            "fee": 0.001,
            "script_type": "P2PKH",
            "src_ip": s_ip,
            "dst_ip": "127.0.0.1",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": s_geo,
            "asn": s_asn
        })

    # -------------------------------------------------------------
    # 3. Anomalous Pattern 2: High-Fanout Structuring / Layering
    # Single wallet dispersing funds to 20 transient wallets simultaneously
    # -------------------------------------------------------------
    fanout_funder = "bc1q_fanout_master_structuring_8801_high"
    benchmark_labels[fanout_funder] = 1
    fanout_targets = [generate_btc_address() for _ in range(18)]
    for ft in fanout_targets:
        benchmark_labels[ft] = 1

    fanout_time = base_time + timedelta(days=3, hours=8)
    records.append({
        "txid": f"TX_FANOUT_BURST_{generate_txid()[:12]}",
        "timestamp": fanout_time.isoformat(),
        "input_addresses": [fanout_funder],
        "input_amounts": [25.0],
        "output_addresses": fanout_targets,
        "output_amounts": [round(24.95 / len(fanout_targets), 4) for _ in fanout_targets],
        "fee": 0.05,
        "script_type": "P2WSH",
        "src_ip": "198.51.100.77",
        "dst_ip": "127.0.0.1",
        "src_port": 8333,
        "dst_port": 8333,
        "geo_country": "CH",
        "asn": "AS12345"
    })

    # -------------------------------------------------------------
    # 4. Anomalous Pattern 3: Multi-IP Rapid Relaying
    # -------------------------------------------------------------
    multi_ip_wallet = "bc1q_multi_ip_hopper_7701_anomaly"
    benchmark_labels[multi_ip_wallet] = 1
    hopping_time = base_time + timedelta(days=4, hours=2)

    for hop_idx in range(6):
        records.append({
            "txid": f"TX_HOPPING_{hop_idx}_{generate_txid()[:12]}",
            "timestamp": (hopping_time + timedelta(minutes=hop_idx * 5)).isoformat(),
            "input_addresses": [multi_ip_wallet],
            "input_amounts": [1.5],
            "output_addresses": [generate_btc_address()],
            "output_amounts": [1.499],
            "fee": 0.001,
            "script_type": "P2WPKH",
            "src_ip": ips[hop_idx % len(ips)],
            "dst_ip": "127.0.0.1",
            "src_port": 8333,
            "dst_port": 8333,
            "geo_country": countries[hop_idx % len(countries)],
            "asn": asns[hop_idx % len(asns)].split()[0]
        })

    # Sort all records by timestamp
    records.sort(key=lambda r: r["timestamp"])

    return {
        "records": records,
        "benchmark_labels": benchmark_labels
    }

def save_sample_datasets():
    data_pkg = generate_synthetic_dataset()
    records = data_pkg["records"]

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "sample")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Save CSV
    csv_path = os.path.join(out_dir, "bitcoin_network_sample.csv")
    fieldnames = [
        "txid", "timestamp", "fee", "script_type",
        "input_addresses", "input_amounts", "output_addresses", "output_amounts",
        "src_ip", "dst_ip", "src_port", "dst_port", "geo_country", "asn"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["input_addresses"] = ";".join(row["input_addresses"])
            row["output_addresses"] = ";".join(row["output_addresses"])
            row["input_amounts"] = ";".join(map(str, row["input_amounts"]))
            row["output_amounts"] = ";".join(map(str, row["output_amounts"]))
            writer.writerow(row)

    # 2. Save JSON
    json_path = os.path.join(out_dir, "bitcoin_network_sample.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"transactions": records}, f, indent=2)

    # 3. Save XML
    xml_path = os.path.join(out_dir, "bitcoin_network_sample.xml")
    root = ET.Element("transactions")
    for r in records:
        tx_elem = ET.SubElement(root, "transaction")
        for k, v in r.items():
            if isinstance(v, list):
                list_elem = ET.SubElement(tx_elem, k)
                for item in v:
                    item_elem = ET.SubElement(list_elem, "item")
                    item_elem.text = str(item)
            else:
                elem = ET.SubElement(tx_elem, k)
                elem.text = str(v)
    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    print(f"Generated {len(records)} synthetic Bitcoin records in CSV, JSON, XML format at: {out_dir}")

if __name__ == "__main__":
    save_sample_datasets()

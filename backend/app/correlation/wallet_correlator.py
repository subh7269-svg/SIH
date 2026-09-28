"""
Wallet and transaction correlation module.
Correlates transactions with wallet addresses, edgelists, and wallet classification labels.
Ensures zero duplicated relationships and streams/indexes large CSVs efficiently.
"""
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import pandas as pd

from backend.app.correlation.config import correlation_settings
from backend.app.correlation.column_detector import detect_schema
from backend.app.correlation.validator import find_dataset_file

logger = logging.getLogger("tracex.correlation.wallet")

CLASS_NAME_MAP = {
    "1": "illicit",
    "2": "licit",
    "3": "unknown",
    1: "illicit",
    2: "licit",
    3: "unknown"
}

class WalletCorrelator:
    """
    In-memory indexed correlation structures for wallet <-> transaction mappings.
    """
    def __init__(self, dataset_dir: Optional[Path] = None):
        self.dataset_dir = dataset_dir
        self.tx_classes: Dict[str, str] = {}
        self.wallet_classes: Dict[str, str] = {}
        self.tx_to_inputs: Dict[str, Set[str]] = {}
        self.tx_to_outputs: Dict[str, Set[str]] = {}
        self.wallet_to_txs: Dict[str, Set[str]] = {}

    def load_transaction_classes(self) -> int:
        """Loads txs_classes.csv and builds txid -> tx_class mapping."""
        fpath = find_dataset_file("txs_classes.csv", self.dataset_dir)
        if not fpath:
            logger.warning("txs_classes.csv not found; all transactions will have tx_class='unknown'")
            return 0

        logger.info(f"Loading transaction classes from {fpath}")
        df = pd.read_csv(fpath)
        schema = detect_schema(list(df.columns), "tx_class")
        txid_col = schema.get("txid") or df.columns[0]
        class_col = schema.get("tx_class") or df.columns[1]

        for _, row in df.iterrows():
            txid = str(row[txid_col]).strip()
            raw_cls = row[class_col]
            cls_name = CLASS_NAME_MAP.get(raw_cls, CLASS_NAME_MAP.get(str(raw_cls), str(raw_cls).lower()))
            self.tx_classes[txid] = cls_name

        logger.info(f"Loaded {len(self.tx_classes)} transaction classes.")
        return len(self.tx_classes)

    def load_wallet_classes(self) -> int:
        """Loads wallets_classes.csv and builds address -> wallet_class mapping."""
        fpath = find_dataset_file("wallets_classes.csv", self.dataset_dir)
        if not fpath:
            logger.info("wallets_classes.csv not found; skipping wallet labels.")
            return 0

        logger.info(f"Loading wallet classes from {fpath}")
        reader = pd.read_csv(fpath, chunksize=100000)
        total = 0
        for chunk in reader:
            schema = detect_schema(list(chunk.columns), "wallet")
            addr_col = schema.get("wallet_address") or chunk.columns[0]
            cls_col = schema.get("wallet_class") or chunk.columns[1]

            for _, row in chunk.iterrows():
                addr = str(row[addr_col]).strip()
                raw_cls = row[cls_col]
                cls_name = CLASS_NAME_MAP.get(raw_cls, CLASS_NAME_MAP.get(str(raw_cls), str(raw_cls).lower()))
                self.wallet_classes[addr] = cls_name
                total += 1

        logger.info(f"Loaded {len(self.wallet_classes)} wallet class labels.")
        return total

    def load_edgelists(self, target_txids: Optional[Set[str]] = None) -> Tuple[int, int]:
        """
        Loads AddrTx_edgelist.csv (input_addr -> txId) and TxAddr_edgelist.csv (txId -> output_addr).
        If target_txids is provided, filters for those txids to preserve memory.
        """
        in_edges_count = 0
        out_edges_count = 0

        # 1. AddrTx_edgelist (Inputs: address -> txId)
        addr_tx_path = find_dataset_file("AddrTx_edgelist.csv", self.dataset_dir)
        if addr_tx_path:
            logger.info(f"Indexing AddrTx_edgelist from {addr_tx_path}")
            reader = pd.read_csv(addr_tx_path, chunksize=100000)
            for chunk in reader:
                addr_col = chunk.columns[0]
                tx_col = chunk.columns[1]
                for _, row in chunk.iterrows():
                    tx = str(row[tx_col]).strip()
                    if target_txids and tx not in target_txids:
                        continue
                    addr = str(row[addr_col]).strip()
                    if tx not in self.tx_to_inputs:
                        self.tx_to_inputs[tx] = set()
                    self.tx_to_inputs[tx].add(addr)

                    if addr not in self.wallet_to_txs:
                        self.wallet_to_txs[addr] = set()
                    self.wallet_to_txs[addr].add(tx)
                    in_edges_count += 1

        # 2. TxAddr_edgelist (Outputs: txId -> address)
        tx_addr_path = find_dataset_file("TxAddr_edgelist.csv", self.dataset_dir)
        if tx_addr_path:
            logger.info(f"Indexing TxAddr_edgelist from {tx_addr_path}")
            reader = pd.read_csv(tx_addr_path, chunksize=100000)
            for chunk in reader:
                tx_col = chunk.columns[0]
                addr_col = chunk.columns[1]
                for _, row in chunk.iterrows():
                    tx = str(row[tx_col]).strip()
                    if target_txids and tx not in target_txids:
                        continue
                    addr = str(row[addr_col]).strip()
                    if tx not in self.tx_to_outputs:
                        self.tx_to_outputs[tx] = set()
                    self.tx_to_outputs[tx].add(addr)

                    if addr not in self.wallet_to_txs:
                        self.wallet_to_txs[addr] = set()
                    self.wallet_to_txs[addr].add(tx)
                    out_edges_count += 1

        logger.info(f"Edgelists loaded: {in_edges_count} input edges, {out_edges_count} output edges.")
        return in_edges_count, out_edges_count

    def correlate_transaction(
        self,
        txid: str,
        inline_inputs: Optional[List[str]] = None,
        inline_outputs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Combines inline transaction addresses with edgelist mappings.
        Returns deduplicated input wallets, output wallets, related wallets, and their classes.
        """
        tx_class = self.tx_classes.get(txid, "unknown")

        # Inputs
        input_wallets_set = set(self.tx_to_inputs.get(txid, set()))
        if inline_inputs:
            input_wallets_set.update(inline_inputs)

        # Outputs
        output_wallets_set = set(self.tx_to_outputs.get(txid, set()))
        if inline_outputs:
            output_wallets_set.update(inline_outputs)

        # Related wallets = union of inputs and outputs
        related_wallets = sorted(list(input_wallets_set | output_wallets_set))
        input_wallets = sorted(list(input_wallets_set))
        output_wallets = sorted(list(output_wallets_set))

        # Wallet classes
        classes_summary = {}
        for w in related_wallets:
            if w in self.wallet_classes:
                classes_summary[w] = self.wallet_classes[w]

        return {
            "tx_class": tx_class,
            "input_wallets": input_wallets,
            "output_wallets": output_wallets,
            "related_wallets": related_wallets,
            "wallet_classes": classes_summary,
            "wallet_count": len(related_wallets)
        }

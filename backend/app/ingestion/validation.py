import re
import ipaddress
from typing import Tuple, Optional, List

# Bitcoin address patterns:
# Supports real-world Mainnet (P2PKH, P2SH, Bech32 bc1q, Taproot bc1p), Testnet (tb1, 2, m, n),
# and synthetic identifiers (bc1q_..., W_..., Wallet_...).
BTC_ADDRESS_REGEX = re.compile(r"^(1[a-km-zA-HJ-NP-Z1-9]{25,34}|3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-Z0-9_]{6,74}|tb1[a-zA-Z0-9_]{6,74}|[a-zA-Z0-9_\-]{3,90})$")
TXID_HEX_REGEX = re.compile(r"^([a-fA-F0-9]{64}|[a-zA-Z0-9_\-]{3,64})$")

def is_valid_txid(txid: str) -> bool:
    if not txid or not isinstance(txid, str):
        return False
    return bool(TXID_HEX_REGEX.match(txid.strip()))

def is_valid_wallet_address(address: str) -> bool:
    if not address or not isinstance(address, str):
        return False
    clean = address.strip()
    if len(clean) < 3 or len(clean) > 90:
        return False
    return bool(BTC_ADDRESS_REGEX.match(clean))

def is_valid_ip(ip_str: str) -> bool:
    if not ip_str or not isinstance(ip_str, str):
        return False
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except ValueError:
        return False

def validate_record(record: dict) -> Tuple[bool, Optional[str]]:
    """
    Validates an ingested record against required fields, syntax rules, and data integrity.
    Returns (is_valid, rejection_reason).
    """
    # 1. TXID check
    txid = record.get("txid")
    if not txid or not is_valid_txid(str(txid)):
        return False, f"Missing or invalid TXID format: {txid}"

    # 2. Timestamp check
    timestamp = record.get("timestamp")
    if not timestamp:
        return False, "Missing timestamp"

    # 3. Inputs check
    inputs = record.get("input_addresses", [])
    if not isinstance(inputs, list) or len(inputs) == 0:
        return False, "At least one input address is required"
    for addr in inputs:
        if not is_valid_wallet_address(str(addr)):
            return False, f"Malformed input wallet address: {addr}"

    # 4. Outputs check
    outputs = record.get("output_addresses", [])
    if not isinstance(outputs, list) or len(outputs) == 0:
        return False, "At least one output address is required"
    for addr in outputs:
        if not is_valid_wallet_address(str(addr)):
            return False, f"Malformed output wallet address: {addr}"

    # 5. Amounts check
    input_amounts = record.get("input_amounts", [])
    output_amounts = record.get("output_amounts", [])
    if not isinstance(input_amounts, list) or not isinstance(output_amounts, list):
        return False, "Input and output amounts must be lists"

    for amt in input_amounts:
        try:
            val = float(amt)
            if val < 0:
                return False, f"Negative input amount: {val}"
        except (ValueError, TypeError):
            return False, f"Non-numeric input amount: {amt}"

    for amt in output_amounts:
        try:
            val = float(amt)
            if val < 0:
                return False, f"Negative output amount: {val}"
        except (ValueError, TypeError):
            return False, f"Non-numeric output amount: {amt}"

    # 6. Fee check
    fee = record.get("fee", 0.0)
    try:
        if float(fee) < 0:
            return False, f"Negative fee: {fee}"
    except (ValueError, TypeError):
        return False, f"Non-numeric fee: {fee}"

    # 7. IP check (if provided)
    src_ip = record.get("src_ip")
    if src_ip and not is_valid_ip(str(src_ip)):
        return False, f"Invalid source IP address format: {src_ip}"

    return True, None

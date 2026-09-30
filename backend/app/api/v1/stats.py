"""
Dashboard statistics endpoints — provides real-time temporal volume
distribution and alert burst data derived from the actual ingested dataset.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Dict, Any

from backend.app.db.session import get_db
from backend.app.models.transaction import Transaction
from backend.app.models.alert import Alert

router = APIRouter(prefix="/stats", tags=["Dashboard Statistics"])


@router.get("/temporal-volume")
def get_temporal_volume(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns transaction volume and alert counts grouped by UTC hour
    for the 'Observed Volume & Anomaly Bursts' dashboard chart.

    Queries the real ingested transaction data — returns an empty
    array when no data has been ingested yet.
    """
    # Count transactions grouped by hour-of-day
    # SQLite: strftime('%H', timestamp)  /  PostgreSQL: EXTRACT(HOUR FROM timestamp)
    try:
        rows = db.execute(
            text("""
                SELECT
                    CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
                    COUNT(*) AS tx_count,
                    COALESCE(SUM(input_total), 0) AS total_input_volume,
                    COALESCE(SUM(output_total), 0) AS total_output_volume
                FROM transactions
                GROUP BY hour
                ORDER BY hour
            """)
        ).fetchall()
    except Exception:
        # Fallback for PostgreSQL
        rows = db.execute(
            text("""
                SELECT
                    EXTRACT(HOUR FROM timestamp)::INT AS hour,
                    COUNT(*) AS tx_count,
                    COALESCE(SUM(input_total), 0) AS total_input_volume,
                    COALESCE(SUM(output_total), 0) AS total_output_volume
                FROM transactions
                GROUP BY hour
                ORDER BY hour
            """)
        ).fetchall()

    # Count alerts grouped by hour-of-day
    try:
        alert_rows = db.execute(
            text("""
                SELECT
                    CAST(strftime('%H', created_at) AS INTEGER) AS hour,
                    COUNT(*) AS alert_count
                FROM alerts
                GROUP BY hour
                ORDER BY hour
            """)
        ).fetchall()
    except Exception:
        alert_rows = db.execute(
            text("""
                SELECT
                    EXTRACT(HOUR FROM created_at)::INT AS hour,
                    COUNT(*) AS alert_count
                FROM alerts
                GROUP BY hour
                ORDER BY hour
            """)
        ).fetchall()

    # Build alert lookup by hour
    alert_by_hour: Dict[int, int] = {}
    for row in alert_rows:
        alert_by_hour[int(row[0])] = int(row[1])

    # Build hourly data array (all 24 hours, filling gaps with zeros)
    tx_by_hour: Dict[int, Dict] = {}
    for row in rows:
        h = int(row[0])
        tx_by_hour[h] = {
            "tx_count": int(row[1]),
            "volume_btc": round(float(row[2]) + float(row[3]), 6),
        }

    hourly_data = []
    for h in range(24):
        entry = tx_by_hour.get(h, {"tx_count": 0, "volume_btc": 0.0})
        hourly_data.append({
            "time": f"{h:02d}:00",
            "hour": h,
            "tx_count": entry["tx_count"],
            "volume": round(entry["volume_btc"], 4),
            "alerts": alert_by_hour.get(h, 0),
        })

    # Summary stats
    total_tx = sum(d["tx_count"] for d in hourly_data)
    total_vol = sum(d["volume"] for d in hourly_data)
    total_alerts = sum(d["alerts"] for d in hourly_data)

    return {
        "hourly_data": hourly_data,
        "total_transactions": total_tx,
        "total_volume_btc": round(total_vol, 6),
        "total_alerts": total_alerts,
        "has_data": total_tx > 0,
    }

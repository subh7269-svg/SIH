from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Configure connect_args for SQLite if needed (check_same_thread=False)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

# ---------- SQLite Pragmas (WAL Mode, Concurrency & Fast Commits) ----------
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA cache_size=-64000")
        except Exception as e:
            logger.warning(f"[DB_SESSION] Could not set SQLite PRAGMAs: {e}")
        finally:
            cursor.close()

# ---------- DEBUG: Log SQLAlchemy connection pool events ----------
@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("[DB_SESSION] Connection checked out from pool")

@event.listens_for(engine, "checkin")
def _on_checkin(dbapi_conn, connection_record):
    logger.debug("[DB_SESSION] Connection returned to pool")


def ensure_db_schema(target_engine):
    """Ensures existing SQLite tables have newly added columns without requiring manual migration."""
    from sqlalchemy import inspect, text
    from backend.app.db.base import Base
    import backend.app.models  # Register all models including profile
    try:
        Base.metadata.create_all(bind=target_engine)
        inspector = inspect(target_engine)
        if "alerts" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("alerts")]
            new_cols = [
                ("raw_anomaly_score", "FLOAT DEFAULT 0.0"),
                ("validation_score", "FLOAT DEFAULT 0.0"),
                ("supporting_evidence", "JSON DEFAULT '[]'"),
                ("counter_evidence", "JSON DEFAULT '[]'"),
                ("behavioural_deviation", "JSON DEFAULT '{}'"),
                ("historical_context", "JSON DEFAULT '{}'"),
                ("validation_explanation", "VARCHAR(1000)"),
            ]
            with target_engine.begin() as conn:
                for col_name, col_def in new_cols:
                    if col_name not in columns:
                        conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_def}"))
                        logger.info(f"[DB_SESSION] Added missing column: alerts.{col_name}")
    except Exception as e:
        logger.error(f"[DB_SESSION] Schema migration failed: {e}", exc_info=True)

ensure_db_schema(engine)

# expire_on_commit=True ensures that after any commit(), all loaded objects
# are expired and will be re-fetched from DB on next access. This prevents
# stale reads when a different request's session committed new data.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=True)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    logger.debug("[DB_SESSION] New session opened")
    try:
        yield db
    finally:
        db.close()
        logger.debug("[DB_SESSION] Session closed")

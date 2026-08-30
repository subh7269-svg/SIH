from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.db.session import get_db
from backend.app.models.ml import EntityCluster
from backend.app.schemas.ml import ClusterSummary, ClusterListResponse

router = APIRouter(prefix="/clusters", tags=["Entity Clustering"])

@router.get("", response_model=ClusterListResponse)
def get_clusters(dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(EntityCluster)
    if dataset_id:
        query = query.filter(EntityCluster.dataset_id == dataset_id)

    clusters = query.order_by(EntityCluster.cluster_label.asc()).all()
    noise_count = sum(c.member_count for c in clusters if c.cluster_label == -1)

    return ClusterListResponse(
        total_clusters=len([c for c in clusters if c.cluster_label != -1]),
        noise_count=noise_count,
        clusters=[ClusterSummary.model_validate(c) for c in clusters]
    )

@router.get("/{cluster_id}", response_model=ClusterSummary)
def get_cluster(cluster_id: str, db: Session = Depends(get_db)):
    cluster = db.query(EntityCluster).filter(EntityCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found.")
    return ClusterSummary.model_validate(cluster)

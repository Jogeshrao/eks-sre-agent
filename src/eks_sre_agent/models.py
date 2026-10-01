from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

class Health(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

class Confidence(StrEnum):
    CONFIRMED = "CONFIRMED"
    HIGH = "HIGH CONFIDENCE"
    MEDIUM = "MEDIUM CONFIDENCE"
    LOW = "LOW CONFIDENCE"
    INSUFFICIENT = "INSUFFICIENT EVIDENCE"

class ClusterConfig(BaseModel):
    cluster_name: str
    environment: str
    aws_account: str
    region: str
    kconnect_context: str
    expected_kube_context: str
    service_account: str
    namespace: str = "all"
    team: str
    owners: list[str] = Field(default_factory=list)
    email_recipients: list[str] = Field(default_factory=list)
    nodegroups: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)

class Inventory(BaseModel):
    clusters: list[ClusterConfig]

class Issue(BaseModel):
    severity: str
    resource: str
    observation: str
    evidence: list[str] = Field(default_factory=list)
    probable_cause: str = "Insufficient evidence"
    confidence: Confidence = Confidence.INSUFFICIENT
    recommended_actions: list[str] = Field(default_factory=list)

class Anomaly(BaseModel):
    metric: str
    baseline: float | None = None
    current: float | None = None
    percentage_change: float | None = None
    window: str = "rolling-history"
    severity: str = "INFO"
    evidence: list[str] = Field(default_factory=list)

class HealthReport(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cluster: str
    environment: str
    aws_account: str
    region: str
    kubernetes_version: str | None = None
    overall_health: Health = Health.UNKNOWN
    nodes: dict[str, Any] = Field(default_factory=dict)
    pods: dict[str, Any] = Field(default_factory=dict)
    deployments: dict[str, Any] = Field(default_factory=dict)
    statefulsets: dict[str, Any] = Field(default_factory=dict)
    daemonsets: dict[str, Any] = Field(default_factory=dict)
    autoscaling: dict[str, Any] = Field(default_factory=dict)
    networking: dict[str, Any] = Field(default_factory=dict)
    storage: dict[str, Any] = Field(default_factory=dict)
    aws_infrastructure: dict[str, Any] = Field(default_factory=dict)
    resource_utilization: dict[str, Any] = Field(default_factory=dict)
    active_alarms: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[Anomaly] = Field(default_factory=list)
    detected_issues: list[Issue] = Field(default_factory=list)
    probable_causes: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    production_action_status: str = "READ-ONLY: no production changes executed"

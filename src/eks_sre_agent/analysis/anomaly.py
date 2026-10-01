from __future__ import annotations
import json, statistics
from pathlib import Path
from ..models import Anomaly

TRACKED = {
    "node_count": lambda r: float(r.nodes.get("total", 0)),
    "pod_count": lambda r: float(r.pods.get("total", 0)),
    "pod_restarts": lambda r: float(r.pods.get("restarts", 0)),
}

class AnomalyDetector:
    def __init__(self, history_dir: str = "reports/history", warning_pct: float = 25.0, critical_pct: float = 50.0):
        self.dir = Path(history_dir)
        self.warning_pct = warning_pct
        self.critical_pct = critical_pct

    def _history(self, cluster: str):
        p = self.dir / f"{cluster}.jsonl"
        if not p.exists():
            return []
        rows = []
        for line in p.read_text().splitlines()[-96:]:
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: pass
        return rows

    def detect(self, report):
        history = self._history(report.cluster)
        out = []
        for metric, getter in TRACKED.items():
            vals = []
            for h in history:
                try:
                    if metric == "node_count": vals.append(float(h["nodes"]["total"]))
                    elif metric == "pod_count": vals.append(float(h["pods"]["total"]))
                    elif metric == "pod_restarts": vals.append(float(h["pods"]["restarts"]))
                except (KeyError, TypeError, ValueError):
                    pass
            if len(vals) < 4:
                continue
            baseline = statistics.median(vals)
            current = getter(report)
            if baseline <= 0:
                continue
            pct = ((current - baseline) / baseline) * 100
            severity = "CRITICAL" if abs(pct) >= self.critical_pct else "WARNING" if abs(pct) >= self.warning_pct else "INFO"
            if severity != "INFO":
                out.append(Anomaly(metric=metric, baseline=baseline, current=current, percentage_change=round(pct, 2), severity=severity,
                                   evidence=[f"median baseline from {len(vals)} prior samples"]))
        return out

    def persist(self, report):
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / f"{report.cluster}.jsonl").open("a") as f:
            f.write(report.model_dump_json() + "\n")

from __future__ import annotations
from ..models import Issue, Confidence

def correlate(report, warning_events):
    issues = []

    if report.nodes.get("NotReady", 0):
        issues.append(Issue(
            severity="CRITICAL", resource="nodes",
            observation=f'{report.nodes["NotReady"]} node(s) are NotReady',
            evidence=["Kubernetes node Ready condition is not True"],
            probable_cause="Node-level failure or loss of control-plane/kubelet connectivity requires investigation",
            confidence=Confidence.HIGH,
            recommended_actions=["Describe affected nodes", "Review kubelet/node infrastructure health", "Check EC2 and node-group status"]
        ))

    bad = report.pods.get("reasons", {})
    bad_total = sum(bad.get(x, 0) for x in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"))
    if bad_total or report.pods.get("oom_killed", 0):
        evidence = [f"pod waiting reasons={bad}", f'OOMKilled={report.pods.get("oom_killed", 0)}']
        issues.append(Issue(
            severity="DEGRADED" if not report.nodes.get("NotReady", 0) else "CRITICAL",
            resource="pods", observation="Unhealthy pod/container states detected",
            evidence=evidence,
            probable_cause="Workload-specific failure; logs, events, image access, and resource limits must be correlated",
            confidence=Confidence.MEDIUM,
            recommended_actions=["Inspect pod describe/events", "Collect current and previous container logs", "Check requests/limits and HPA"]
        ))

    pending = report.pods.get("phases", {}).get("Pending", 0)
    scaled_hpas = [h for h in report.autoscaling.get("hpa", []) if (h.get("desired_replicas") or 0) > (h.get("current_replicas") or 0)]
    node_anom = next((a for a in report.anomalies if a.metric == "node_count" and (a.percentage_change or 0) > 0), None)
    if pending and (scaled_hpas or node_anom):
        chain = []
        if scaled_hpas: chain.append("HPA desired replicas exceed current replicas")
        chain.append(f"{pending} pod(s) Pending")
        if node_anom: chain.append(f"node count increased {node_anom.percentage_change}% vs baseline")
        issues.append(Issue(
            severity="DEGRADED", resource="autoscaling",
            observation="Scaling activity correlates with Pending pods",
            evidence=chain,
            probable_cause="Application demand may have increased replicas and triggered capacity scaling; verify Cluster Autoscaler/node-group events before treating as incident",
            confidence=Confidence.MEDIUM,
            recommended_actions=["Check HPA metrics and events", "Check Cluster Autoscaler logs/events", "Check node-group desired/current capacity", "Compare request rate and CPU/memory"]
        ))

    if warning_events and not issues:
        issues.append(Issue(
            severity="DEGRADED", resource="kubernetes-events",
            observation=f"{len(warning_events)} recent Warning event(s) found",
            evidence=[f'{e.get("reason")}: {e.get("object")}' for e in warning_events[-10:]],
            probable_cause="Warning events require workload-specific correlation",
            confidence=Confidence.LOW,
            recommended_actions=["Review warning event messages and affected objects"]
        ))
    return issues

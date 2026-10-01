from __future__ import annotations

def render_health(report) -> str:
    lines = [
        "EKS HEALTH SUMMARY",
        f"Cluster: {report.cluster}",
        f"Environment: {report.environment}",
        f"Region: {report.region}",
        f"Overall Health: {report.overall_health}",
        f"Kubernetes Version: {report.kubernetes_version}",
        f"Nodes: {report.nodes}",
        f"Pods: {report.pods}",
        f"Active alarms: {len(report.active_alarms)}",
        f"Anomalies: {len(report.anomalies)}",
        f"Detected issues: {len(report.detected_issues)}",
        f"Production action status: {report.production_action_status}",
    ]
    return "\n".join(lines)

def render_incident(report) -> str:
    issue = report.detected_issues[0] if report.detected_issues else None
    if not issue:
        return render_health(report) + "\n\nNo active incident identified from collected evidence."
    return f"""INCIDENT SUMMARY

Cluster: {report.cluster}
Environment: {report.environment}
Severity: {issue.severity}
Affected Resource: {issue.resource}

OBSERVATIONS
{issue.observation}

EVIDENCE
""" + "\n".join(f"- {x}" for x in issue.evidence) + f"""

PROBABLE ROOT CAUSE
{issue.probable_cause}

CONFIDENCE
{issue.confidence}

TROUBLESHOOTING STEPS
""" + "\n".join(f"- {x}" for x in issue.recommended_actions) + """

RECOMMENDED REMEDIATION
No write operation is automatically executed. Any remediation requiring a production change must be proposed with target, impact, rollback, and explicit human approval.

RISK
Changing production resources without validated RCA can increase blast radius.

PRODUCTION ACTION STATUS
READ-ONLY: no production changes executed
"""

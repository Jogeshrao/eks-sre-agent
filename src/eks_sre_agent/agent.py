from __future__ import annotations
import os, shlex
from pathlib import Path
from .models import HealthReport, Health
from .command import CommandRunner
from .collectors.kubernetes import KubernetesCollector
from .collectors.aws import AWSCollector
from .analysis.anomaly import AnomalyDetector
from .analysis.correlation import correlate

class EKSAgent:
    def __init__(self, config, reports_dir="reports"):
        self.cfg = config
        self.r = CommandRunner()
        self.reports = Path(reports_dir)

    def connect_and_verify(self):
        template = os.getenv("KCONNECT_TEMPLATE", "kconnect --context {kconnect_context} --service-account {service_account}")
        cmd = template.format(
            kconnect_context=self.cfg.kconnect_context,
            service_account=self.cfg.service_account,
            cluster_name=self.cfg.cluster_name,
            region=self.cfg.region,
        )
        argv = shlex.split(cmd)
        # Normalize executable basename for safety policy if wrapper is a full path.
        self.r.run(argv, timeout=120)

        current = self.r.run(["kubectl", "config", "current-context"]).stdout.strip()
        if current != self.cfg.expected_kube_context:
            raise RuntimeError(f"Context verification failed. Expected {self.cfg.expected_kube_context!r}, got {current!r}")

        aws = AWSCollector(self.cfg.region)
        identity = aws.identity()
        if identity["Account"] != self.cfg.aws_account:
            raise RuntimeError("AWS account verification failed")

        eks = aws.eks_cluster(self.cfg.cluster_name)
        if eks["name"] != self.cfg.cluster_name:
            raise RuntimeError("EKS cluster identity verification failed")
        return aws, eks

    def collect(self):
        aws, eks = self.connect_and_verify()
        k = KubernetesCollector(self.r, self.cfg.namespace)
        workloads = k.workloads()
        report = HealthReport(
            cluster=self.cfg.cluster_name,
            environment=self.cfg.environment,
            aws_account=self.cfg.aws_account,
            region=self.cfg.region,
            kubernetes_version=k.version() or eks.get("version"),
            nodes=k.nodes(),
            pods=k.pods(),
            deployments=workloads["deployments"],
            statefulsets=workloads["statefulsets"],
            daemonsets=workloads["daemonsets"],
            autoscaling=k.autoscaling(),
            networking=k.networking(),
            storage=k.storage(),
            aws_infrastructure=aws.infrastructure(self.cfg.cluster_name),
            resource_utilization=k.utilization(),
            active_alarms=aws.alarms(),
        )

        detector = AnomalyDetector(str(self.reports / "history"))
        report.anomalies = detector.detect(report)
        warnings = k.warning_events()
        report.detected_issues = correlate(report, warnings)

        critical = any(i.severity == "CRITICAL" for i in report.detected_issues) or any(a.severity == "CRITICAL" for a in report.anomalies)
        degraded = bool(report.detected_issues or report.anomalies or report.active_alarms)
        report.overall_health = Health.CRITICAL if critical else Health.DEGRADED if degraded else Health.HEALTHY
        report.probable_causes = list(dict.fromkeys(i.probable_cause for i in report.detected_issues))
        report.recommended_actions = list(dict.fromkeys(x for i in report.detected_issues for x in i.recommended_actions))
        detector.persist(report)
        return report

    def save(self, report):
        self.reports.mkdir(parents=True, exist_ok=True)
        p = self.reports / f"{report.cluster}-latest.json"
        p.write_text(report.model_dump_json(indent=2))
        return p

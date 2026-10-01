# EKS Production Support & SRE Agent

A read-only-by-default EKS operations agent for cluster health checks, incident investigation, anomaly detection, correlation, JSON reporting, and email alerting.

## Safety model

The monitoring path only permits Kubernetes read verbs/commands: `get`, `list`, `watch`, `describe`, `logs`, and `top`.

Write operations such as `delete`, `patch`, `edit`, `apply`, `replace`, `rollout`, `scale`, `drain`, `cordon`, `uncordon`, AWS terminate/modify/update, etc. are blocked by the command guard. Remediation is proposed as text and requires a separate human-approved workflow.

The service account and IAM role should also enforce read-only permissions. Application-side blocking is not a substitute for RBAC/IAM.

## Architecture

```text
clusters.json
    |
Inventory Loader
    |
kconnect -> Context/Account/Region Guard
    |
    +---------------- Kubernetes collectors ----------------+
    | nodes | pods | workloads | HPA | events | storage     |
    +--------------------------------------------------------+
    |
    +---------------- AWS collectors ------------------------+
    | EKS | EC2 | ASG | ELBv2 | CloudWatch                 |
    +--------------------------------------------------------+
    |
Normalizer -> Correlation/RCA -> Anomaly Detector
    |
Health Evaluator
    |
    +--> Human-readable incident/health summary
    +--> JSON health report
    +--> Alert de-duplication
    +--> Email (SMTP or adapter)
```

## Repository layout

```text
eks-sre-agent/
├── config/clusters.example.json
├── src/eks_sre_agent/
│   ├── agent.py
│   ├── cli.py
│   ├── command.py
│   ├── inventory.py
│   ├── models.py
│   ├── safety.py
│   ├── collectors/
│   │   ├── kubernetes.py
│   │   └── aws.py
│   ├── analysis/
│   │   ├── anomaly.py
│   │   └── correlation.py
│   └── reporting/
│       ├── emailer.py
│       └── renderer.py
├── tests/
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml
```

## Quick start

Requirements: Python 3.11+, AWS CLI, kubectl, your approved `kconnect` binary/script, AWS credentials through your enterprise authentication flow, and Kubernetes Metrics Server for `kubectl top`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp config/clusters.example.json config/clusters.json
# Edit inventory with real NON-SECRET metadata.

eks-sre-agent health --inventory config/clusters.json --cluster payments-prod
eks-sre-agent incident --inventory config/clusters.json --cluster payments-prod
```

Reports are written under `reports/`.

## kconnect integration

Organizations implement `kconnect` differently. Set `KCONNECT_TEMPLATE` rather than hard-coding credentials.

Example only:

```bash
export KCONNECT_TEMPLATE='kconnect --context {kconnect_context} --service-account {service_account}'
```

The agent substitutes only inventory metadata, invokes kconnect, then validates:
1. current kubectl context
2. EKS cluster identity
3. AWS account
4. AWS region
5. environment metadata

If identity verification fails, collection stops.

## Email

For SMTP:

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=...
export SMTP_PASSWORD=...
export SMTP_FROM=eks-sre@example.com
```

Do not place SMTP passwords in the inventory or Git.

For AWS SES or an enterprise mail API, replace `reporting/emailer.py` with an approved adapter.

## Scheduling

Run from Jenkins, GitHub Actions self-hosted runners, Kubernetes CronJobs, or your enterprise scheduler. The execution environment must have network access to the private EKS endpoint and approved AWS APIs.

Example cron:

```cron
*/15 * * * * /opt/eks-agent/.venv/bin/eks-sre-agent health --inventory /etc/eks-agent/clusters.json --all --email
```

## Anomaly baseline

This starter uses rolling report history from `reports/history/<cluster>.jsonl`. Production deployments should use CloudWatch/Prometheus historical queries and define per-metric windows, seasonality, minimum sample counts, and thresholds.

Default starter rule:
- baseline = median of prior samples
- percent change = `(current - baseline) / baseline * 100`
- warning threshold = 25%
- critical threshold = 50%
- minimum baseline samples = 4

Normal autoscaling is not automatically treated as an incident. Correlation checks demand, HPA, pending pods, node count, and AWS capacity before assigning severity.

## Recommended production hardening

- Kubernetes `view`/custom read-only ClusterRole with no Secret read access.
- IAM role limited to Describe/List/GetMetricData/GetMetricStatistics APIs.
- Explicit account/region allowlists.
- Private runner inside approved network boundaries.
- Secrets in Secrets Manager or enterprise vault.
- Immutable audit logs for every tool invocation.
- CloudWatch/Prometheus baselines instead of local history.
- Alert fingerprint + TTL/state store for deduplication.
- Change/deployment metadata from Argo CD, GitHub, Jenkins, or your deployment platform.
- Separate approval service for remediation. Never add write permissions to the monitoring service account.

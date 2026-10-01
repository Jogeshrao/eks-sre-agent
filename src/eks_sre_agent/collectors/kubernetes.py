from __future__ import annotations
import json
from collections import Counter
from typing import Any
from ..command import CommandRunner

class KubernetesCollector:
    def __init__(self, runner: CommandRunner, namespace: str):
        self.r = runner
        self.namespace = namespace

    def _scope(self):
        return ["-A"] if self.namespace in {"all", "*"} else ["-n", self.namespace]

    def _json(self, args: list[str]) -> dict[str, Any]:
        return self.r.run(["kubectl", *args, "-o", "json"]).json()

    def version(self):
        raw = self.r.run(["kubectl", "version", "-o", "json"]).json()
        return raw.get("serverVersion", {}).get("gitVersion")

    def nodes(self):
        data = self._json(["get", "nodes"])
        counts = Counter()
        pressure = Counter()
        for n in data.get("items", []):
            conditions = {c["type"]: c["status"] for c in n.get("status", {}).get("conditions", [])}
            counts["Ready" if conditions.get("Ready") == "True" else "NotReady"] += 1
            for key in ("MemoryPressure", "DiskPressure", "PIDPressure"):
                if conditions.get(key) == "True":
                    pressure[key] += 1
        return {"total": len(data.get("items", [])), **counts, "pressure": dict(pressure)}

    def pods(self):
        data = self._json(["get", "pods", *self._scope()])
        phases, reasons = Counter(), Counter()
        restarts = 0
        oom = 0
        for p in data.get("items", []):
            phases[p.get("status", {}).get("phase", "Unknown")] += 1
            for cs in p.get("status", {}).get("containerStatuses", []):
                restarts += cs.get("restartCount", 0)
                waiting = cs.get("state", {}).get("waiting", {}).get("reason")
                terminated = cs.get("lastState", {}).get("terminated", {}).get("reason")
                if waiting:
                    reasons[waiting] += 1
                if terminated == "OOMKilled":
                    oom += 1
        return {"total": len(data.get("items", [])), "phases": dict(phases), "reasons": dict(reasons), "restarts": restarts, "oom_killed": oom}

    def workloads(self):
        out = {}
        for resource in ("deployments", "statefulsets", "daemonsets"):
            data = self._json(["get", resource, *self._scope()])
            unavailable = 0
            items = []
            for x in data.get("items", []):
                s = x.get("status", {})
                desired = s.get("replicas", s.get("desiredNumberScheduled", 0)) or 0
                ready = s.get("readyReplicas", s.get("numberReady", 0)) or 0
                unavailable += max(0, desired - ready)
                items.append({"namespace": x["metadata"].get("namespace"), "name": x["metadata"]["name"], "desired": desired, "ready": ready})
            out[resource] = {"count": len(items), "unavailable_replicas": unavailable, "items": items}
        return out

    def autoscaling(self):
        hpa = self._json(["get", "hpa", *self._scope()])
        items = []
        for x in hpa.get("items", []):
            s = x.get("status", {})
            items.append({
                "namespace": x["metadata"].get("namespace"), "name": x["metadata"]["name"],
                "current_replicas": s.get("currentReplicas"), "desired_replicas": s.get("desiredReplicas"),
                "last_scale_time": s.get("lastScaleTime")
            })
        return {"hpa": items}

    def networking(self):
        services = self._json(["get", "services", *self._scope()])
        ing = self._json(["get", "ingress", *self._scope()])
        ep = self._json(["get", "endpoints", *self._scope()])
        empty = []
        for x in ep.get("items", []):
            subsets = x.get("subsets") or []
            addresses = sum(len(s.get("addresses", [])) for s in subsets)
            if addresses == 0:
                empty.append(f'{x["metadata"].get("namespace")}/{x["metadata"]["name"]}')
        return {"services": len(services.get("items", [])), "ingress": len(ing.get("items", [])), "endpoints_without_ready_addresses": empty}

    def storage(self):
        pv = self._json(["get", "pv"])
        pvc = self._json(["get", "pvc", *self._scope()])
        pending = [f'{x["metadata"].get("namespace")}/{x["metadata"]["name"]}' for x in pvc.get("items", []) if x.get("status", {}).get("phase") != "Bound"]
        return {"persistent_volumes": len(pv.get("items", [])), "persistent_volume_claims": len(pvc.get("items", [])), "non_bound_pvcs": pending}

    def warning_events(self):
        data = self._json(["get", "events", *self._scope()])
        events = []
        for e in data.get("items", []):
            if e.get("type") == "Warning":
                events.append({
                    "namespace": e["metadata"].get("namespace"), "reason": e.get("reason"),
                    "message": e.get("message"), "object": e.get("involvedObject", {}).get("name"),
                    "last_timestamp": e.get("lastTimestamp") or e.get("eventTime")
                })
        return events[-100:]

    def utilization(self):
        node = self.r.run(["kubectl", "top", "nodes", "--no-headers"], check=False)
        pod = self.r.run(["kubectl", "top", "pods", *self._scope(), "--no-headers"], check=False)
        return {
            "node_top": node.stdout.splitlines() if node.returncode == 0 else [],
            "pod_top": pod.stdout.splitlines() if pod.returncode == 0 else [],
            "metrics_errors": [x for x in [node.stderr if node.returncode else "", pod.stderr if pod.returncode else ""] if x]
        }

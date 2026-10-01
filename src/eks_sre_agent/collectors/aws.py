from __future__ import annotations
from datetime import datetime, timezone, timedelta
import boto3

class AWSCollector:
    # boto3 clients are intentionally limited to read APIs in this class.
    def __init__(self, region: str):
        self.region = region
        self.eks = boto3.client("eks", region_name=region)
        self.ec2 = boto3.client("ec2", region_name=region)
        self.asg = boto3.client("autoscaling", region_name=region)
        self.elbv2 = boto3.client("elbv2", region_name=region)
        self.cw = boto3.client("cloudwatch", region_name=region)
        self.sts = boto3.client("sts", region_name=region)

    def identity(self):
        return self.sts.get_caller_identity()

    def eks_cluster(self, name: str):
        c = self.eks.describe_cluster(name=name)["cluster"]
        return {
            "name": c["name"], "arn": c["arn"], "version": c["version"], "status": c["status"],
            "endpoint_public_access": c.get("resourcesVpcConfig", {}).get("endpointPublicAccess"),
            "endpoint_private_access": c.get("resourcesVpcConfig", {}).get("endpointPrivateAccess")
        }

    def nodegroups(self, cluster: str):
        names = self.eks.list_nodegroups(clusterName=cluster).get("nodegroups", [])
        out = []
        for name in names:
            ng = self.eks.describe_nodegroup(clusterName=cluster, nodegroupName=name)["nodegroup"]
            sc = ng.get("scalingConfig", {})
            out.append({"name": name, "status": ng.get("status"), "min": sc.get("minSize"), "max": sc.get("maxSize"), "desired": sc.get("desiredSize")})
        return out

    def alarms(self):
        resp = self.cw.describe_alarms(StateValue="ALARM", MaxRecords=100)
        return [{"name": x["AlarmName"], "reason": x.get("StateReason"), "updated": str(x.get("StateUpdatedTimestamp"))} for x in resp.get("MetricAlarms", [])]

    def infrastructure(self, cluster: str):
        return {"eks": self.eks_cluster(cluster), "nodegroups": self.nodegroups(cluster)}

import json
from pathlib import Path
from .models import Inventory, ClusterConfig

def load_inventory(path: str) -> Inventory:
    return Inventory.model_validate(json.loads(Path(path).read_text()))

def get_cluster(inv: Inventory, name: str) -> ClusterConfig:
    for c in inv.clusters:
        if c.cluster_name == name:
            return c
    raise KeyError(f"Cluster not found in approved inventory: {name}")

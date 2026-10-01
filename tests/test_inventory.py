from eks_sre_agent.models import Inventory
def test_inventory_model():
    x = Inventory.model_validate({"clusters":[{
        "cluster_name":"c","environment":"prod","aws_account":"123","region":"us-east-1",
        "kconnect_context":"c","expected_kube_context":"c","service_account":"ro",
        "namespace":"all","team":"sre"
    }]})
    assert x.clusters[0].cluster_name == "c"

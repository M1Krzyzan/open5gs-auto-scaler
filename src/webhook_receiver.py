from typing import Optional

import yaml
from kubernetes import client, config
from fastapi import FastAPI, Request

app = FastAPI()

config.load_incluster_config()
v1 = client.CoreV1Api()
api_client = client.ApiClient()


@app.post("/alert")
async def receive_webhook(request: Request):
    payload = await request.json()
    """
    main logic of webhook receiver:
    - load file with scaling policy
    """
    if payload["alerts"][0]["status"] == "resolved":
        return {"status": "success"}

    amf_sessions = payload["alerts"][0]["values"]["A"]

    print("AMF_SESSIONS:", amf_sessions)

    if (upf_pod_name := get_upf_pod_name()) is None:
        print("No upf pod in cluster")

    with open("scaling_policy.yaml", "r") as file:
        data = yaml.safe_load(file)
        scaling_policy = data["scaling_policy"]

    scaling_policy = sorted(scaling_policy, key=lambda x: x["threshold"])

    cpu_limit = ""

    for policy in scaling_policy:
        if (threshold := policy.get("threshold")) is None:
            print("No threshold in policy")
            return {"status": "failure"}

        if threshold > amf_sessions:
            break

        if (resources := policy.get("resources")) is None:
            print("No resources in policy")
            return {"status": "failure"}

        if (cpu_limit := resources.get("cpu")) is None:
            print("No cpu limit in resources")
            return {"status": "failure"}

    current_cpu_limit = get_current_upf_cpu_limit(upf_pod_name)

    if current_cpu_limit == cpu_limit or cpu_limit == "":
        return {"status": "received"}

    scale_upf_pod(upf_pod_name, "200m")

    return {"status": "received"}


def get_upf_pod_name() -> Optional[str]:
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    for pod in pod_list.items:
        if pod.metadata.name.startswith("open5gs-upf"):
            return pod.metadata.name
    return None


def scale_upf_pod(upf_pod_name: str, cpu_limit: str):
    patch_body = {
        "spec": {
            "containers": [
                {
                    "name": "open5gs-upf",
                    "resources": {
                        "limits": {
                            "cpu": cpu_limit
                        }
                    }
                }
            ]
        }
    }

    response = api_client.call_api(
        f"/api/v1/namespaces/default/pods/{upf_pod_name}/resize",
        "PATCH",
        body=patch_body,
        header_params={"Content-Type": "application/strategic-merge-patch+json"},
        response_type="object",
        auth_settings=["BearerToken"]
    )
    containers = response[0].get("spec", {}).get("containers", [])
    cpu_limit_found = False
    for c in containers:
        limits = c.get("resources", {}).get("limits", {})
        if "cpu" in limits:
            cpu_limit_found = True
            print(f"Container '{c.get('name')}' CPU limit patched to: {limits['cpu']}")

    if not cpu_limit_found:
        print("No CPU limit found in the patched response.")



def get_current_upf_cpu_limit(upf_pod_name: str) -> Optional[str]:
    pod = v1.read_namespaced_pod(name = upf_pod_name,namespace = "default")
    containers = pod.spec.containers
    for container in containers:
        upf_cpu_limit = container.resources.limits.get("cpu")
        return upf_cpu_limit
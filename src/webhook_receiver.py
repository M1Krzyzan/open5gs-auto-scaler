import json
from typing import Optional

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
    - parse request body
    - get value of amf sessions
    - load file with scaling policy
    - get name of upf pod
    - create patch request to scale UPF pod
    """
    if payload["alerts"][0]["status"] == "resolved":
        return {"status": "success"}

    amf_sessions = payload["alerts"][0]["values"]["A"]

    print("AMF_SESSIONS:", amf_sessions)

    if (upf_pod_name := get_upf_pod_name()) is None:
        print("No upf pod in cluster")
    print(upf_pod_name)

    print(get_current_upf_cpu_limit(upf_pod_name))

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

    print("Resize response:", response)


def get_current_upf_cpu_limit(upf_pod_name: str) -> Optional[str]:
    pod = v1.read_namespaced_pod(name = upf_pod_name,namespace = "default")
    containers = pod.spec.containers
    for container in containers:
        upf_cpu_limit = container.resources.limits.get("cpu")
        return upf_cpu_limit
from fastapi import FastAPI, Request

app = FastAPI()

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
    return {"status":"received"}

def get_upf_pod_name() -> str:
    pass

def scale_upf_pod(upf_pod_name: str, cpu_limit: int):
    pass

def get_current_upf_cpu_limit() -> int:
    pass
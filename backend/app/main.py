from fastapi import FastAPI

app = FastAPI(title="PulseCheck")


@app.get("/health")
def health():
    return {"status": "ok"}

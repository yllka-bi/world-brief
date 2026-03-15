from typing import Any, Dict

from fastapi import FastAPI

app = FastAPI(title="World Brief API", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}

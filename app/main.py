"""API de comparação de documentos. Execute: uvicorn app.main:app --host 127.0.0.1 --port 8000"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from .core import MAX_FILE_BYTES, compare, extract_text

app = FastAPI(title="Conferência Documental", docs_url="/api/docs")
UI = Path(__file__).with_name("index.html")

@app.get("/")
def home():
    return FileResponse(UI)

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/compare")
async def compare_documents(files: list[UploadFile] = File(...)):
    if not 3 <= len(files) <= 20:
        raise HTTPException(400, "Selecione de 3 a 20 documentos")
    inputs = []
    for item in files:
        data = await item.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(413, f"Arquivo excede 20 MB: {item.filename}")
        inputs.append((Path(item.filename or "").name, data))
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(inputs))) as pool:
            documents = list(pool.map(lambda pair: extract_text(*pair), inputs))
        return compare(documents)
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc

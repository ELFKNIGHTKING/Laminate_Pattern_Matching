from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import shutil, uuid, os, json, time
from pathlib import Path

from model import get_image_embedding, is_laminate_image
from db import search_similar_laminates, insert_laminate_segment
from preprocessing import preprocess_image  # NEW: preprocessing import

# Path configuration

BASE_DIR     = Path(__file__).resolve().parent       # …/backend/python
PROJECT_ROOT = BASE_DIR.parent.parent                 # …/laminate-pattern-matching
PUBLIC_DIR   = PROJECT_ROOT / "public"
UPLOAD_DIR   = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ADMIN_UPLOADS_DIR = Path(r"C:/Users/katha/OneDrive/Desktop/Web Development/laminate-pattern-matching/admin_uploads")  # <-- Change this path to your actual folder

if not PUBLIC_DIR.exists():
    raise RuntimeError(f"Public directory not found at {PUBLIC_DIR}")
if not ADMIN_UPLOADS_DIR.exists():
    raise RuntimeError(f"Admin uploads directory not found at {ADMIN_UPLOADS_DIR}")

# FastAPI setup

app = FastAPI(
    docs_url="/supersecret123docs",  # Only you know this path
    redoc_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# API ROUTES

@app.get("/api")
def api_root():
    return {"message": "FastAPI backend is running."}

@app.post("/api/search")
async def search_laminate(file: UploadFile = File(...)):
    timer_total_start = time.time()

    if not file.filename:
        raise HTTPException(400, "File must have a filename")

    suffix = Path(file.filename).suffix
    temp_name = f"{uuid.uuid4().hex}{suffix}"
    temp_path = UPLOAD_DIR / temp_name

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # TIMER: Preprocessing
    timer_preproc_start = time.time()
    preproc_path = temp_path.with_name(temp_path.stem + "_preproc" + temp_path.suffix)
    preprocess_image(str(temp_path), str(preproc_path))
    timer_preproc_end = time.time()

    # TIMER: Embedding
    timer_embed_start = time.time()
    embedding = get_image_embedding(str(preproc_path))
    timer_embed_end = time.time()

    # TIMER: Database search
    timer_db_start = time.time()
    results = search_similar_laminates(embedding)
    timer_db_end = time.time()

    temp_path.unlink(missing_ok=True)
    preproc_path.unlink(missing_ok=True)

    timer_total_end = time.time()
    print(f"---- Search pipeline timing ----")
    print(f"Preprocessing: {timer_preproc_end - timer_preproc_start:.2f} s")
    print(f"Embedding:     {timer_embed_end - timer_embed_start:.2f} s")
    print(f"DB search:     {timer_db_end - timer_db_start:.2f} s")
    print(f"TOTAL:         {timer_total_end - timer_total_start:.2f} s")
    print(f"---------------------------------")

    return results

@app.post("/upload-laminate/")
async def upload_laminate(
    laminate_id: int = Form(...),              # Group ID for this laminate
    segment_num: int = Form(...),              # 0 = main, 1-12 = segments
    name: str = Form(...),
    color: str = Form(None),
    code: str = Form(None),
    metadata: str = Form('{}'),                # Pass as JSON string
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(400, "File must have a filename")

    suffix = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_DIR / stored_name

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # Preprocess before laminate detection & embedding
    preproc_path = save_path.with_name(save_path.stem + "_preproc" + save_path.suffix)
    preprocess_image(str(save_path), str(preproc_path))

    # Validate laminate pattern
    if not is_laminate_image(str(preproc_path)):
        save_path.unlink(missing_ok=True)
        preproc_path.unlink(missing_ok=True)
        return {"status": "rejected", "reason": "Not recognized as a laminate pattern."}

    # Compute embedding & insert into DB (on preprocessed image)
    embedding = get_image_embedding(str(preproc_path))
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    insert_laminate_segment(
        laminate_id,
        segment_num,
        stored_name,
        embedding,
        name,
        color,
        code,
        meta_dict
    )

    # DO NOT DELETE save_path (original image)
    # Only delete the preprocessed temp image
    preproc_path.unlink(missing_ok=True)

    return {
        "status":    "success",
        "laminate_id": laminate_id,
        "segment_num": segment_num,
        "image_url": f"/uploads/{stored_name}"
    }

# STATIC FILE MOUNTS (after API routes)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)
app.mount(
    "/admin_uploads",
    StaticFiles(directory=str(ADMIN_UPLOADS_DIR), html=True),
    name="admin_uploads"
)
app.mount(
    "/",
    StaticFiles(directory=str(PUBLIC_DIR), html=True),
    name="public"
)

import os
import re
import sys
import json
import pandas as pd

from pathlib import Path

# Import your project functions
sys.path.append(str(Path(__file__).resolve().parent))  # Ensure import works
from model import get_image_embedding, is_laminate_image
from db import insert_laminate_segment
from preprocessing import preprocess_image

# === CHANGES HERE: Add import for psycopg2 if using raw SQL ===
import psycopg2

# SETTINGS
IMAGE_FOLDER = "uploads"         # Folder with all your images
CSV_PATH = os.path.join(IMAGE_FOLDER, "metadata.csv")  # Optional: CSV with metadata
IMAGE_URL_PREFIX = "/uploads/"        # Where images will be accessible via API
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"  # Where to copy originals

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load CSV metadata if present
if os.path.exists(CSV_PATH):
    df_metadata = pd.read_csv(CSV_PATH)
else:
    df_metadata = pd.DataFrame()

def get_extra_metadata(laminate_id, segment_num):
    if df_metadata.empty:
        return None, None, {}
    row = df_metadata[
        (df_metadata['laminate_id'] == laminate_id) & 
        (df_metadata['segment_num'] == segment_num)
    ]
    if row.empty:
        return None, None, {}
    color = row['color'].values[0] if 'color' in row else None
    code = row['code'].values[0] if 'code' in row else None
    # Metadata column is assumed as a JSON string
    if 'metadata' in row and pd.notna(row['metadata'].values[0]):
        try:
            metadata = json.loads(row['metadata'].values[0])
        except Exception:
            metadata = {}
    else:
        metadata = {}
    return color, code, metadata

# === CHANGES HERE: Add function to check if image already exists ===
def laminate_exists_by_filename(filename):
    # Adjust connection and table/column names to your DB setup!
    try:
        conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="postgres",  # Change if your DB name is different
    user="postgres",
    password="Parth@123"
)
        cur = conn.cursor()
        # If you store just filename: (change column/table if needed)
        cur.execute("SELECT 1 FROM laminates WHERE image_url=%s LIMIT 1;", (filename,))
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"[laminate_exists_by_filename] DB error: {e}")
        return False

def main():
    files = sorted([f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith('.jpg')])

    if not files:
        print(f"No .jpg files found in {IMAGE_FOLDER}")
        return

    for filename in files:
        filepath = os.path.join(IMAGE_FOLDER, filename)
        # Expect: "5223 Volango Concreat 0.jpg"
        match = re.match(r'(\d+)\s+(.+)\s+(\d+)\.jpg$', filename)
        if not match:
            print(f"Skipping invalid filename: {filename}")
            continue

        laminate_id, name, segment_num = match.groups()
        laminate_id = int(laminate_id)
        segment_num = int(segment_num)

        # Step 1: Copy image to uploads folder for serving via /uploads
        dest_name = filename  # You may want to randomize or clean this if needed
        dest_path = UPLOAD_DIR / dest_name
        if not dest_path.exists():
            with open(filepath, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
        image_url = IMAGE_URL_PREFIX + dest_name

        # === CHANGES HERE: SKIP IF ALREADY IN DB ===
        if laminate_exists_by_filename(dest_name):
            print(f"[{filename}] Skipped: already exists in DB.")
            continue

        # Step 2: Preprocess image for model input
        preproc_path = str(dest_path.with_name(dest_path.stem + "_preproc" + dest_path.suffix))
        try:
            preprocess_image(str(dest_path), preproc_path)
        except Exception as e:
            print(f"[{filename}] Failed preprocessing: {e}")
            continue

        # Step 4: Embedding
        try:
            embedding = get_image_embedding(preproc_path)
        except Exception as e:
            print(f"[{filename}] Failed embedding: {e}")
            os.remove(preproc_path)
            continue
        finally:
            os.remove(preproc_path)

        # Step 5: Metadata
        color, code, metadata = get_extra_metadata(laminate_id, segment_num)

        # Step 6: Insert into DB
        try:
            insert_laminate_segment(
                laminate_id,
                segment_num,
                dest_name,
                embedding,
                name,
                color,
                code,
                metadata
            )
            print(f"[{filename}] Inserted successfully.")
        except Exception as e:
            print(f"[{filename}] Failed DB insert: {e}")

if __name__ == "__main__":
    main()

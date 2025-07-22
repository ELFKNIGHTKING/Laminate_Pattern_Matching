import psycopg2
from pgvector.psycopg2 import register_vector
import os
import json

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="postgres",  # Change if your DB name is different
    user="postgres",
    password="Parth@123"
)

# Register pgvector support
register_vector(conn)

def insert_laminate_segment(
    laminate_id, segment_num, image_url, embedding, name, color, code, metadata
):
    """Insert one laminate segment (or main image) with full metadata."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO laminates
            (laminate_id, segment_num, image_url, embedding, name, color, code, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (laminate_id, segment_num, image_url, embedding, name, color, code, json.dumps(metadata))
        )
        conn.commit()

def insert_laminate_with_segments(
    laminate_id, main_image, main_embedding, segments, name, color, code, metadata
):
    """
    Insert a main image and its segments for a laminate.
    segments: List of tuples [(segment_image, segment_embedding), ...]
    """
    # Insert main image (segment_num = 0)
    insert_laminate_segment(
        laminate_id, 0, main_image, main_embedding, name, color, code, metadata
    )

    # Insert segments (segment_num = 1 to N)
    for idx, (seg_image, seg_embedding) in enumerate(segments, start=1):
        insert_laminate_segment(
            laminate_id, idx, seg_image, seg_embedding, name, color, code, metadata
        )

def search_similar_laminates(query_embedding, threshold=0.8, topn=5):
    """
    Search all images for similar embeddings, group by laminate_id,
    but always return the main image (segment_num=0) for each matched laminate.
    The similarity is based on the best segment/main image for that laminate.
    """
    with conn.cursor() as cur:
        # First, get best matches (main or segment) for each laminate_id
        cur.execute("""
            SELECT laminate_id, name, color, code, image_url, segment_num, 1 - (embedding <=> %s::vector) AS similarity
            FROM laminates
            WHERE (embedding <=> %s::vector) <= %s
            ORDER BY embedding <=> %s::vector
            LIMIT 50
        """, (query_embedding, query_embedding, 1 - threshold, query_embedding))
        results = cur.fetchall()

        # For each laminate_id, keep only the highest similarity match
        seen = {}
        for r in results:
            lam_id = r[0]
            if lam_id not in seen or r[6] > seen[lam_id][6]:
                seen[lam_id] = r

        # Now, for each matched laminate_id, fetch the main image (segment_num=0)
        main_images = []
        for lam_id, match_row in seen.items():
            cur.execute("""
                SELECT laminate_id, name, color, code, image_url, segment_num
                FROM laminates
                WHERE laminate_id = %s AND segment_num = 0
                LIMIT 1
            """, (lam_id,))
            main_row = cur.fetchone()
            if main_row:
                main_images.append({
                    "laminate_id": main_row[0],
                    "name": main_row[1],
                    "color": main_row[2],
                    "code": main_row[3],
                    "image_url": main_row[4],
                    "segment_num": main_row[5],  # should always be 0
                    "similarity": round(match_row[6], 3)  # use similarity from best segment/main match
                })

        # Sort by similarity descending and return top N
        main_images.sort(key=lambda x: -x["similarity"])
        return main_images[:topn]

# Optional: For backward compatibility
def insert_laminate(name, image_url, embedding):
    # Uses segment_num = 0, laminate_id = -1 for "old style"
    insert_laminate_segment(-1, 0, image_url, embedding, name, None, None, {})

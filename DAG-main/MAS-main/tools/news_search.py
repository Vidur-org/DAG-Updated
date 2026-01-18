import json
import numpy as np
import ijson
from sentence_transformers import SentenceTransformer
from dateutil import parser as dateparser
from datetime import datetime
from abc import ABC, abstractmethod
import json
from typing import Dict, List, Any
import json
from tqdm import tqdm
from abc import ABC, abstractmethod
from pathlib import Path

def News_Search(query: str, start_date: str, end_date: str, top_k: int):
# -----------------------------
# Load data
# -----------------------------
    JSON_FILE = Path(__file__).parent.parent / "merged_sorted_embeddings.json"
    print("Loading embedded data...")
    # try:
    #     with open(JSON_FILE, "r", encoding="utf-8") as f:
    #         docs = json.load(f)
    # except Exception as e:
    #     print(f"❌ Error loading {JSON_FILE}: {e}")
    #     return [],0
    # print(f"✅ Loaded {len(docs)} documents with embeddings")
    # -----------------------------
    # Parse date range (once)
    # -----------------------------
    start_dt = dateparser.parse(start_date).replace(tzinfo=None)
    end_dt   = dateparser.parse(end_date).replace(tzinfo=None)

    filtered_docs = []
    filtered_embs = []

    # -----------------------------
    # Filter documents by date
    # -----------------------------
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Filtering documents from {start_date} to {end_date}...")
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        for doc in tqdm(
                ijson.items(f, "item"),
                desc="📄 Scanning News",
                unit=" articles"
            ):
            
            if not isinstance(doc, dict):
                continue
            pub = doc.get("publish_date")
            emb = doc.get("embedding")

            if not pub or not emb:
                continue

            dt = dateparser.parse(pub)
            if dt.tzinfo is not None:
                dt = dt.astimezone(None).replace(tzinfo=None)

            if start_dt <= dt <= end_dt:
                filtered_docs.append(doc)
                filtered_embs.append(emb)

    if not filtered_docs:
        print("❌ No documents found in the given date range")
        return [], 0


    print(f"✅ Documents after date filter: {len(filtered_docs)}")
    
    # If very few documents, print warning
    if len(filtered_docs) < 10:
        print(f"⚠️  Warning: Only {len(filtered_docs)} articles found in date range. Search results may be limited.")

    # -----------------------------
    # Convert embeddings → NumPy
    # -----------------------------
    filtered_embs = np.array(filtered_embs, dtype="float32")

    # Normalize embeddings (for cosine similarity)
    filtered_embs /= (
        np.linalg.norm(filtered_embs, axis=1, keepdims=True) + 1e-12
    )
    print("✅ Normalized embeddings for semantic search")
    # -----------------------------
    # Query embedding
    # -----------------------------
    

    q_emb = model.encode(query, convert_to_numpy=True).astype("float32")
    q_emb /= (np.linalg.norm(q_emb) + 1e-12)

    # -----------------------------
    # Semantic Search
    # -----------------------------
    scores = filtered_embs @ q_emb   # cosine similarity
    top_idx = np.argsort(-scores)[:top_k]
    if(len(top_idx)==0):
        return [],0
    top_score = scores[top_idx[0]]
    print(f"✅ Retrieved top {top_k} results for the query.")
    # --------p---------------------
    # Print results
    # -----------------------------
    print("\n🔎 Top Results\n" + "-" * 60)
    docs=[]

    for rank, idx in enumerate(top_idx, start=1):
        doc=filtered_docs[idx]
        docs.append(doc)
        # top5.append(doc)
        print(f"\nRank {rank} | Score: {scores[idx]:.4f}")
        print("Title:", doc["title"])
        print("Date :", doc["publish_date"])
        print("URL  :", doc["url"])
        print("Summary:", doc["summary"][:350])
    return docs, top_score
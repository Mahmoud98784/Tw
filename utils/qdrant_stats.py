import requests
import os

QDRANT_URL = os.getenv("QDRANT_URL")
COLLECTION = os.getenv("QDRANT_COLLECTION_NAME")

def get_qdrant_statistics():
    resp = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
    data = resp.json()

    total_points = data["result"]["points_count"]

    # Handle both old and new Qdrant versions
    vector_size = None
    if "vectors" in data["result"]:
        vector_size = data["result"]["vectors"]["size"]
    elif "vector_config" in data["result"]:
        # vector_config is a dict keyed by vector name
        first_key = list(data["result"]["vector_config"].keys())[0]
        vector_size = data["result"]["vector_config"][first_key]["size"]

    # Example: fetch labels distribution
    query = {
        "limit": 1000,
        "with_payload": True
    }
    resp = requests.post(f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll", json=query)
    points = resp.json()["result"]["points"]

    labels = [p["payload"].get("label", "unknown") for p in points]
    distribution = {}
    for l in labels:
        distribution[l] = distribution.get(l, 0) + 1

    return {
        "total_points": total_points,
        "avg_dim": vector_size,
        "unique_labels": len(set(labels)),
        "label_distribution": distribution
    }
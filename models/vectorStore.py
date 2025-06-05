from langchain.schema import Document
from langchain_community.vectorstores import Qdrant
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

import uuid
import time
from datetime import datetime

class QdrantVectorStoreClient:
    def __init__(
        self,
        url: str,
        api_key: str,
        collection: str,
        google_api_key: str,
        prefer_grpc: bool = False,
    ):
        """
        url: the full HTTPS URL (no :6333) for Qdrant Cloud, e.g.
             "https://<YOUR-CLOUD-ID>.gcp.cloud.qdrant.io"
        api_key: your Qdrant Cloud API key
        collection: the name of the Qdrant collection to create/use
        google_api_key: your Google Generative AI key for embeddings
        prefer_grpc: if True, attempt gRPC; if False, force HTTP
        """
        # Force REST (HTTP) rather than gRPC; Cloud endpoints respond on default HTTPS port (443).
        self.client = QdrantClient(
            url=url,
            api_key=api_key or None,
            prefer_grpc=prefer_grpc
        )

        # Check if the collection already exists
        existing = [c.name for c in self.client.get_collections().collections]
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

        # Initialize Google Generative AI embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )
        # Wrap Qdrant with LangChain’s vectorstore
        self.vs = Qdrant(
            client=self.client,
            collection_name=collection,
            embeddings=self.embeddings
        )

    def add_documents(self, items: list[dict]) -> list[str]:
        """
        items: list of dicts, each representing a “property” or “item”
        Returns: list of inserted document IDs
        """
        if not items:
            return []

        docs: list[Document] = []
        for item in items:
            # Use provided "id" or generate a new UUID
            prop_id = item.get("id") or str(uuid.uuid4())

            # Flatten item into a single string (only scalar fields, plus JSON dumps for non-scalars)
            # If you want to include nested structures as JSON, do that here.
            raw_lines = []
            for k, v in item.items():
                if isinstance(v, (str, int, float)):
                    raw_lines.append(f"{k}: {v}")
                else:
                    # For lists or dicts, serialize to JSON-like string
                    raw_lines.append(f"{k}: {v}")
            raw_text = "\n".join(raw_lines).strip()
            if not raw_text:
                continue

            # Create a single Document containing the entire raw_text
            doc = Document(
                page_content=raw_text,
                metadata={
                    "id": f"{prop_id}_0",
                    "property_id": prop_id,
                    "chunk_id": 0,
                    "upload_time": datetime.utcnow().isoformat(),
                }
            )
            docs.append(doc)

        return self._retry_add(docs)

    def _retry_add(self, documents: list[Document], max_retries: int = 5) -> list[str]:
        """
        Retry logic for rate‐limit or overload errors.
        """
        retries = 0
        while True:
            try:
                inserted_ids = self.vs.add_documents(documents)
                return inserted_ids
            except Exception as e:
                err = str(e).upper()
                if any(tok in err for tok in ["429", "RATE_LIMIT", "QUOTA", "OVERLOADED"]):
                    if retries < max_retries:
                        wait = 2**retries + 2
                        time.sleep(wait)
                        retries += 1
                        continue
                raise RuntimeError(f"Unable to add documents: {e}")

    def similarity_search(self, query: str, k: int = 5) -> list[dict]:
        """
        Return up to k nearest‐neighbor documents (with scores) for the given query.
        """
        results = self.vs.similarity_search_with_score(query, k=k)
        out = []
        for doc, score in results:
            out.append({
                "id": doc.metadata.get("id"),
                "property_id": doc.metadata.get("property_id"),
                "score": score,
                "metadata": doc.metadata,
                "content": doc.page_content
            })
        return out


if __name__ == "__main__":
    # ——— Example instantiation for Qdrant Cloud ———
    vector_store = QdrantVectorStoreClient(
        url="https://886d811f-9d2e-41a5-8043-7354789c11a3.europe-west3-0.gcp.cloud.qdrant.io",
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.w1474GJFXKREKXNFYEAQ_bMQ1HT3tKynM969KGHysi4",
        collection="sample",
        google_api_key="AIzaSyCmnhXgfxSw8iDPFsR9rm14Q8KFxntvUvk",
        prefer_grpc=False
    )

    # ——— Sample item (as a Python dict) to insert into “sample” collection ———
    example_item = {
        "property_name": "1RK Apartment in Sector 57",
        "property_location": "Sector 57",
        "property_summary": (
            "A fully furnished 1RK apartment in Sector 57 with modern appliances and amenities.  "
            "Features include a combined living and dining area, 2 bedrooms, and 2 bathrooms. "
            "Rent is ₹20,000."
        ),
        "rooms": [
            "kitchen", "living room", "bedroom", "bedroom_2",
            "bathroom", "bathroom_2"
        ],
        "appliances": {
            "fridge": 2,
            "fan": 2,
            "microwave": 2,
            "bed": 3,
            "sofa": 2,
            "air conditioner": 3,
            "tv": 2,
            "washing machine": 2,
            "tables": 2,
            "chairs": 8,
            "oven": 2,
            "stove": 1,
            "dishwasher": 1,
            "toilet": 2,
            "shower": 2,
            "washbasin": 2
        },
        "key_features": [
            "high ceilings",
            "wooden floor",
            "tile flooring",
            "large windows",
            "built-in wardrobes"
        ],
        "amenities": [
            "Wifi",
            "RO water purifier",
            "Power backup",
            "24hrs High Advance Security",
            "balcony",
            "Fully furnished"
        ],
        "layout_and_condition": (
            "The apartment features a combined living and dining area adjacent to the kitchen. "
            "Two bedrooms and two bathrooms are located in a separate wing, accessible via a hallway.  "
            "Good overall condition with minor signs of wear in some areas. Natural light is adequate "
            "in most rooms, though somewhat limited in the bedrooms. Space utilization is efficient. "
            "Ventilation appears sufficient."
        ),
        "location_insights": "Information not available",
        "rules_and_restrictions": "21 Days Brokerage",
        "contact_info": "Not specified",
        "additional_info": "Jain properties",
        "rent": "20,000"
    }

    # Wrap it in a list and add to the vector store; this will create one document per item
    # inserted_ids = vector_store.add_documents([example_item])
    # print(f"Inserted document IDs: {inserted_ids}")

    # # ——— (Optional) Example similarity search to verify insertion ———
    query = "Fully furnished apartment with modern appliances and amenities"
    results = vector_store.similarity_search(query, k=3)
    for idx, res in enumerate(results, start=1):
        print(f"\nResult #{idx}:")
        print(f"  ID: {res['id']}")
        print(f"  Score: {res['score']}")
        snippet = res['content']
        print(f"  Content snippet: {snippet[:100]}...")

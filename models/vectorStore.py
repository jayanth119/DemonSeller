import time
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

class QdrantVectorStore:
    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: str,
        collection_name: str,
        google_api_key: str
    ):
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.collection_name = collection_name
        self.google_api_key = google_api_key

        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            timeout=30.0
        )

        # Initialize embedding model
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=self.google_api_key
        )

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Ensure collection exists
        self.ensure_collection()

        # Initialize LangChain Qdrant wrapper
        self.vector_store = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding_model,
        )

    def ensure_collection(self):
        """Ensure the collection exists, create if it doesn't"""
        try:
            collections = self.qdrant_client.get_collections().collections
            names = [col.name for col in collections]
            if self.collection_name not in names:
                self.logger.info(f"Creating collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                self.logger.info(f"Collection {self.collection_name} created")
            else:
                self.logger.info(f"Collection {self.collection_name} exists")
        except Exception as e:
            self.logger.error(f"Error ensuring collection: {e}")
            raise

    def add_documents(self, items: List[Dict[str, Any]]) -> List[str]:
        """Add a batch of property items to Qdrant with all JSON fields in content and metadata."""
        if not items:
            self.logger.warning("No items to add")
            return []

        docs = []
        for item in items:
            prop_id = item.get("id") or str(uuid.uuid4())
            upload_time = datetime.utcnow().isoformat()

            # Flatten and stringify key fields
            content_parts = []

            for key, value in item.items():
                if isinstance(value, dict):
                    content_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                elif isinstance(value, list):
                    content_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    content_parts.append(f"{key}: {value}")

            page_content = "\n".join(content_parts)

            # Store the whole item as metadata (limit Qdrant’s max metadata size if necessary)
            metadata = {
                "id": prop_id,
                "upload_time": upload_time,
                "raw_data": json.dumps(item, ensure_ascii=False)
            }

            doc = Document(page_content=page_content, metadata=metadata)
            docs.append(doc)

        return self._retry_add(docs)


    def _retry_add(self, documents: List[Document], max_retries: int = 5) -> List[str]:
        retries = 0
        while retries < max_retries:
            try:
                ids = self.vector_store.add_documents(documents)
                return ids
            except Exception as e:
                err = str(e).upper()
                self.logger.error(f"Add attempt {retries+1} failed: {e}")
                if any(k in err for k in ["429", "RATE_LIMIT", "QUOTA"]):
                    wait = 2**retries + 5
                    time.sleep(wait)
                    retries += 1
                else:
                    raise
        raise RuntimeError(f"Failed after {max_retries} retries")

    def search_by_text(self, query: str, k: int = 5, filter: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Similarity search using a text query."""
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k, filter=filter)
            return [self._format_result(doc, score) for doc, score in results]
        except Exception as e:
            self.logger.error(f"search_by_text error: {e}")
            return []

    def search_by_filters(self, filters: Dict[str, Any], k: int = 5) -> List[Dict[str, Any]]:
        """Convert filter dict to text and search."""
        query = json.dumps(filters, ensure_ascii=False)
        return self.search_by_text(query, k=k)

    def _format_result(self, doc: Document, score: float) -> Dict[str, Any]:
        return {
            "id": doc.metadata.get("id"),
            "score": score,
            "distance": 1 - score,
            "metadata": doc.metadata,
            "page_content": doc.page_content
        }

    def health_check(self) -> bool:
        try:
            cols = self.qdrant_client.get_collections().collections
            return any(col.name == self.collection_name for col in cols)
        except Exception:
            return False


if __name__ == "__main__":
    # Example usage
    store = QdrantVectorStore(
        qdrant_url="https://886d811f-9d2e-41a5-8043-7354789c11a3.europe-west3-0.gcp.cloud.qdrant.io:6333",
        qdrant_api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.LCM5Vdz80er3DdIf8Mk6qGIKr3xF9MgyNcKpYup3TWA",
        collection_name="sample",
        google_api_key="AIzaSyCjz77h8Q3s3sa9XFx4jWm9qNio23ttxe8"
    )

    # Example property item
    property_item = {
  "property_name": "Modern 1RK Apartment",
  "property_location": "Sector 57",
  "property_summary": "This is a well-maintained, fully furnished 1RK apartment located in Sector 57. The estimated price is ₹20,000.",
  "rooms": [
    "Room",
    "Living Room",
    "Kitchen",
    "Bedroom",
    "Bathroom"
  ],
  "appliances": {
    "fridge": 2,
    "microwave": 2,
    "oven": 2,
    "stove": 2,
    "dishwasher": 1,
    "bed": 4,
    "sofa": 2,
    "tv": 3,
    "washing machine": 1,
    "dining table": 1,
    "chairs": 8,
    "coffee table": 1,
    "air conditioner": 2,
    "table": 1
  },
  "key_features": [
    "Modern kitchen",
    "RO water system",
    "Balcony",
    "City view",
    "Hardwood floors",
    "Walk-in closet",
    "Fully furnished",
    "Power backup",
    "WiFi"
  ],
  "amenities": [
    "RO water system",
    "Power backup",
    "Washing machine",
    "24hrs High Advance Security",
    "Fully furnished",
    "WiFi"
  ],
  "layout_and_condition": "The apartment features an open-plan living area that flows seamlessly into the modern kitchen. Bedrooms are separate from the living area, ensuring privacy. The bathroom is conveniently accessible from the hallway. The property is well-maintained and offers good use of space with ample natural light in the living areas and bedrooms.",
  "location_insights": "Location details are not available.",
  "rules_and_restrictions": "No specific rules or restrictions are mentioned.",
  "contact_info": "Jain properties",
  "additional_info": "21 Days Brokerage applicable.",
  "rent": "20000"
}


    added_ids = store.add_documents([property_item])
    print("Added document IDs:", added_ids)

    # # Example search
    # query = "Luxury apartment under 25000"
    # matches = store.search_by_text(query, k=3)
    # for match in matches:
    #     print("Match:", match)
    #     agent = PropertySearchAgent()

    # query = (
    #     "I want a 2BHK apartment with 2 ACs, a sofa, a balcony, "
    #     "under 25000 in Sector 35 with WiFi and inverter"
    # )

    # parsed_result = agent.search(query)
    # print("Parsed filter JSON:")
    # print(json.dumps(parsed_result, indent=2))
    
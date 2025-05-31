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
import logging

logger = logging.getLogger(__name__)

class QdrantVectorStoreClient:
    def __init__(self, url: str, api_key: str, collection: str, google_api_key: str):
        self.logger = logger
        self.client = QdrantClient(url=url, api_key=api_key)
        # ensure collection exists
        existing = [c.name for c in self.client.get_collections().collections]
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
        self.vs = Qdrant(
            client=self.client,
            collection_name=collection,
            embeddings=GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=google_api_key
            ),
        
        )
        

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform similarity search and return list of dicts with id, score, metadata, and content
        """
        results = self.vs.similarity_search_with_score(query, k=k)
        formatted = []
        for doc, score in results:
            formatted.append({
                "id": doc.metadata.get("id"),
                "score": score,
                "metadata": doc.metadata,
                "content": doc.page_content,
            })
        return formatted

    def _retry_add(self, documents: List[Document], max_retries: int = 5) -> List[str]:
        retries = 0
        while retries < max_retries:
            try:
                ids = self.vs.client.upload_collection(collection_name=self.vs.collection_name, documents=documents)
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

            # Store the whole item as metadata (limit Qdrant's max metadata size if necessary)
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
                ids = self.vs.add_documents(documents)
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


if __name__ == "__main__":
    # Example usage
    store = QdrantVectorStore(
        url="http://localhost:6333",    
        api_key="",
        collection="",
        google_api_key=""
    )

    # Example property item
    property_item = {
        
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
    
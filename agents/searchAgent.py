import time
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import time
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os
import sys
import json
import re
from pathlib import Path
import os
import sys
import json
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Configure root logger
logging.basicConfig(level=logging.INFO)
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
        """
        Add batch of property items to Qdrant.
        Each item is stored as a Document with flattened content and full JSON in metadata.
        """
        if not items:
            self.logger.warning("No items to add")
            return []

        docs: List[Document] = []
        for item in items:
            prop_id = item.get("id") or str(uuid.uuid4())
            upload_time = datetime.utcnow().isoformat()

            # Flatten content
            content_parts = []
            for key, value in item.items():
                if isinstance(value, dict):
                    content_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                elif isinstance(value, list):
                    content_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    content_parts.append(f"{key}: {value}")

            page_content = "\n".join(content_parts)

            metadata = {
                "id": prop_id,
                "upload_time": upload_time,
                "raw_data": json.dumps(item, ensure_ascii=False)
            }

            doc = Document(page_content=page_content, metadata=metadata)
            docs.append(doc)

        return self._retry_add(docs)


# Agent wrapper for property search filtering
import re
from agno.agent import Agent
from models.gemini import model

class PropertySearchAgent:
    def __init__(self, vector_store_client: QdrantVectorStoreClient):
        self.logger = logger  # Add logger attribute
        self.model = model
        self.vector_store = vector_store_client
        self.agent = Agent(
            name="PropertySearchAgent",
            model=self.model,
            markdown=False,
            description="Filters vector search results based on user query."
        )
        
        # Define the prompt as a separate method or attribute
        self.system_prompt = """
You are a smart real estate assistant. The input is a user query and vector db result, and your task is to filter the result based on the user query.
If the user query is not related to the vector db result, then return "No matching properties found. Try adjusting your search terms."

Instructions:
- Consider all filters and abbreviations in the user query (example: ac for air conditioning, inverter, etc.)
- In output, return only property_id and score as a JSON list
- Format: [{{"property_id": "id1", "score": 0.95}}, {{"property_id": "id2", "score": 0.87}}]

User query: {user_query}
Vector db result: {vector_db_result}
"""

    def search(self, user_query: str, k: int = 5) -> List[Dict[str, Any]]:
        # Step 1: retrieve top-k candidates
        candidates = self.vector_store.similarity_search(user_query, k)
        
        if not candidates:
            return []
        
        # Step 2: run filtering prompt
        prompt = self.system_prompt.format(
            user_query=user_query,
            vector_db_result=json.dumps(candidates, indent=2)
        )
        
        try:
            response = self.agent.run(prompt)
            # Handle different response formats
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # Try to parse JSON response
            if response_content.strip().startswith('['):
                return json.loads(response_content)
            elif "No matching properties found" in response_content:
                return []
            else:
                # Fallback: return original candidates if parsing fails
                self.logger.warning(f"Could not parse agent response: {response_content}")
                return [{"property_id": c.get("id"), "score": c.get("score", 0.0)} for c in candidates]
                
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error in agent search: {e}")
            return []


if __name__ == "__main__":
    # Example usage
    try:
        qdrant_client = QdrantVectorStoreClient(
            url="https://886d811f-9d2e-41a5-8043-7354789c11a3.europe-west3-0.gcp.cloud.qdrant.io:6333",
            api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.LCM5Vdz80er3DdIf8Mk6qGIKr3xF9MgyNcKpYup3TWA",
            collection="sample",
            google_api_key="AIzaSyCjz77h8Q3s3sa9XFx4jWm9qNio23ttxe8"
        )
        search_agent = PropertySearchAgent(qdrant_client)
        query = "Flats in Gurgaon  "
        results = search_agent.search(query, k=5)
        print("Filtered Results:", results)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
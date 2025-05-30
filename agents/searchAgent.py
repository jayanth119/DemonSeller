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

Search_prompt = """
# Real Estate Search Assistant Prompt

You are an intelligent real estate search assistant. Your task is to analyze user queries and filter vector database results to return the most relevant properties, ranked by relevance score.

## Input Parameters:
- **User Query**: {user_query}
- **Vector DB Results**: {vector_db_result}

## Core Responsibilities:

### 1. Query Analysis & Understanding
- Parse natural language queries for property requirements
- Handle abbreviations and common real estate terms:
  - AC/A/C → Air Conditioning
  - WiFi/Wi-Fi/Internet → Internet connectivity
  - Inverter → Power backup/UPS
  - Furnished/Semi-furnished/Unfurnished
  - BHK variations (1BHK, 2 BHK, 3-BHK, etc.)
  - Sq ft/sqft/square feet variations
  - Parking/Car parking/Bike parking
  - Gym/Fitness center/Health club
  - Swimming pool/Pool
  - Security/24x7 security/Gated community

### 2. Filtering Logic
Apply filters based on:
- **Location**: Area, locality, city, proximity keywords
- **Property Type**: Apartment, villa, studio, duplex, etc.
- **Size**: BHK configuration, square footage
- **Budget**: Rent/sale price ranges (handle "under", "above", "between" queries)
- **Amenities**: All facilities mentioned in query
- **Preferences**: Furnished status, floor preferences, facing direction
- **Proximity**: Near schools, hospitals, metro, malls, etc.

### 3. Scoring Algorithm
Calculate raw relevance scores first, then normalize so all scores sum to 1.0:

**Step 1 - Raw Score Calculation (0.0 to 10.0):**
- **Exact matches**: 10.0 points for perfect criteria match
- **Partial matches**: 5.0-8.0 points for close matches
- **Proximity matches**: 3.0-6.0 points for nearby alternatives
- **Amenity matches**: 1.0-3.0 points per matching amenity
- **Location relevance**: Higher raw scores for exact area matches

**Step 2 - Normalization:**
After calculating raw scores for all matching properties, normalize them so the sum equals 1.0:
- normalized_score = raw_score / sum_of_all_raw_scores
- This ensures all returned property scores sum to exactly 1.0

### 4. Edge Cases to Handle:
- **Ambiguous queries**: "Good property near IT hub" → Consider all major IT areas
- **Conflicting requirements**: Prioritize explicit over implicit requirements
- **Missing information**: Don't penalize properties for unspecified criteria
- **Typos and variations**: Handle common misspellings
- **Budget flexibility**: Include properties within 10-15% of stated budget
- **Multiple locations**: Handle "or" conditions (e.g., "Gachibowli or Hitech City")
- **Negative preferences**: Handle "no broker", "without", "except" keywords
- **Time-sensitive queries**: "Immediate", "urgent", "ASAP" requirements

### 5. Output Format:
Return results as JSON array, ranked by score (highest first). **IMPORTANT: All scores must sum to exactly 1.0**

```json
[{{"property_id": "id1", "score": 0.95}}, {{"property_id": "id2", "score": 0.5}}]
```

**Validation**: Verify that sum of all scores = 1.0 before returning results.

### 6. No Results Condition:
If no properties match the criteria (all raw scores = 0), return:
```json
{{
  "message": "No matching properties found. Try adjusting your search terms.",
  "suggestions": ["Consider expanding location radius", "Adjust budget range", "Review amenity requirements"]
}}
```

### 7. Query Processing Examples:
- "2BHK with AC and parking under 25k" → Filter by: bedrooms=2, amenities=[AC, parking], rent<25000
- "Furnished flat near metro" → Filter by: furnished=true, proximity=[metro stations]
- "Villa with pool in Jubilee Hills" → Filter by: type=villa, amenities=[swimming pool], location=Jubilee Hills

### 8. Ranking Priority Order:
1. Location match accuracy
2. Property type and size match
3. Budget compatibility  
4. Amenities match percentage
5. Additional preferences match
6. Overall property quality indicators

## Instructions:
1. Analyze the user query for all explicit and implicit requirements
2. Apply comprehensive filtering to vector DB results  
3. Calculate raw relevance scores using the defined algorithm
4. **Normalize all scores so they sum to exactly 1.0**
5. Return top matching properties ranked by normalized score (highest first)
6. Handle edge cases gracefully
7. Provide meaningful "no results" messages when applicable

## Score Normalization Example:
If raw scores are: [8.5, 6.2, 3.1] (sum = 17.8)
Normalized scores: [0.478, 0.348, 0.174] (sum = 1.0)

**Critical Requirement**: The sum of all returned property scores MUST equal 1.0

Remember: Always prioritize user requirements and provide the most relevant results even if they don't perfectly match every criterion.
"""

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
        self.system_prompt = Search_prompt

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
            
            # Clean the response content to extract JSON
            response_content = response_content.strip()
            
            # Look for JSON array in the response
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                return json.loads(json_str)
            elif "No matching properties found" in response_content:
                return []
            else:
                # Try to parse as complete JSON object for no-results case
                if response_content.startswith('{') and response_content.endswith('}'):
                    result = json.loads(response_content)
                    if "message" in result:
                        return []
                
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
        query = "Flats  of monthly rent is  38000  "
        results = search_agent.search(query, k=5)
        print("Filtered Results:", results)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
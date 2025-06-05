import json
import logging
from typing import List, Dict, Any
import os
import sys

from agno.agent import Agent


# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add path for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.gemini import model
from prompts.searchPrompt import Search_prompt
from models.vectorStore import QdrantVectorStoreClient

class PropertySearchAgent:
    def __init__(self, vector_store_client: QdrantVectorStoreClient):
        self.logger = logger
        self.model = model  # Only Gemini model
        self.vector_store = vector_store_client
        self.agent = Agent(
            name="PropertySearchAgent",
            model=self.model,
            markdown=False,
            description=Search_prompt
        )
        
        
        self.system_prompt = Search_prompt

    def search(self, user_query: str, k: int = 5) -> List[Dict[str, Any]]:
        candidates = self.vector_store.similarity_search(user_query, k)

        if not candidates:
            return []

        prompt = self.system_prompt.format(
            user_query=user_query,
            vector_db_result=json.dumps(candidates, indent=2)
        )

        try:
            response = self.agent.run(prompt)
            response_content = response.content if hasattr(response, 'content') else str(response)
            response_content = response_content.strip()

            # Try to extract JSON array
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                print(json_str)
                return json.loads(json_str)
            elif "No matching properties found" in response_content:
                return []
            elif response_content.startswith('{') and response_content.endswith('}'):
                result = json.loads(response_content)
                if "message" in result:
                    return []
            else:
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
                api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.w1474GJFXKREKXNFYEAQ_bMQ1HT3tKynM969KGHysi4",
                collection="sample",
                google_api_key="AIzaSyCmnhXgfxSw8iDPFsR9rm14Q8KFxntvUvk"
        )
        search_agent = PropertySearchAgent(qdrant_client)
        query = "Flats  contains of  no ac  , not  having elevator  and  Newly renovated  "
        results = search_agent.search(query, k=5)
        print("Filtered Results:", results)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
import time
import json
import logging
import uuid
from datetime import datetime
import time
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
import sys
import json
import re
import os 
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import re
from agno.agent import Agent
from models.gemini import model
from prompts.searchPrompt import Search_prompt
from models.vectorStore import QdrantVectorStoreClient

class PropertySearchAgent:
    def __init__(self, vector_store_client: QdrantVectorStoreClient):
        self.logger = logger  # Add logger attribute
        self.model = model
        self.vector_store = vector_store_client
        self.agent = Agent(
            name="PropertySearchAgent",
            model=self.model,
            markdown=False,
            description=Search_prompt
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

        )
        search_agent = PropertySearchAgent(qdrant_client)
        query = "Flats  contains of  no ac  , not  having elevator  and  Newly renovated  "
        results = search_agent.search(query, k=5)
        print("Filtered Results:", results)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
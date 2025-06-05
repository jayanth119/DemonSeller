from langchain.schema import Document
from langchain_community.vectorstores import Qdrant
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.exceptions import ResponseHandlingException
import json 
import uuid
import time
import ssl
import httpx
from datetime import datetime

class QdrantVectorStoreClient:
    def __init__(
        self,
        url: str,
        api_key: str,
        collection: str,
        google_api_key: str,
        prefer_grpc: bool = False,
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Enhanced initialization with SSL timeout handling
        
        Args:
            url: Qdrant Cloud URL (without :6333 for cloud)
            api_key: Qdrant Cloud API key
            collection: Collection name
            google_api_key: Google API key for embeddings
            prefer_grpc: Use gRPC instead of HTTP
            timeout: Connection timeout in seconds
            max_retries: Maximum connection retry attempts
        """
        self.url = url
        self.api_key = api_key
        self.collection = collection
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Fix URL format for Qdrant Cloud
        if ":6333" in url:
            # Remove port for cloud connections
            self.url = url.replace(":6333", "")
        
        # Initialize client with retry logic
        self.client = self._create_client_with_retry(prefer_grpc)
        
        # Create collection if it doesn't exist
        self._ensure_collection_exists()
        
        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )
        
        # Create LangChain vectorstore wrapper
        self.vs = Qdrant(
            client=self.client,
            collection_name=collection,
            embeddings=self.embeddings
        )

    def _create_client_with_retry(self, prefer_grpc: bool) -> QdrantClient:
        """Create Qdrant client with connection retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Method 1: Standard connection with increased timeout
                if attempt == 0:
                    client = QdrantClient(
                        url=self.url,
                        api_key=self.api_key,
                        prefer_grpc=prefer_grpc,
                        timeout=self.timeout
                    )
                
                # Method 2: Force HTTPS with custom SSL context
                elif attempt == 1:
                    # Create custom SSL context
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    # Create httpx client with custom SSL
                    httpx_client = httpx.Client(
                        timeout=self.timeout,
                        verify=ssl_context
                    )
                    
                    client = QdrantClient(
                        url=self.url,
                        api_key=self.api_key,
                        prefer_grpc=False,  # Force HTTP for this attempt
                        timeout=self.timeout
                    )
                
                # Method 3: Try with different URL format
                else:
                    # Ensure HTTPS protocol
                    url = self.url
                    if not url.startswith('https://') and not url.startswith('http://'):
                        url = f"https://{url}"
                    
                    client = QdrantClient(
                        url=url,
                        api_key=self.api_key,
                        prefer_grpc=False,
                        timeout=self.timeout * 2  # Double timeout for final attempt
                    )
                
                # Test the connection
                collections = client.get_collections()
                print(f"✅ Successfully connected to Qdrant on attempt {attempt + 1}")
                return client
                
            except (ResponseHandlingException, ssl.SSLError, TimeoutError) as e:
                last_exception = e
                wait_time = (attempt + 1) * 2
                print(f"❌ Connection attempt {attempt + 1} failed: {str(e)}")
                print(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # If all attempts failed, raise the last exception
        raise ConnectionError(
            f"Failed to connect to Qdrant after {self.max_retries} attempts. "
            f"Last error: {last_exception}"
        )

    def _ensure_collection_exists(self):
        """Ensure the collection exists with retry logic"""
        try:
            existing = [c.name for c in self.client.get_collections().collections]
            if self.collection not in existing:
                print(f"📝 Creating collection: {self.collection}")
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                print(f"✅ Collection '{self.collection}' created successfully")
            else:
                print(f"✅ Collection '{self.collection}' already exists")
        except Exception as e:
            print(f"❌ Error managing collection: {e}")
            raise

    def add_documents(self, items: list[dict]) -> list[str]:
        """Add documents with retry logic for rate limiting"""
        if not items:
            return []

        docs: list[Document] = []
        for item in items:
            prop_id = item.get("id") or str(uuid.uuid4())
            
            # Flatten item into text
            raw_lines = []
            for k, v in item.items():
                if isinstance(v, (str, int, float)):
                    raw_lines.append(f"{k}: {v}")
                else:
                    raw_lines.append(f"{k}: {v}")
            
            raw_text = "\n".join(raw_lines).strip()
            if not raw_text:
                continue

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
        """Enhanced retry logic for adding documents"""
        retries = 0
        while True:
            try:
                inserted_ids = self.vs.add_documents(documents)
                print(f"✅ Successfully added {len(documents)} documents")
                return inserted_ids
            except ResponseHandlingException as e:
                if retries < max_retries:
                    wait = 2**retries + 2
                    print(f"⏳ Rate limited, waiting {wait} seconds...")
                    time.sleep(wait)
                    retries += 1
                    continue
                raise RuntimeError(f"Unable to add documents after {max_retries} retries: {e}")
            except Exception as e:
                err = str(e).upper()
                if any(tok in err for tok in ["429", "RATE_LIMIT", "QUOTA", "OVERLOADED", "TIMEOUT"]):
                    if retries < max_retries:
                        wait = 2**retries + 2
                        print(f"⏳ Error detected, waiting {wait} seconds...")
                        time.sleep(wait)
                        retries += 1
                        continue
                raise RuntimeError(f"Unable to add documents: {e}")

    def similarity_search(self, query: str, k: int = 5) -> list[dict]:
        """Search with connection retry logic"""
        max_search_retries = 3
        for attempt in range(max_search_retries):
            try:
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
            except (ResponseHandlingException, TimeoutError) as e:
                if attempt < max_search_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⏳ Search failed, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"Search failed after {max_search_retries} attempts: {e}")

    def health_check(self) -> bool:
        """Check if the connection is healthy"""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False


# Updated PropertySearchAgent with better error handling
class PropertySearchAgent:
    def __init__(self, vector_store_client: QdrantVectorStoreClient):
        self.logger = logging.getLogger(__name__)
        self.vector_store = vector_store_client
        
        # Verify connection before proceeding
        if not self.vector_store.health_check():
            raise ConnectionError("Vector store connection is not healthy")
        
        # Import here to avoid circular imports
        try:
            from agno.agent import Agent
            from models.gemini import model
            from prompts.searchPrompt import Search_prompt
            
            self.model = model
            self.agent = Agent(
                name="PropertySearchAgent",
                model=self.model,
                markdown=False,
                description=Search_prompt
            )
            self.system_prompt = Search_prompt
        except ImportError as e:
            print(f"⚠️  Warning: Could not import agent dependencies: {e}")
            self.agent = None
            self.system_prompt = None

    def search(self, user_query: str, k: int = 5) -> list[dict]:
        """Enhanced search with better error handling"""
        try:
            # Step 1: Vector search
            candidates = self.vector_store.similarity_search(user_query, k)
            
            if not candidates:
                return []
            
            # If agent is not available, return candidates directly
            if not self.agent:
                return [{"property_id": c.get("id"), "score": c.get("score", 0.0)} for c in candidates]
            
            # Step 2: Agent filtering
            prompt = self.system_prompt.format(
                user_query=user_query,
                vector_db_result=json.dumps(candidates, indent=2)
            )
            
            response = self.agent.run(prompt)
            response_content = response.content if hasattr(response, 'content') else str(response)
            response_content = response_content.strip()
            
            # Parse JSON response
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                return json.loads(json_str)
            elif "No matching properties found" in response_content:
                return []
            else:
                # Fallback to candidates
                self.logger.warning(f"Could not parse agent response, returning candidates")
                return [{"property_id": c.get("id"), "score": c.get("score", 0.0)} for c in candidates]
                
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return []


# Example usage with improved error handling
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("🚀 Initializing Qdrant connection...")
        qdrant_client = QdrantVectorStoreClient(
            url="https://886d811f-9d2e-41a5-8043-7354789c11a3.europe-west3-0.gcp.cloud.qdrant.io",  # Removed :6333
            api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.w1474GJFXKREKXNFYEAQ_bMQ1HT3tKynM969KGHysi4",
            collection="sample",
            google_api_key="AIzaSyCmnhXgfxSw8iDPFsR9rm14Q8KFxntvUvk",
            timeout=60,
            max_retries=3
        )
        
        print("🔍 Initializing search agent...")
        search_agent = PropertySearchAgent(qdrant_client)
        
        print("📋 Running search query...")
        query = "Flats contains of no ac, not having elevator and Newly renovated"
        results = search_agent.search(query, k=5)
        
        print("✅ Search completed!")
        print("Filtered Results:", json.dumps(results, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
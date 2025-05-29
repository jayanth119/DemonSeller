import time
import json
import logging
from typing import List, Optional, Dict, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import Qdrant
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import ResponseHandlingException


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
            timeout=30.0  # Add timeout
        )
        
        # Initialize embedding model
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=self.google_api_key
        )

        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Ensure collection exists
        self.ensure_collection()

        # Initialize Langchain Qdrant wrapper
        self.vector_store = Qdrant(
            client=self.qdrant_client,
            collection_name=self.collection_name,
            embeddings=self.embedding_model,
        )

    def ensure_collection(self):
        """Ensure the collection exists, create if it doesn't"""
        try:
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.logger.info(f"Creating collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                self.logger.info(f"Collection {self.collection_name} created successfully")
            else:
                self.logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            self.logger.error(f"Error ensuring collection: {e}")
            raise

    def add_documents(self, items: List[Dict[str, Any]]):
        """Add documents to the vector store with retry logic"""
        if not items:
            self.logger.warning("No items to add")
            return

        try:
            # Prepare documents for Langchain
            docs = []
            for item in items:
                # Create page_content from the text_description or a combination of fields
                page_content = item.get('text_description', '')
                if not page_content and 'description' in item:
                    page_content = item['description']
                if not page_content:
                    page_content = json.dumps(item, ensure_ascii=False)
                
                # Create document with metadata
                doc = Document(
                    page_content=page_content,
                    metadata=item  # Store full item as metadata
                )
                docs.append(doc)
            
            # Add documents with retry logic
            self._retry_add(docs)
            self.logger.info(f"Successfully added {len(items)} documents")
            
        except Exception as e:
            self.logger.error(f"Error in add_documents: {e}")
            raise

    def _retry_add(self, documents: List[Document], max_retries: int = 5):
        """Add documents with exponential backoff retry"""
        retries = 0
        while retries < max_retries:
            try:
                # Use Langchain's add_documents method
                ids = self.vector_store.add_documents(documents)
                self.logger.info(f"Successfully added {len(documents)} documents to Qdrant")
                
                # Force flush to make points immediately searchable
                try:
                    self.qdrant_client.flush(collection_name=self.collection_name, wait=True)
                    self.logger.info("Successfully flushed collection")
                except Exception as flush_error:
                    self.logger.warning(f"Flush operation failed: {flush_error}")
                
                return ids
                
            except Exception as e:
                error_str = str(e).upper()
                self.logger.error(f"Error adding documents (attempt {retries+1}): {e}")
                
                if any(keyword in error_str for keyword in ["RATE_LIMIT", "QUOTA", "429"]):
                    wait_time = (2 ** retries) + 5  # Exponential backoff
                    self.logger.info(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                elif "TIMEOUT" in error_str or "CONNECTION" in error_str:
                    wait_time = 5 + retries * 2
                    self.logger.info(f"Connection issue, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    # For other errors, don't retry
                    self.logger.error(f"Non-retryable error: {e}")
                    raise
                    
        self.logger.error(f"Failed to add documents after {max_retries} retries")
        raise Exception(f"Failed to add documents after {max_retries} retries")

    def search_properties(
        self, 
        query: str, 
        k: int = 5, 
        filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Search for properties using similarity search"""
        try:
            self.logger.info(f"Searching for: '{query}' with k={k}")
            
            # Perform similarity search with scores
            results = self.vector_store.similarity_search_with_score(
                query, k=k, filter=filter
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                result = {
                    "id": doc.metadata.get("id", "unknown"),
                    "metadata": doc.metadata,
                    "score": score,
                    "distance": 1.0 - score,  # Convert similarity to distance
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                }
                formatted_results.append(result)
            
            self.logger.info(f"Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error in search_properties: {e}")
            return []

    def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific property by ID"""
        try:
            self.logger.info(f"Retrieving property: {property_id}")
            
            # Search for the specific property using metadata filter
            # Using a simple query but filtering by ID in metadata
            results = self.vector_store.similarity_search(
                query=f"property {property_id}",  # Simple query
                k=10,  # Get more results to find the right one
            )
            
            # Find the exact match by ID
            for doc in results:
                if doc.metadata.get("id") == property_id:
                    self.logger.info(f"Found property {property_id}")
                    return doc.metadata
            
            # Alternative approach: try direct point retrieval if the above fails
            try:
                # Get all points and filter (less efficient but more reliable)
                scroll_result = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,  # Adjust based on your needs
                    with_payload=True,
                    with_vectors=False
                )
                
                for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
                    if point.payload and point.payload.get("metadata", {}).get("id") == property_id:
                        self.logger.info(f"Found property {property_id} via scroll")
                        return point.payload.get("metadata", {})
                        
            except Exception as scroll_error:
                self.logger.warning(f"Scroll search failed: {scroll_error}")
            
            self.logger.warning(f"Property {property_id} not found")
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving property {property_id}: {e}")
            return None

    def get_all_properties(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all properties from the collection"""
        try:
            all_properties = []
            offset = None
            
            while True:
                scroll_result = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=min(limit, 100),  # Qdrant has a max limit per request
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                points, next_offset = scroll_result
                
                for point in points:
                    if point.payload and "metadata" in point.payload:
                        all_properties.append(point.payload["metadata"])
                
                if next_offset is None or len(all_properties) >= limit:
                    break
                    
                offset = next_offset
            
            self.logger.info(f"Retrieved {len(all_properties)} properties")
            return all_properties[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting all properties: {e}")
            return []

    def delete_property(self, property_id: str) -> bool:
        """Delete a property by ID"""
        try:
            # Find points with matching property ID
            scroll_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            
            points_to_delete = []
            for point in scroll_result[0]:
                if point.payload and point.payload.get("metadata", {}).get("id") == property_id:
                    points_to_delete.append(point.id)
            
            if points_to_delete:
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=points_to_delete
                )
                self.logger.info(f"Deleted property {property_id}")
                return True
            else:
                self.logger.warning(f"Property {property_id} not found for deletion")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting property {property_id}: {e}")
            return False

    def count_properties(self) -> int:
        """Count total number of properties"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            self.logger.error(f"Error counting properties: {e}")
            return 0

    def health_check(self) -> bool:
        """Check if the vector store is healthy"""
        try:
            collections = self.qdrant_client.get_collections()
            return self.collection_name in [col.name for col in collections.collections]
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
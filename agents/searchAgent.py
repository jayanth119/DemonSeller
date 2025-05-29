import os
import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from agno.models.message import Message
from agno.agent import Agent
from models.gemini import model as gemini_model
from prompts.searchPrompt import Search_prompt
from models.vectorStore import QdrantVectorStore


class PropertySearchAgent:
    def __init__(self):
        self.synonyms = {
            'ac': 'air conditioner',
            'air conditioner': 'ac',
            'tv': 'television',
            'television': 'tv',
            'fridge': 'refrigerator',
            'refrigerator': 'fridge',
            'bhk': 'bedroom hall kitchen',
            '1bhk': '1 bedroom hall kitchen',
            '2bhk': '2 bedroom hall kitchen',
            '3bhk': '3 bedroom hall kitchen',
            '4bhk': '4 bedroom hall kitchen',
        }

        self.agent = Agent(
            name="SearchAgent",
            model=gemini_model,
            markdown=False,
            description=Search_prompt
        )

        self.vector_store = QdrantVectorStore(

        )

        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        logfile = os.path.join(log_dir, f'search_agent_{ts}.log')
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(logfile),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Search Agent initialized")

    def _normalize_synonyms(self, text: str) -> str:
        """Normalize synonyms in text for better matching"""
        if not text:
            return text
            
        normalized_text = text.lower()
        for synonym, replacement in self.synonyms.items():
            pattern = re.compile(rf"\b{re.escape(synonym)}\b", re.IGNORECASE)
            normalized_text = pattern.sub(replacement, normalized_text)
        return normalized_text

    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms"""
        expanded_query = self._normalize_synonyms(query)
        
        # Add common property-related terms
        property_terms = []
        if any(term in expanded_query.lower() for term in ['bhk', 'bedroom']):
            property_terms.append('apartment flat house')
        if any(term in expanded_query.lower() for term in ['parking', 'garage']):
            property_terms.append('car parking vehicle')
        if any(term in expanded_query.lower() for term in ['furnish', 'furniture']):
            property_terms.append('furnished semi-furnished unfurnished')
            
        if property_terms:
            expanded_query += ' ' + ' '.join(property_terms)
            
        return expanded_query

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for properties matching the query"""
        try:
            if not query or not query.strip():
                self.logger.warning("Empty query provided")
                return []

            self.logger.info(f"Starting search for query: '{query}'")
            
            # Normalize and expand query
            normalized_query = self._normalize_synonyms(query.strip())
            expanded_query = self._expand_query(query.strip())
            
            self.logger.info(f"Normalized query: '{normalized_query}'")
            self.logger.info(f"Expanded query: '{expanded_query}'")

            # Perform initial vector search with expanded query
            initial_results = self.vector_store.search_properties(
                expanded_query, 
                k=min(n_results * 3, 20)  # Get more results for better filtering
            )
            
            self.logger.info(f"Initial vector search returned {len(initial_results)} results")

            if not initial_results:
                # Try with original query if expanded query returns nothing
                self.logger.info("Trying with original query")
                initial_results = self.vector_store.search_properties(
                    normalized_query, 
                    k=n_results * 2
                )

            if not initial_results:
                self.logger.info("No results found from vector search")
                return []

            # Apply LLM-based filtering and ranking
            filtered_results = self._llm_filter_and_rank(query, initial_results)
            
            # Sort by distance (lower is better) and limit results
            filtered_results.sort(key=lambda x: x.get('distance', 1.0))
            final_results = filtered_results[:n_results]
            
            self.logger.info(f"Returning {len(final_results)} filtered results")
            return final_results

        except Exception as e:
            self.logger.error(f"Error in search: {e}")
            return []

    def _llm_filter_and_rank(self, query: str, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to filter and rank properties based on query relevance"""
        if not properties:
            return []

        try:
            # Prepare property profiles for LLM analysis
            property_profiles = []
            for prop in properties:
                metadata = prop.get('metadata', {})
                
                # Extract key information for LLM analysis
                profile_info = {
                    'id': prop.get('id', 'unknown'),
                    'distance': prop.get('distance', 1.0),
                    'description': metadata.get('description', ''),
                }
                
                # Try to parse text_description if it exists
                if 'text_description' in metadata:
                    try:
                        parsed_desc = json.loads(metadata['text_description'])
                        if isinstance(parsed_desc, dict):
                            profile_info.update(parsed_desc)
                        else:
                            profile_info['raw_description'] = str(parsed_desc)
                    except (json.JSONDecodeError, TypeError):
                        profile_info['raw_description'] = str(metadata.get('text_description', ''))
                
                # Add other metadata
                for key, value in metadata.items():
                    if key not in ['text_description'] and value:
                        profile_info[key] = value
                
                property_profiles.append(profile_info)

            # Create LLM prompt for filtering and ranking
            prompt_content = self._create_filter_prompt(query, property_profiles)
            
            # Get LLM response
            response = self.agent.invoke([Message(role="user", content=prompt_content)])
            
            self.logger.info(f"LLM response: {response.text[:200]}...")
            
            # Parse LLM response to get selected property IDs
            selected_ids = self._parse_llm_response(response.text)
            
            self.logger.info(f"LLM selected property IDs: {selected_ids}")
            
            # Filter properties based on LLM selection
            filtered_properties = []
            for prop in properties:
                if prop.get('id') in selected_ids:
                    # Add LLM ranking information
                    try:
                        llm_rank = selected_ids.index(prop.get('id'))
                        prop['llm_rank'] = llm_rank
                        prop['llm_score'] = 1.0 - (llm_rank / len(selected_ids))
                    except ValueError:
                        prop['llm_rank'] = 999
                        prop['llm_score'] = 0.0
                    
                    filtered_properties.append(prop)
            
            # If LLM filtering returns too few results, include top vector results
            if len(filtered_properties) < min(3, len(properties)):
                self.logger.info("LLM filtering returned few results, including top vector matches")
                for prop in properties[:5]:  # Include top 5 vector results
                    if prop not in filtered_properties:
                        prop['llm_rank'] = 999
                        prop['llm_score'] = 0.0
                        filtered_properties.append(prop)

            return filtered_properties

        except Exception as e:
            self.logger.error(f"Error in LLM filtering: {e}")
            # Return original results if LLM filtering fails
            return properties

    def _create_filter_prompt(self, query: str, properties: List[Dict[str, Any]]) -> str:
        """Create a prompt for LLM to filter and rank properties"""
        prompt = f"""
You are a property search expert. Given a user's search query and a list of property profiles, 
select and rank the most relevant properties that match the user's requirements.

USER QUERY: "{query}"

PROPERTY PROFILES:
"""
        
        for i, prop in enumerate(properties, 1):
            prompt += f"\n{i}. Property ID: {prop.get('id', 'unknown')}\n"
            prompt += f"   Vector Score: {prop.get('distance', 'N/A')}\n"
            
            # Add key property details
            if 'description' in prop and prop['description']:
                prompt += f"   Description: {prop['description'][:200]}...\n"
            
            # Add parsed property features if available
            for key, value in prop.items():
                if key not in ['id', 'distance', 'description', 'text_description', 'created_at'] and value:
                    if isinstance(value, (str, int, float, bool)):
                        prompt += f"   {key.title()}: {value}\n"
            
            prompt += "\n"

        prompt += """
INSTRUCTIONS:
1. Analyze each property against the user's search query
2. Consider factors like: property type, size, amenities, location, furnishing, etc.
3. Select properties that best match the user's requirements
4. Rank them by relevance (most relevant first)
5. Return ONLY the Property IDs in order of relevance, separated by commas

EXAMPLE RESPONSE FORMAT:
20241201123456, 20241201234567, 20241201345678

YOUR RESPONSE (Property IDs only):"""

        return prompt

    def _parse_llm_response(self, response_text: str) -> List[str]:
        """Parse LLM response to extract property IDs"""
        try:
            # Clean the response
            cleaned_response = response_text.strip()
            
            # Remove any extra text and extract property IDs
            # Look for patterns that match property ID format (timestamp-like)
            id_pattern = r'\b\d{14}\b'  # 14-digit property IDs
            found_ids = re.findall(id_pattern, cleaned_response)
            
            if found_ids:
                self.logger.info(f"Found property IDs using regex: {found_ids}")
                return found_ids
            
            # Fallback: split by commas and clean
            parts = [part.strip() for part in cleaned_response.split(',')]
            valid_ids = [part for part in parts if part and len(part) >= 10]
            
            self.logger.info(f"Parsed property IDs: {valid_ids}")
            return valid_ids
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return []

    def get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific property"""
        try:
            self.logger.info(f"Fetching details for property ID: {property_id}")
            
            details = self.vector_store.get_property(property_id)
            
            if details:
                self.logger.info(f"Retrieved details for property ID: {property_id}")
                
                # Parse text_description if it exists
                if 'text_description' in details:
                    try:
                        parsed_desc = json.loads(details['text_description'])
                        if isinstance(parsed_desc, dict):
                            details.update(parsed_desc)
                    except (json.JSONDecodeError, TypeError) as e:
                        self.logger.warning(f"Failed to parse text_description: {e}")
                
                return details
            else:
                self.logger.warning(f"No details found for property ID: {property_id}")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error fetching property details for {property_id}: {e}")
            return {}

    def get_all_properties(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all registered properties"""
        try:
            self.logger.info(f"Fetching all properties (limit: {limit})")
            properties = self.vector_store.get_all_properties(limit=limit)
            self.logger.info(f"Retrieved {len(properties)} properties")
            return properties
        except Exception as e:
            self.logger.error(f"Error fetching all properties: {e}")
            return []

    def health_check(self) -> bool:
        """Check if the search agent and vector store are healthy"""
        try:
            return self.vector_store.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
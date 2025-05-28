from typing import List, Dict, Any
import re
import numpy as np
from models.vectorStore import PropertyVectorStore
import logging
from models.gemini import model as gemini_model
from agno.models.message import Message
from agno.agent import Agent
import os
import sys
import json
from pathlib import Path
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.searchPrompts import Search_prompt
from .mainAgent import MainAnalysisAgent

class PropertySearchAgent:
    def __init__(self):
        self.agent = Agent(
            name="SearchAgent",
            model=gemini_model,
            markdown=False,
            description=Search_prompt,
        )
        self.main_agent = MainAnalysisAgent()
        self.vector_store = PropertyVectorStore()
        
        # Common property attributes to extract
        self.property_types = ['1bhk', '2bhk', '3bhk', '4bhk', 'studio', 'apartment', 'flat', 'house', '1rk', '2rk', '3rk', '4rk']
        self.price_keywords = ['rent', 'price', 'cost', 'budget']
        
        # Set up enhanced logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Set up enhanced logging configuration"""
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a unique log file for each run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(log_dir, f'search_agent_{timestamp}.log')
        
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Search Agent initialized")
        
    def _log_property_analysis(self, property_id: str, analysis: Dict[str, Any]):
        """Log detailed property analysis"""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Property Analysis for {property_id}")
        self.logger.info(f"{'='*50}")
        
        if isinstance(analysis, str):
            self.logger.info(f"\nANALYSIS:\n{analysis}")
        elif isinstance(analysis, dict):
            for key, value in analysis.items():
                if isinstance(value, dict):
                    self.logger.info(f"\n{key.upper()}:")
                    for subkey, subvalue in value.items():
                        self.logger.info(f"  {subkey}: {subvalue}")
                elif isinstance(value, list):
                    self.logger.info(f"\n{key.upper()}:")
                    for item in value:
                        self.logger.info(f"  - {item}")
                else:
                    self.logger.info(f"\n{key.upper()}: {value}")
        else:
            self.logger.info(f"\nANALYSIS:\n{str(analysis)}")
        
        self.logger.info(f"{'='*50}\n")

    def _extract_price_range(self, query: str) -> Dict[str, float]:
        """Extract price range from natural language query"""
        price_range = {'min': None, 'max': None}
        
        # Convert query to lowercase for consistent matching
        query_lower = query.lower()
        
        # Look for price range patterns
        range_patterns = [
            r'(\d+)[kK]?\s*-\s*(\d+)[kK]?',  # 15k-25k
            r'between\s+(\d+)[kK]?\s*(?:and|to|-)\s*(\d+)[kK]?',  # between 15k and 25k
            r'(\d+)[kK]?\s*(?:to|-)\s*(\d+)[kK]?',  # 15k to 25k
            r'(\d+)[kK]?\s*(?:and|&)\s*(\d+)[kK]?',  # 15k and 25k
            r'rent\s+(?:of|is|around|about)?\s*(\d+)[kK]?',  # rent of 20k
            r'(\d+)[kK]?\s*(?:thousand|k)',  # 20 thousand or 20k
        ]
        
        for pattern in range_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                if len(match.groups()) == 2:  # Range pattern
                    min_val = self._convert_price(match.group(1))
                    max_val = self._convert_price(match.group(2))
                    price_range['min'] = min(min_val, max_val)
                    price_range['max'] = max(min_val, max_val)
                    self.logger.info(f"Found price range: {price_range}")
                    return price_range
                else:  # Single value pattern
                    val = self._convert_price(match.group(1))
                    if price_range['min'] is None:
                        price_range['min'] = val
                    else:
                        price_range['max'] = val
        
        return price_range
    
    def _convert_price(self, price_str: str) -> float:
        """Convert price string to float value"""
        # Remove any non-numeric characters except 'k' and 'K'
        price_str = re.sub(r'[^\dkK]', '', price_str)
        
        # Convert to float
        if 'k' in price_str.lower():
            return float(price_str.lower().replace('k', '')) * 1000
        return float(price_str)
    
    def _extract_property_type(self, query: str) -> List[str]:
        """Extract property types from natural language query"""
        query_lower = query.lower()
        found_types = []
        type_patterns = [
            r'(\d+)\s*bhk',  # 2 bhk, 3bhk
            r'(\d+)\s*bedroom',  # 2 bedroom
            r'(\d+)\s*bed',  # 2 bed
            r'(\d+)\s*rk',  # 1rk, 2rk
            r'studio\s*apartment',  # studio apartment
            r'apartment',  # apartment
            r'flat',  # flat
            r'house',  # house
        ]
        for pattern in type_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                if 'bhk' in pattern or 'bedroom' in pattern or 'bed' in pattern:
                    found_types.append(f"{match.group(1)}bhk")
                elif 'rk' in pattern:
                    found_types.append(f"{match.group(1)}rk")
                else:
                    found_types.append(match.group(0))
        return list(set(found_types))  # Remove duplicates
    
    def _extract_location(self, query: str) -> str:
        """Extract location from natural language query"""
        location_keywords = ['in', 'at', 'near', 'around', 'close to', 'located in', 'situated in']
        words = query.lower().split()
        
        for i, word in enumerate(words):
            if word in location_keywords and i + 1 < len(words):
                # Get all words after the location keyword until the next keyword or end
                location = []
                for j in range(i + 1, len(words)):
                    if words[j] in location_keywords:
                        break
                    location.append(words[j])
                return ' '.join(location)
        return None
    
    def _filter_by_criteria(self, properties: List[Dict[str, Any]], 
                           property_types: List[str],
                           price_range: Dict[str, float],
                           location: str) -> List[Dict[str, Any]]:
        """Filter properties based on extracted criteria with more flexible matching"""
        filtered_properties = []
        
        for prop in properties:
            metadata = prop['metadata']
            description = metadata.get('text_description', '').lower()
            price = metadata.get('price', '')
            prop_type = metadata.get('property_type', '').lower()
            prop_location = metadata.get('location', '').lower()
            
            # Log property details for debugging
            self.logger.info(f"\nAnalyzing property {prop['id']}:")
            self.logger.info(f"Description: {description}")
            self.logger.info(f"Type: {prop_type}")
            self.logger.info(f"Price: {price}")
            self.logger.info(f"Location: {prop_location}")
            
            # Check property type with more flexible matching
            if property_types:
                # Extract property type from description
                desc_type = None
                type_patterns = [
                    r'(\d+)\s*bhk',
                    r'(\d+)\s*rk',
                    r'studio\s*apartment',
                    r'apartment',
                    r'flat',
                    r'house'
                ]
                for pattern in type_patterns:
                    match = re.search(pattern, description)
                    if match:
                        if 'bhk' in pattern:
                            desc_type = f"{match.group(1)}bhk"
                        elif 'rk' in pattern:
                            desc_type = f"{match.group(1)}rk"
                        else:
                            desc_type = match.group(0)
                        break
                
                # If no specific type was requested, accept any residential property
                if not property_types or property_types == ['flat']:
                    type_match = True
                    self.logger.info(f"No specific type requested, accepting any residential property")
                else:
                    # Check if any of the property types match
                    type_match = False
                    if desc_type:
                        type_match = any(ptype.lower() == desc_type.lower() for ptype in property_types)
                    if not type_match:
                        # Fallback to checking if type is mentioned in description
                        type_match = any(ptype.lower() in description for ptype in property_types)
                
                if not type_match:
                    self.logger.info(f"Property {prop['id']} filtered out due to type mismatch")
                    continue
                else:
                    self.logger.info(f"Property {prop['id']} passed type check")
            
            # Check price range with more flexible matching
            if price_range['min'] is not None or price_range['max'] is not None:
                prices = []
                
                # Add price from metadata if available
                if price:
                    try:
                        # Handle various price formats
                        price_str = price.lower()
                        if 'lakh' in price_str or 'lac' in price_str:
                            price_val = float(re.sub(r'[^\d.]', '', price_str)) * 100000
                        elif 'cr' in price_str or 'crore' in price_str:
                            price_val = float(re.sub(r'[^\d.]', '', price_str)) * 10000000
                        else:
                            price_val = float(re.sub(r'[^\d.]', '', price_str))
                            if 'k' in price_str:
                                price_val *= 1000
                        prices.append(price_val)
                        self.logger.info(f"Found price in metadata: {price_val}")
                    except ValueError as e:
                        self.logger.info(f"Could not parse price from metadata: {e}")
                
                # Extract prices from description
                price_patterns = [
                    r'rent\s*[-:]?\s*(\d+)[kK]',  # rent - 20k
                    r'rent\s*(?:of|is|around|about)?\s*(\d+)[kK]',  # rent of 20k
                    r'(\d+)[kK]',  # 20k
                    r'(\d+)[,\d]*\s*(?:thousand|k)',  # 20 thousand
                    r'(\d+)[,\d]*\s*(?:lakh|lac)',  # 20 lakh
                    r'(\d+)[,\d]*\s*(?:cr|crore)',  # 20 crore
                    r'rs\.?\s*(\d+)[kK]?',  # Rs. 20k
                ]
                
                for pattern in price_patterns:
                    matches = re.finditer(pattern, description)
                    for match in matches:
                        try:
                            price = float(match.group(1))
                            if 'k' in match.group(0).lower():
                                price *= 1000
                            elif 'lakh' in match.group(0).lower() or 'lac' in match.group(0).lower():
                                price *= 100000
                            elif 'cr' in match.group(0).lower() or 'crore' in match.group(0).lower():
                                price *= 10000000
                            prices.append(price)
                            self.logger.info(f"Found price in description: {price}")
                        except ValueError as e:
                            self.logger.info(f"Could not parse price from description: {e}")
                
                if prices:
                    # Check if any price falls within the range
                    price_in_range = False
                    for price in prices:
                        if (price_range['min'] is None or price >= price_range['min']) and \
                           (price_range['max'] is None or price <= price_range['max']):
                            price_in_range = True
                            self.logger.info(f"Price {price} is within range {price_range}")
                            break
                    if not price_in_range:
                        self.logger.info(f"Property {prop['id']} filtered out due to price range mismatch. Prices found: {prices}, Range: {price_range}")
                        continue
                    else:
                        self.logger.info(f"Property {prop['id']} passed price check")
                else:
                    self.logger.info(f"Property {prop['id']} filtered out due to no price found")
                    continue
            
            # Check location with more flexible matching
            if location:
                location_match = (location.lower() in description or 
                                location.lower() in prop_location or
                                any(loc.lower() in description for loc in location.split()))
                if not location_match:
                    self.logger.info(f"Property {prop['id']} filtered out due to location mismatch")
                    continue
                else:
                    self.logger.info(f"Property {prop['id']} passed location check")
            
            filtered_properties.append(prop)
            self.logger.info(f"Property {prop['id']} passed all checks")
        
        return filtered_properties
    
    def _llm_filter_properties(self, query: str, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Gemini LLM to filter properties based on the user query and property data."""
        if not properties:
            return []
        
        # Prepare detailed property information for the LLM
        property_details = []
        for prop in properties:
            metadata = prop['metadata']
            details = {
                'id': prop['id'],
                'description': metadata.get('text_description', ''),
                'price': metadata.get('price', ''),
                'type': metadata.get('property_type', ''),
                'location': metadata.get('location', ''),
                'features': metadata.get('features', []),
                'image_description': metadata.get('image_description', '')
            }
            property_details.append(details)
        
        # Construct a more detailed prompt for Gemini
        prompt = f"""Given the following user query and property listings, identify which properties best match the requirements.
        
User Query: {query}

Available Properties:
{property_details}

Please analyze each property and return a comma-separated list of property IDs that match the user's requirements.
Consider:
1. Price requirements (including various formats like k, lakh, crore)
2. Property type (including BHK, RK, studio, etc.)
3. Location
4. Features and amenities
5. Overall match with user's intent

Important guidelines:
- If a property's price is within the requested range, include it
- If a property type matches or is similar to what was requested, include it
- If no specific type was requested, consider all residential properties
- Be lenient in matching - if a property is close to the requirements, include it
- Consider both explicit and implicit requirements in the query

Return only the IDs of properties that are a good match, separated by commas."""

        # Call Gemini LLM using Message objects
        messages = [Message(role="user", content=prompt)]
        response = self.agent.invoke(messages)
        
        # Extract and clean selected IDs
        selected_ids = [id.strip() for id in response.text.strip().split(',') if id.strip()]
        self.logger.info(f"LLM selected property IDs: {selected_ids}")
        
        # Filter properties based on selected IDs
        filtered_properties = [prop for prop in properties if prop['id'] in selected_ids]
        return filtered_properties
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform intelligent property search based on natural language query
        """
        # Get initial results from vector store
        initial_results = self.vector_store.search_properties(query, n_results=n_results*2)
        self.logger.info(f"Found {len(initial_results)} initial results")
        
        # Use LLM to filter properties
        llm_filtered_results = self._llm_filter_properties(query, initial_results)
        self.logger.info(f"After LLM filtering: {len(llm_filtered_results)} results")
        
        # Sort by relevance (distance) and return top n results
        llm_filtered_results.sort(key=lambda x: x['distance'])
        return llm_filtered_results[:n_results]
    
    def get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific property"""
        return self.vector_store.get_property(property_id)

    def search_properties(self, query: str, properties_dir: str) -> List[Dict[str, Any]]:
        """Search through properties based on user query with enhanced logging"""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Starting property search")
        self.logger.info(f"Query: {query}")
        self.logger.info(f"Properties directory: {properties_dir}")
        self.logger.info(f"{'='*50}\n")
        
        results = []
        
        # Get all property directories
        property_dirs = [d for d in os.listdir(properties_dir) 
                        if os.path.isdir(os.path.join(properties_dir, d))]
        self.logger.info(f"Found {len(property_dirs)} property directories")
        
        # Analyze each property
        for prop_dir in property_dirs:
            self.logger.info(f"\nProcessing property: {prop_dir}")
            property_path = os.path.join(properties_dir, prop_dir)
            
            try:
                # Get property analysis
                self.logger.info("Starting property analysis...")
                analysis = self.main_agent.analyze_property(property_path)
                self._log_property_analysis(prop_dir, analysis)
                
                # Check for direct matches in contact info
                if "jain" in analysis.lower():
                    results.append({
                        "property_id": prop_dir,
                        "analysis": analysis,
                        "relevance_score": 1.0,
                        "match_reason": "Direct match with Jain Properties"
                    })
                    self.logger.info(f"Property {prop_dir} matched directly with Jain Properties")
                    continue
                
                # Search for matches using LLM
                self.logger.info("Checking property against query...")
                try:
                    response = self.agent.run(
                        f"Query: {query}\n\nProperty Analysis:\n{analysis}"
                    )
                    
                    # Parse the response
                    response_data = self._parse_search_response(response.content)
                    
                    # Log search results
                    self.logger.info(f"Search results for {prop_dir}:")
                    self.logger.info(f"Matches: {response_data['matches']}")
                    self.logger.info(f"Relevance score: {response_data['relevance_score']}")
                    self.logger.info(f"Matching criteria: {response_data['matching_criteria']}")
                    self.logger.info(f"Non-matching criteria: {response_data['non_matching_criteria']}")
                    self.logger.info(f"Explanation: {response_data['explanation']}")
                    
                    # If property matches query, add to results
                    if response_data['matches']:
                        results.append({
                            "property_id": prop_dir,
                            "analysis": analysis,
                            "relevance_score": response_data['relevance_score'],
                            "match_reason": response_data['explanation']
                        })
                        self.logger.info(f"Property {prop_dir} added to results")
                    else:
                        self.logger.info(f"Property {prop_dir} did not match query")
                        
                except Exception as e:
                    self.logger.error(f"Error checking property {prop_dir} against query: {str(e)}")
                    continue
                
            except Exception as e:
                self.logger.error(f"Error analyzing property {prop_dir}: {str(e)}", exc_info=True)
                continue
        
        # Sort results by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        self.logger.info(f"\nSearch completed. Found {len(results)} matching properties")
        
        # Log final results
        self.logger.info("\nFinal Results:")
        if results:
            for idx, result in enumerate(results, 1):
                self.logger.info(f"\n{idx}. Property: {result['property_id']}")
                self.logger.info(f"   Relevance Score: {result['relevance_score']}")
                self.logger.info(f"   Match Reason: {result.get('match_reason', 'No reason provided')}")
        else:
            self.logger.info("No properties found matching the search criteria")
        
        return results

    def get_property_details(self, property_id: str, properties_dir: str) -> Dict[str, Any]:
        """Get detailed information about a specific property with enhanced logging"""
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Getting details for property: {property_id}")
        
        property_path = os.path.join(properties_dir, property_id)
        if not os.path.exists(property_path):
            self.logger.error(f"Property {property_id} not found")
            raise ValueError(f"Property {property_id} not found")
        
        try:
            self.logger.info("Starting property analysis...")
            analysis = self.main_agent.analyze_property(property_path)
            self._log_property_analysis(property_id, analysis)
            return analysis
        except Exception as e:
            self.logger.error(f"Error getting property details: {str(e)}", exc_info=True)
            raise

    def _parse_search_response(self, response: str) -> Dict[str, Any]:
        """Parse the plain text search response into a structured format"""
        try:
            # Extract matches (yes/no)
            matches = False
            if re.search(r'\b(yes|matches|is a match)\b', response.lower()):
                matches = True
            
            # Extract relevance score
            relevance_score = 0.0
            score_match = re.search(r'relevance score:?\s*(\d*\.?\d+)', response.lower())
            if score_match:
                relevance_score = float(score_match.group(1))
            
            # Extract matching criteria
            matching_criteria = []
            criteria_match = re.search(r'matching criteria:?\s*(.*?)(?:\n|$)', response.lower())
            if criteria_match:
                criteria_text = criteria_match.group(1)
                matching_criteria = [c.strip() for c in criteria_text.split(',') if c.strip()]
            
            # Extract non-matching criteria
            non_matching_criteria = []
            non_match = re.search(r'non-matching criteria:?\s*(.*?)(?:\n|$)', response.lower())
            if non_match:
                criteria_text = non_match.group(1)
                non_matching_criteria = [c.strip() for c in criteria_text.split(',') if c.strip()]
            
            # Extract explanation
            explanation = ""
            explanation_match = re.search(r'explanation:?\s*(.*?)(?:\n\n|$)', response, re.DOTALL)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
            
            return {
                "matches": matches,
                "relevance_score": relevance_score,
                "matching_criteria": matching_criteria,
                "non_matching_criteria": non_matching_criteria,
                "explanation": explanation
            }
        except Exception as e:
            self.logger.error(f"Error parsing search response: {str(e)}")
            return {
                "matches": False,
                "relevance_score": 0.0,
                "matching_criteria": [],
                "non_matching_criteria": [],
                "explanation": f"Error parsing response: {str(e)}"
            }

if __name__ == "__main__":
    agent = PropertySearchAgent()
    properties_dir = "/path/to/properties"  
    query = "Find properties with 2 bedrooms and a balcony"
    results = agent.search_properties(query, properties_dir)
    print(json.dumps(results, indent=2)) 
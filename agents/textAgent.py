from agno.agent import Agent
import os
import sys
import time
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.textPrompts import Text_prompt
from models.gemini import model

class TextAnalysisAgent:
    def __init__(self):
        self.agent = Agent(
            name="TextAgent",
            model=model,
            markdown=False,
            description=Text_prompt,
        )

    def analyze_text(self, text_path):
        """Analyze text content and extract relevant property information"""
        try:
            # Read the text file
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            # Use a single prompt to extract all information
            combined_prompt = f"""Analyze this property description and provide a detailed analysis in plain text format.
            Text: {text_content}
            
            Include the following information in your analysis:
            • Property details (type, size, location, price)
            • Available amenities and facilities
            • Property rules and restrictions
            • Additional relevant information
            • Contact information for inquiries
            
            Format your response in clear, well-structured paragraphs."""

            # Add retry logic for rate limits
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = self.agent.run(combined_prompt)
                    return response.content.strip()
                    
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        print(f"Rate limit hit, retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    raise

        except Exception as e:
            print(f"Error in text analysis: {str(e)}")
            return "Error analyzing text. Please try again later."
        
        
if __name__ == "__main__":
    agent = TextAnalysisAgent()
    text_path = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7/flat7.txt"
    result = agent.analyze_text(text_path)
    print(result)

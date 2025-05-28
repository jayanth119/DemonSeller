from agno.agent import Agent
import os
import sys
import json
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.mainPrompts import Main_prompt
from models.gemini import model
from .imageAgent import ImageAnalysisAgent
from .videoAgent import VideoAnalysisAgent
from .textAgent import TextAnalysisAgent

class MainAnalysisAgent:
    def __init__(self):
        self.agent = Agent(
            name="MainAgent",
            model=model,
            markdown=False,
            description=Main_prompt,
        )
        self.image_agent = ImageAnalysisAgent()
        self.video_agent = VideoAnalysisAgent()
        self.text_agent = TextAnalysisAgent()

    def analyze_property(self, property_path):
        """Analyze a property using all available data sources"""
        results = {
            "image_analysis": None,
            "video_analysis": None,
            "text_analysis": None
        }

        # Analyze images
        image_dir = os.path.join(property_path, "images")
        if os.path.exists(image_dir):
            try:
                results["image_analysis"] = self.image_agent.analyze_images(image_dir)
            except Exception as e:
                print(f"Error in image analysis: {str(e)}")

        # Analyze videos
        video_dir = os.path.join(property_path, "videos")
        if os.path.exists(video_dir):
            try:
                for video_file in os.listdir(video_dir):
                    if video_file.lower().endswith(('.mp4', '.avi', '.mov')):
                        video_path = os.path.join(video_dir, video_file)
                        results["video_analysis"] = self.video_agent.analyze_video(video_path)
                        break  # Analyze only the first video for now
            except Exception as e:
                print(f"Error in video analysis: {str(e)}")

        # Analyze text
        text_dir = os.path.join(property_path, "text")
        if os.path.exists(text_dir):
            try:
                for text_file in os.listdir(text_dir):
                    if text_file.lower().endswith(('.txt', '.doc', '.docx', '.pdf')):
                        text_path = os.path.join(text_dir, text_file)
                        results["text_analysis"] = self.text_agent.analyze_text(text_path)
                        break  # Analyze only the first text file for now
            except Exception as e:
                print(f"Error in text analysis: {str(e)}")

        # Combine all analyses
        try:
            # Convert results to a string representation
            results_str = "\n\n".join([
                f"Image Analysis:\n{results['image_analysis']}" if results['image_analysis'] else "No image analysis available",
                f"Video Analysis:\n{results['video_analysis']}" if results['video_analysis'] else "No video analysis available",
                f"Text Analysis:\n{results['text_analysis']}" if results['text_analysis'] else "No text analysis available"
            ])

            combined_analysis = self.agent.run(
                f"Based on the following property analyses, provide a comprehensive property profile:\n\n{results_str}"
            )
            return combined_analysis.content.strip()
        except Exception as e:
            raise Exception(f"Error combining analyses: {str(e)}")

    def answer_query(self, property_path, query):
        """Answer a specific query about the property"""
        analysis = self.analyze_property(property_path)
        try:
            response = self.agent.run(
                f"Based on the following property analysis, answer this query: {query}\n\nAnalysis: {analysis}"
            )
            return response.content.strip()
        except Exception as e:
            raise Exception(f"Error answering query: {str(e)}")

if __name__ == "__main__":
    agent = MainAnalysisAgent()
    property_path = "/path/to/property"  # Replace with actual property path
    result = agent.analyze_property(property_path)
    print(result)
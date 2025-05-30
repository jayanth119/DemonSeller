from agno.agent import Agent
import os
import sys
import json
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.mainPrompts import Main_prompt
from models.gemini import model
from agents.imageAgent import ImageAnalysisAgent
from agents.videoAgent import VideoAnalysisAgent
from agents.textAgent import TextAnalysisAgent


def clean_json_string(s: str) -> str:
    """
    Remove markdown code fences and extraneous backticks from a JSON string.
    """
    s = re.sub(r"```(?:json)?\n", "", s)
    s = s.replace("```", "")
    return s.strip()


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

    def merge_analyses(self, analyses):
        """
        Merge JSON outputs from image, video, and text analyses into a single cohesive dict.
        If an appliance appears in all three sources, use the minimum reported count; otherwise, sum the counts.
        """
        merged = {
            "rooms": set(),
            "appliances": {},
            "features": set(),
            "Property details": {},
            "Available amenities and facilities": set(),
            "Property rules and restrictions": None,
            "Additional relevant information": set(),
            "layout": None,
            "condition": None,
            "space_quality": None,
            "location_details": set(),
            "Contact information for inquiries": None
        }
        # Collect appliance counts across sources
        appliance_counts = {}
        for src in analyses:
            if not src or not isinstance(src, dict):
                continue
            # rooms
            for r in src.get("rooms", []): merged["rooms"].add(r)
            # features
            for f in src.get("features", []): merged["features"].add(f)
            # property details - only if dict
            property_details = src.get("Property details", {})
            if isinstance(property_details, dict):
                for key, val in property_details.items():
                    merged["Property details"].setdefault(key, val)
            # amenities
            for a in src.get("Available amenities and facilities", []): merged["Available amenities and facilities"].add(a)
            # rules
            if src.get("Property rules and restrictions"):
                merged["Property rules and restrictions"] = src["Property rules and restrictions"]
            # additional info
            for info in src.get("Additional relevant information", []): merged["Additional relevant information"].add(info)
            # layout, condition, space_quality
            if src.get("layout"): merged["layout"] = src["layout"]
            if src.get("condition"): merged["condition"] = src["condition"]
            if src.get("space_quality"): merged["space_quality"] = src["space_quality"]
            # location insights
            for loc in src.get("Nearby landmarks", []): merged["location_details"].add(loc)
            # contact
            if src.get("Contact information for inquiries"):
                merged["Contact information for inquiries"] = src["Contact information for inquiries"]
            # appliances: accumulate counts
            for k, v in src.get("appliances", {}).items():
                appliance_counts.setdefault(k, []).append(v)
        # Apply counting rule: min if appears in all three analyses, else sum
        total_sources = len([src for src in analyses if isinstance(src, dict)])
        for appliance, counts in appliance_counts.items():
            if len(counts) == total_sources:
                merged["appliances"][appliance] = min(counts)
            else:
                merged["appliances"][appliance] = sum(counts)
        # Convert sets back to lists
        merged["rooms"] = list(merged["rooms"])
        merged["features"] = list(merged["features"])
        merged["Available amenities and facilities"] = list(merged["Available amenities and facilities"])
        merged["Additional relevant information"] = list(merged["Additional relevant information"])
        merged["location_details"] = list(merged["location_details"])
        return merged

    def analyze_property(self, property_path):
        """Analyze a property using all available data sources (images, video, text)."""
        raw_results = []
        p = Path(property_path)

        def process_raw(raw):
            if isinstance(raw, str):
                cleaned = clean_json_string(raw)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}\nRaw content:\n{cleaned}")
                    return {}
            return raw if isinstance(raw, dict) else {}

        # Images
        imgs = list((p / "images").glob("**/*.*")) if (p / "images").exists() else list(p.glob("*.jp*g")) + list(p.glob("*.png"))
        if imgs:
            try:
                raw = self.image_agent.analyze_images(str(p / "images")) if (p / "images").exists() else self.image_agent.analyze_images(property_path)
                raw_results.append(process_raw(raw))
            except Exception as e:
                print(f"Error in image analysis: {e}")
        # Video
        vid_dir = p / "videos"
        video_files = []
        if vid_dir.exists():
            video_files = [f for f in vid_dir.iterdir() if f.suffix.lower() in ('.mp4', '.avi', '.mov')]
        else:
            video_files = [f for f in p.glob('*.mp4')] + [f for f in p.glob('*.mov')] + [f for f in p.glob('*.avi')]
        if video_files:
            try:
                raw = self.video_agent.analyze_video(str(video_files[0]))
                raw_results.append(process_raw(raw))
            except Exception as e:
                print(f"Error in video analysis: {e}")
        # Text
        txt_dir = p / "text"
        text_files = []
        if txt_dir.exists():
            text_files = [f for f in txt_dir.iterdir() if f.suffix.lower() in ('.txt', '.doc', '.docx', '.pdf')]
        else:
            text_files = [f for f in p.glob('*.txt')] + [f for f in p.glob('*.pdf')]
        if text_files:
            try:
                raw = self.text_agent.analyze_text(str(text_files[0]))
                raw_results.append(process_raw(raw))
            except Exception as e:
                print(f"Error in text analysis: {e}")
        # Merge and generate
        merged = self.merge_analyses(raw_results)
        profile = self.agent.run(
            f"Create a comprehensive property profile based on this merged data: {json.dumps(merged)}"
        )
        return profile.content.strip()


if __name__ == "__main__":
    agent = MainAnalysisAgent()
    property_path = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7"
    print(agent.analyze_property(property_path))

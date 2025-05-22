from agno.agent import Agent
import os
import sys
import time 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.textTool import load_txt_files_from_directory
from prompts.textPrompts import text_Prompt
from models.gemini import model
text_Agent = Agent(
    model = model,
    markdown=False,
    description=text_Prompt,

    
)


if __name__ == "__main__":
    directory_path = "/Users/jayanth/Documents/GitHub/DemonSeller/Flats/flat7"
    # this now returns one big string, not a list
    text = load_txt_files_from_directory(directory_path)

    # you can either pass a raw string...
    response = text_Agent.run(text)

    # ...or, if your prompt requires a list of messages, wrap it:
    # response = text_Agent.run([{"role": "user", "content": text}])

    print(response.content)

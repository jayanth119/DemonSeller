from agents.imageAgent import imageAgent
from agents.textAgent import text_Agent
from agents.videoAgent import videoAgent
from agno.team.team import Team
from models.gemini import model

flat_seller_team = Team(
    name = "FlatSeller",
    mode = "route",
    model = model , 
    show_tool_calls=True,
    markdown=True,
    description = "Your assiant for flat seller , he will give data  of the flat according that you have behave  ",
    instructions = [
        ],
    members=[
        imageAgent,
        text_Agent,
        videoAgent,
    ],
    show_members_responses=False,
    enable_agentic_context=True,
    enable_team_history=True,
    num_of_interactions_from_history=5,
)

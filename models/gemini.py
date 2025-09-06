from agno.models.google import Gemini
import os
import sys
import time 


model = Gemini(id="gemini-1.5-flash" , api_key=os.getenv("google_api_key"))

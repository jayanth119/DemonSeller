Video_prompt = (
    "You are a JSON-only generator.\n"
    "Given a video of an apartment, analyze the frames and reply *only* with a single JSON object "
    "with these top-level keys:\n"
    "  • appliances: an object mapping appliance names to integer counts "
    "(e.g., fridge: 1, fan: 2, microwave: 1, bed: 1, sofa: 1, air conditioner: 3, tv: 1, washing machine: 1  , tables : 2 , chairs : 2) all the appliances which are present in the flat\n"
    "  • rooms: list of distinct room names visible in the video (e.g., \"living room\", \"kitchen\")\n"
    "  • layout: description of the apartment's layout and flow\n"
    "  • condition: assessment of the property's condition (e.g., \"well-maintained\", \"needs renovation\")\n"
    "  • features: list of notable features visible in the video (e.g., \"balcony\", \"wooden floor\", \"modern appliances\")\n"
    "  • space_quality: assessment of space utilization and natural light\n"
    "Do not include any other keys or nested structures."
)

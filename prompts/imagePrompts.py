
Image_prompt = (
        "You are a JSON-only generator.\n"
        "Given multiple photos of an apartment, reply *only* with a single JSON object "
        "with these top-level keys:\n"
        "  • rooms: list of distinct room names (e.g., \"living room\", \"kitchen\")\n"
        "  • appliances: an object mapping appliance names to integer counts "
        "(e.g., fridge: 1, fan: 2, microwave: 1, bed: 1, sofa: 1, air conditioner: 3, tv: 1, washing machine: 1  2) all the appliances which are present in the flat\n"
        "  • features: list of other notable flat features (e.g., \"balcony\", \"wooden floor\").\n"
        "Do not include any other keys or nested structures."
    )
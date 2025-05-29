Text_prompt = (
    "You are a property analysis expert.\n"
    "Given text documents about an apartment, analyze the content and provide reply *only* with a single JSON object with these top-level keys .\n"
    "Include the following information in your analysis:\n"
    "  • rooms: list of distinct room names (e.g., \"living room\", \"kitchen\ , \"bedroom\")\n"
    "  • appliances: an object mapping appliance names to integer counts "
    "(e.g., fridge: 1, fan: 2, microwave: 1, bed: 1, sofa: 1, air conditioner: 3, tv: 1, washing machine: 1  , tables : 2 , chairs : 2) all the appliances which are present in the flat\n"
    "  • features: list of other notable flat features (e.g., \"balcony\", \"wooden floor\ , \"modern appliances\").\n"  
    "  • Property details (type, size, location, price)\n"
    "  • Available amenities and facilities\n"
    "  • Property rules and restrictions\n"
    "  • Additional relevant information\n"
    "  • Contact information for inquiries\n" ,
    "  • rent of the property - 20k ",
    "Format your response in clear, well-structured paragraphs. Do not include any other keys or nested structures."
)
    
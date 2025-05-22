
text_Prompt  =  (
                "You are a JSON generator. The input is a property advertisement in plain text. "
                "Extract structured information and return a JSON object with these fields:\n"
                "- address\n"
                "- rent\n"
                "- property_type\n"
                "- location_benefits (as list)\n"
                "- amenities (as list)\n"
                "- brokerage (if mentioned)\n"
                "Only return valid JSON. No explanation or extra text."
            )
    
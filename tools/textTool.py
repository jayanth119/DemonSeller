from agno.tools import tool
import os

# @tool(show_result=True, stop_after_tool_call=True)
def load_txt_files_from_directory(directory_path):
    """
    Load text files from a directory and return their combined content as a single string.
    """
    if not os.path.isdir(directory_path):
        raise ValueError(f"{directory_path} is not a valid directory.")
    txt_files = [
        os.path.join(directory_path, file)
        for file in os.listdir(directory_path)
        if file.lower().endswith(".txt") and os.path.isfile(os.path.join(directory_path, file))
    ]
    if not txt_files:
        raise ValueError(f"No .txt files found in {directory_path}")
    combined_text = ""
    
    for file_path in txt_files:
        with open(file_path, "r", encoding="utf-8") as f:
            combined_text += f.read() + "\n"
    print(combined_text)
    return combined_text






# @tool(show_result=True, stop_after_tool_call=True)
# def load_txt_files_from_directory(directory_path):
#     """
#     Load text files from a directory and return their combined content as a single string.
#     """
#     api_key = "AIzaSyCjz77h8Q3s3sa9XFx4jWm9qNio23ttxe8" 
#     txt_tool = TextTool(api_key=api_key, model="gemini", folder=directory_path)
#     txt_summaries = txt_tool.analyze_folder()
#     return  json.dumps(txt_summaries, indent=2)




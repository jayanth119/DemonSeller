from agno.tools import tool
import os

@tool(description="Load and process text files from a directory")
def load_txt_files_from_directory(directory_path: str):
    """
    Load text files from a directory and return their combined content.
    
    Args:
        directory_path (str): Path to directory containing text files
        
    Returns:
        str: Combined content of all text files
    """
    if not os.path.isdir(directory_path):
        return f"Invalid directory: {directory_path}"
    
    txt_files = []
    for file in os.listdir(directory_path):
        if file.lower().endswith(".txt"):
            full_path = os.path.join(directory_path, file)
            if os.path.isfile(full_path):
                txt_files.append(full_path)
    
    if not txt_files:
        return f"No .txt files found in {directory_path}"
    
    combined_text = ""
    for file_path in txt_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read().strip()
                if file_content:
                    combined_text += f"\n--- Content from {os.path.basename(file_path)} ---\n"
                    combined_text += file_content + "\n"
        except Exception as e:
            combined_text += f"\n--- Error reading {os.path.basename(file_path)}: {str(e)} ---\n"
    
    return combined_text if combined_text else "No readable content found in text files"

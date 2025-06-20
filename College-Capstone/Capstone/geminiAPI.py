import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the API key
genai.configure(api_key=os.getenv("GEMINI_API"))

# Define model settings
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Initialize the Gemini model with an updated system instruction
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    system_instruction="Your task is to add short, concise comments to code converted from one programming language to another. Keep comments brief, typically 3-5 words, and avoid lengthy explanations.",
)

def add_ai_comments(code, target_language):
    """
    Sends converted code to Gemini API and returns commented code without language identifiers.
    
    :param code: The code to be commented, as a string.
    :param target_language: The language of the code ('python' or 'c++').
    :return: Commented code as a string.
    """
    chat_session = model.start_chat(history=[])  # Start a new chat session
    
    # Construct the prompt based on the target language with emphasis on brevity
    if target_language.lower() == 'python':
        prompt = f"Add short, concise comments (3-5 words max) to this Python code:\n{code}"
    elif target_language.lower() == 'c++':
        prompt = f"Add short, concise comments (3-5 words max) to this C++ code:\n{code}"
    else:
        raise ValueError("Unsupported language for commenting")

    response = chat_session.send_message(prompt)
    # Clean up the response by removing code block markers and language identifiers
    commented_code = response.text
    # Remove common code block markers and language tags
    for marker in ["```cpp", "```python", "```c++", "```", "cpp", "python"]:
        commented_code = commented_code.replace(marker, "").strip()
   
    commented_code = commented_code.strip()
    return commented_code 
# test_openai_key.py
import os
from openai import OpenAI

# Make sure your API key is set in environment variables
# Windows (cmd): setx OPENAI_API_KEY "YOUR_API_KEY"
# Mac/Linux (bash): export OPENAI_API_KEY="YOUR_API_KEY"

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set!")

client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, just testing my API key!"}],
        max_tokens=50
    )
    print("✅ API key works! Here's a test response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("❌ Something went wrong:")
    print(e)

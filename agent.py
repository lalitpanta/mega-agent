
import json
import threading
import os
from dotenv import load_dotenv
from openai import OpenAI
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    raise ValueError("❌ OPENROUTER_API_KEY not found in .env file!")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# Global variables for business info
business_info = {}
business_context = "You are a helpful AI assistant."

def load_business_context():
    """Load business information and create context"""
    global business_info, business_context
    try:
        with open("aboutbusiness.json", "r") as f:
            business_info = json.load(f)
        business_context = f"""You are a helpful AI assistant representing this business:

BUSINESS NAME: {business_info.get('business_name', 'N/A')}
CEO: {business_info.get('ceo', 'N/A')}
INDUSTRY: {business_info.get('industry', 'N/A')}
DESCRIPTION: {business_info.get('description', 'N/A')}
SERVICES: {', '.join(business_info.get('services', []))}
MISSION: {business_info.get('mission', 'N/A')}
TARGET AUDIENCE: {business_info.get('target_audience', 'N/A')}
CONTACT: {business_info.get('contact', 'N/A')}
ADDITIONAL INFO: {business_info.get('additional_info', 'N/A')}

IMPORTANT RULES:
1. Keep responses SHORT and CONCISE (1-3 sentences max)
2. Be sweet and friendly in tone
3. Be logical and to the point
4. Reference business details when relevant
5. Use the business name "{business_info.get('business_name', 'N/A')}" when appropriate
6. NO lengthy explanations - get straight to the point"""
        print(f"\n✓ Business loaded: {business_info.get('business_name', 'N/A')} ({business_info.get('industry', 'N/A')})")
        print("=" * 60)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        business_context = "You are a helpful AI assistant."
        print(f"\n⚠ No business info found. Edit aboutbusiness.json with your business details.")

class BusinessFileHandler(FileSystemEventHandler):
    """Watch for changes to aboutbusiness.json"""
    def on_modified(self, event):
        if event.src_path.endswith('aboutbusiness.json'):
            print("\n📝 Detected changes to aboutbusiness.json - reloading...")
            load_business_context()

# Load business context on startup
load_business_context()

# Start file watcher in background thread
def start_file_watcher():
    observer = Observer()
    observer.schedule(BusinessFileHandler(), path='.', recursive=False)
    observer.start()

watcher_thread = threading.Thread(target=start_file_watcher, daemon=True)
watcher_thread.start()

# Load existing chat history
try:
    with open("chat_history.json", "r") as f:
        conversation = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    conversation = []

while True:
    user = input("You: ")

    conversation.append({
        "role": "user",
        "content": user
    })

    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "system", "content": business_context}] + conversation
    )

    reply = response.choices[0].message.content

    print("Agent:", reply)

    conversation.append({
        "role": "assistant",
        "content": reply
    })

    # Save chat history to JSON
    with open("chat_history.json", "w") as f:
        json.dump(conversation, f, indent=2)


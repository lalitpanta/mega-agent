import json
import threading
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

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
1. ALWAYS keep responses to 1-2 sentences maximum
2. Be direct, logical, and helpful
3. Avoid unnecessary words, emojis (except when truly helpful), or fluff
4. Don't be overly cheerful or annoying - be professional but friendly
5. Reference business details only when directly relevant
6. Give quick, straight-to-the-point answers
7. No repetition or explaining obvious things
8. If the question is outside business scope, politely decline"""
        print("✅ Business context loaded!")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        business_context = "You are a helpful AI assistant."
        print(f"⚠️  Error loading business info: {e}")

class BusinessFileHandler(FileSystemEventHandler):
    """Watch for changes to aboutbusiness.json"""
    def on_modified(self, event):
        if event.src_path.endswith('aboutbusiness.json'):
            print("📝 Detected changes to aboutbusiness.json - reloading...")
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

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    global conversation
    
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    # Add user message to conversation
    conversation.append({
        "role": "user",
        "content": user_message
    })
    
    # Get AI response
    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "system", "content": business_context}] + conversation
    )
    
    ai_message = response.choices[0].message.content
    
    # Add assistant message to conversation
    conversation.append({
        "role": "assistant",
        "content": ai_message
    })
    
    # Save chat history
    with open("chat_history.json", "w") as f:
        json.dump(conversation, f, indent=2)
    
    return jsonify({
        'message': ai_message,
        'conversation': conversation
    })

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify({'conversation': conversation})

@app.route('/clear', methods=['POST'])
def clear_history():
    global conversation
    conversation = []
    with open("chat_history.json", "w") as f:
        json.dump(conversation, f, indent=2)
    return jsonify({'status': 'cleared'})

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mega AI Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px;
            min-height: 100vh;
        }
        
        .container {
            width: 100%;
            max-width: 600px;
            height: 90vh;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            border-bottom: 3px solid #5568d3;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .header h1 {
            font-size: 26px;
            margin-bottom: 5px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        
        .header p {
            font-size: 12px;
            opacity: 0.95;
            font-weight: 500;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            background: #f8f9fa;
        }
        
        .message {
            display: flex;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 15px;
            word-wrap: break-word;
            line-height: 1.5;
            font-size: 14px;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 0;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
        }
        
        .message.assistant .message-content {
            background: #f0f2f5;
            color: #2c3e50;
            border-bottom-left-radius: 0;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        }
        
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
            background: #e9ecef;
            border-radius: 15px;
            width: fit-content;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            background: #999;
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes bounce {
            0%, 60%, 100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }
        
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #ddd;
            display: flex;
            gap: 10px;
        }
        
        .input-group {
            flex: 1;
            display: flex;
            gap: 10px;
        }
        
        input[type="text"] {
            flex: 1;
            border: 2px solid #ddd;
            border-radius: 25px;
            padding: 12px 20px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        
        input[type="text"]:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button.clear-btn {
            background: #dc3545;
            padding: 10px 15px;
            font-size: 12px;
        }
        
        button.clear-btn:hover {
            box-shadow: 0 5px 15px rgba(220, 53, 69, 0.4);
        }
        
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
            text-align: center;
        }
        
        .empty-state svg {
            width: 80px;
            height: 80px;
            margin-bottom: 20px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>� Mega AI Assistant</h1>
            <p>Smart, Quick & Logical Responses</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="empty-state">
                <div>🤖</div>
                <h2>Welcome to Mega AI</h2>
                <p>Ask quick questions & get instant answers</p>
            </div>
        </div>
        
        <div class="input-area">
            <div class="input-group">
                <input 
                    type="text" 
                    id="messageInput" 
                    placeholder="Type your message..." 
                    autocomplete="off"
                >
                <button onclick="sendMessage()">Send</button>
            </div>
            <button class="clear-btn" onclick="clearHistory()">Clear</button>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        let isLoading = false;
        
        // Load chat history on page load
        window.addEventListener('load', loadHistory);
        
        async function loadHistory() {
            try {
                const response = await fetch('/history');
                const data = await response.json();
                
                if (data.conversation && data.conversation.length > 0) {
                    chatMessages.innerHTML = '';
                    data.conversation.forEach(msg => {
                        displayMessage(msg.content, msg.role);
                    });
                    scrollToBottom();
                }
            } catch (error) {
                console.error('Error loading history:', error);
            }
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            
            if (!message || isLoading) return;
            
            // Remove empty state if present
            if (chatMessages.querySelector('.empty-state')) {
                chatMessages.innerHTML = '';
            }
            
            // Display user message
            displayMessage(message, 'user');
            messageInput.value = '';
            isLoading = true;
            
            // Show typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant';
            typingDiv.innerHTML = `
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            chatMessages.appendChild(typingDiv);
            scrollToBottom();
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // Remove typing indicator
                    typingDiv.remove();
                    
                    // Display AI response
                    displayMessage(data.message, 'assistant');
                } else {
                    typingDiv.remove();
                    displayMessage('Error: ' + (data.error || 'Failed to get response'), 'assistant');
                }
            } catch (error) {
                typingDiv.remove();
                displayMessage('Error: ' + error.message, 'assistant');
            } finally {
                isLoading = false;
                scrollToBottom();
                messageInput.focus();
            }
        }
        
        function displayMessage(content, role) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + role;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            messageDiv.appendChild(contentDiv);
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        async function clearHistory() {
            if (confirm('Are you sure you want to clear all chat history?')) {
                try {
                    await fetch('/clear', { method: 'POST' });
                    chatMessages.innerHTML = `
                        <div class="empty-state">
                            <div>🤖</div>
                            <h2>Welcome to Mega AI</h2>
                            <p>Ask quick questions & get instant answers</p>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error clearing history:', error);
                }
            }
        }
        
        // Allow sending message with Enter key
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !isLoading) {
                sendMessage();
            }
        });
        
        // Focus input on load
        messageInput.focus();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Starting AI Chatbot Server...")
    print(f"📱 Open your browser to: http://0.0.0.0:{port}")
    print("Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=port, debug=False)

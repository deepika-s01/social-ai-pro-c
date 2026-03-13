from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import random
from groq import Groq

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION ---
client = Groq(api_key="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") 

def init_db():
    conn = sqlite3.connect('socialai.db')
    cursor = conn.cursor()
    # 1. Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT)''')
    
    # 2. Scheduled posts table
    cursor.execute('''CREATE TABLE IF NOT EXISTS posts 
                      (id INTEGER PRIMARY KEY, platform TEXT, content TEXT, date TEXT)''')
    
    # 3. NEW: History table (Add this line!)
    cursor.execute('''CREATE TABLE IF NOT EXISTS history 
                      (id INTEGER PRIMARY KEY, topic TEXT, platform TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# Call the function to apply changes
init_db()

# --- 2. AUTHENTICATION ROUTES ---

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "User created successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Return the user's name so the dashboard can say "Welcome, Name!"
            return jsonify({"status": "success", "user": {"name": user[0]}})
        else:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 3. DASHBOARD GENERATOR ROUTE ---
import urllib.parse  # Standard library to help with URL encoding

@app.route('/generate', methods=['POST', 'OPTIONS'])
def generate_ai_content():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    data = request.json
    topic = data.get('topic', 'General Strategy')
    platform = data.get('platform', 'Instagram')
    tone = data.get('tone', 'Professional')
    
    try:
        # --- AGENT 1: THE CREATIVE WRITER ---
        writer_response = client.chat.completions.create(
            messages=[{"role": "user", "content": f"Draft a {tone} post for {platform} about {topic}."}],
            model="llama-3.3-70b-versatile",
        )
        initial_draft = writer_response.choices[0].message.content

        # --- AGENT 2: THE VIRAL STRATEGIST (THE CRITIC) ---
        # Forces a dynamic heading and hashtags based on the unique draft
        # --- AGENT 2: THE VIRAL STRATEGIST ---
        # In your generate_ai_content route, update the critic prompt:
        # --- AGENT 2: THE UNIVERSAL STRATEGIST ---
        critic_prompt = f"""
Act as an expert Social Media Strategist. Review this draft: "{initial_draft}"

Improve it for {platform} by following these strict formatting rules:
1. 💡 HEADING: Create a catchy, unique BOLD heading at the very top that summarizes the topic '{topic}'.
2. 📝 BODY: Refine the text for flow and engagement. Ensure there is a clear empty line between paragraphs.
3. ✨ EMOJIS: Add 3-5 relevant emojis to make the post visually engaging but keep it professional.
4. #️⃣ HASHTAGS: Place exactly 5 trending hashtags related to '{topic}' at the very bottom.

Return ONLY the final formatted post. Do not include 'Here is your post' or any intro text.
"""
        
        refinement_response = client.chat.completions.create(
            messages=[{"role": "user", "content": critic_prompt}],
            model="llama-3.3-70b-versatile",
        )
        final_caption = refinement_response.choices[0].message.content

        # --- DYNAMIC FREE IMAGE GENERATION ---
        # This uses Pollinations.ai to generate a free AI image based on your topic
        # Encoding ensures the URL is valid even with spaces in the topic
        safe_topic = urllib.parse.quote(f"professional social media graphic for {topic}")
        image_url = f"https://image.pollinations.ai/prompt/{safe_topic}?width=1080&height=1080&nologo=true"

        # --- SAVE TO HISTORY ---
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (topic, platform, content) VALUES (?, ?, ?)", 
                       (topic, platform, final_caption))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success", 
            "caption": final_caption,
            "engagement_score": f"{random.randint(84, 98)}%"
        })

    except Exception as e:
        print(f"Error in Agentic Flow: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/run_agent', methods=['POST'])
def run_social_agent():
    data = request.json
    current_content = data.get('content')
    task = data.get('task')

    # Logic to switch prompts based on the task type
    if task == "SEO Optimize":
        # 🔍 ANALYTICAL PROMPT (Simple, No Rewrite)
        agent_prompt = f"""
        You are the SocialAI SEO Specialist Agent. 
        Analyze this content: "{current_content}"

        Provide a very brief 3-step technical audit:
        1. [SEO SCORE]: (Estimate out of 100)
        2. [KEYWORDS]: (List 3 high-volume technical keywords to include)
        3. [FIX]: (One specific sentence on how to rank better on search)
        
        Keep it purely analytical. Do not rewrite the post.
        """
    else:
        # 🚀 VIRALITY PROMPT (Full Rewrite with Copyable Content)
        agent_prompt = f"""
        You are the SocialAI Viral Strategist Agent. 
        Your Task: {task}
        Content to Process: "{current_content}"

        Step 1: Analyze engagement psychology.
        Step 2: Rewrite for maximum "stopping power" and emotional connection.
        
        Output format:
        [THOUGHT]: Briefly explain the hook change.
        [ACTION]: The fully optimized and rewritten post.
        """

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": agent_prompt}],
            model="llama-3.3-70b-versatile",
        )
        return jsonify({
            "status": "success", 
            "agent_output": response.choices[0].message.content,
            "task_type": task  # Send task type back so JS knows whether to show Copy btn
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 4. AI WRITER TRANSFORM ROUTE ---
@app.route('/transform', methods=['POST', 'OPTIONS'])
def transform_long_content():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    data = request.json
    content = data.get('content', '')
    prompt = f"Transform this into a {data.get('type')}. Use 3 hooks, main content, and hashtags. End with '|||' and a viral analysis. Content: {content}"
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", 
            max_tokens=1000
        )
        full_response = completion.choices[0].message.content
        if "|||" in full_response:
            caption, reason = full_response.split("|||", 1)
        else:
            caption, reason = full_response, "Optimal for engagement."

        return jsonify({
            "status": "success", 
            "transformed_text": caption.strip(),
            "viral_score": random.randint(82, 97),
            "analysis": reason.strip(),
            "suggested_frequency": "Daily updates"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 5. CALENDAR & DATABASE ROUTES ---
# --- 5. CALENDAR & DATABASE ROUTES ---

@app.route('/schedule', methods=['POST'])
def schedule_post():
    data = request.json
    date = data.get('date')
    platform = data.get('platform')
    content = data.get('content')

    if not all([date, platform, content]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        # ✅ FIX: Inserting into 'posts' table (which your /get_posts route uses)
        cursor.execute("INSERT INTO posts (platform, content, date) VALUES (?, ?, ?)", 
                       (platform, content, date))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Post successfully scheduled!"})
    except Exception as e:
        print(f"Schedule Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_posts', methods=['GET'])
def get_posts():
    try:
        conn = sqlite3.connect('socialai.db')
        # Use row_factory to easily convert rows to dictionaries
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute("SELECT id, platform, content, date FROM posts ORDER BY date ASC")
        rows = cursor.fetchall()
        conn.close()
        
        posts = [dict(row) for row in rows]
        return jsonify({"status": "success", "posts": posts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_post', methods=['POST'])
def delete_post():
    try:
        data = request.json
        post_id = data.get('id')
        
        if not post_id:
            return jsonify({"status": "error", "message": "No ID provided"}), 400

        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Post deleted successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
# --- 5.5 HISTORY ROUTES ---
@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, topic, platform, content, timestamp FROM history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        history = [{"id": r[0], "topic": r[1], "platform": r[2], "content": r[3], "time": r[4]} for r in rows]
        return jsonify({"status": "success", "history": history})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/delete_history_item', methods=['POST'])
def delete_history_item():
    try:
        data = request.json
        item_id = data.get('id')
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/clear_all_history', methods=['POST'])
def clear_all_history():
    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 6. INSIGHTS ROUTE ---
@app.route('/get_insights', methods=['GET'])
def get_insights():
    try:
        conn = sqlite3.connect('socialai.db')
        cursor = conn.cursor()
        
        # 1. Get total count
        cursor.execute("SELECT COUNT(*) FROM posts")
        count = cursor.fetchone()[0]
        
        # 2. Get the most frequent platform (Dynamic Top Platform)
        cursor.execute("SELECT platform, COUNT(platform) AS freq FROM posts GROUP BY platform ORDER BY freq DESC LIMIT 1")
        row = cursor.fetchone()
        top_platform = row[0] if row else "Instagram"

        conn.close()

        # 3. Dynamic "Smart Time" Logic
        # We simulate AI analysis by changing the time based on the platform
        time_mapping = {
            "Instagram": "7:45 PM",
            "LinkedIn": "9:15 AM",
            "Twitter": "1:30 PM"
        }
        smart_time = time_mapping.get(top_platform, "6:00 PM")

        return jsonify({
            "status": "success",
            "reach": f"{round(count * 1.2, 1)}K",
            "posts_count": count,
            "smart_time": smart_time,
            "top_platform": top_platform,
            "sentiment": {
                "pos": random.randint(75, 90), 
                "neu": random.randint(5, 15), 
                "neg": random.randint(1, 5)
            }
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    init_db()  # <--- THIS LINE IS THE FIX
    app.run(debug=True, port=5000)
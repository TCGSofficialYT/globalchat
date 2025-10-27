from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
import threading
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session management
socketio = SocketIO(app, cors_allowed_origins="*")

# Chat log
chat_log = []

# Load users from txt file
def load_users():
    users = {}
    if os.path.exists("users.txt"):
        with open("users.txt") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    username, password = line.split(":", 1)
                    users[username] = password
    return users

users = load_users()

# --- Login Page ---
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body { background: #111; color: #0f0; font-family: monospace; padding: 20px; }
        input { padding: 8px; margin: 5px 0; font-family: monospace; }
        button { padding: 8px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h2>Login</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="post">
        Username:<br><input name="username"><br>
        Password:<br><input type="password" name="password"><br>
        <button type="submit">Login</button>
        <p>New user? <a href="{{ url_for('register') }}">Register here</a></p>
    </form>
</body>
</html>
"""

# --- Chat Page ---
CHAT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Global Chat</title>
    <style>
        body { background: #111; color: #0f0; font-family: monospace; padding: 20px; }
        #messages { border: 1px solid #0f0; padding: 10px; height: 300px; overflow-y: scroll; margin-bottom: 10px; }
        input { width: 80%; padding: 8px; font-family: monospace; }
        button { padding: 8px; font-family: monospace; }
    </style>
</head>
<body>
    <h2>🌎 Global Messaging System</h2>
    <p>Logged in as: {{ username }}</p>
    <div id="messages"></div>
    <input id="msg" placeholder="Type a message..." autofocus>
    <button onclick="send()">Send</button>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        const socket = io();
        const messages = document.getElementById('messages');
        const username = "{{ username }}";

        socket.on('connect', () => console.log("Connected"));

        socket.on('chat_log', log => {
            messages.innerHTML = '';
            log.forEach(msg => {
                const div = document.createElement('div');
                div.textContent = msg;
                messages.appendChild(div);
            });
            messages.scrollTop = messages.scrollHeight;
        });

        socket.on('new_message', msg => {
            const div = document.createElement('div');
            div.textContent = msg;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        });

        function send() {
            const input = document.getElementById('msg');
            const text = input.value.trim();
            if (text) {
                socket.emit('message', {user: username, text: text});
                input.value = '';
            }
        }

        document.getElementById('msg').addEventListener('keypress', e => {
            if (e.key === 'Enter') send();
        });
    </script>
</body>
</html>
"""

# --- Registration Page ---
REGISTER_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Register</title>
    <style>
        body { background: #111; color: #0f0; font-family: monospace; padding: 20px; }
        input { padding: 8px; margin: 5px 0; font-family: monospace; }
        button { padding: 8px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h2>Register</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="post">
        Username:<br><input name="username"><br>
        Password:<br><input type="password" name="password"><br>
        <button type="submit">Register</button>
    </form>
</body>
</html>
"""

# --- Flask Routes ---
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            session["username"] = username
            return redirect(url_for("chat"))
        else:
            return render_template_string(LOGIN_PAGE, error="Invalid username or password")
    return render_template_string(LOGIN_PAGE, error=None)

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template_string(CHAT_PAGE, username=session["username"])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users:
            return render_template_string(REGISTER_PAGE, error="Username already exists")
        if not username or not password:
            return render_template_string(REGISTER_PAGE, error="Username and password required")
        users[username] = password
        # Save to users.txt
        with open("users.txt", "a") as f:
            f.write(f"{username}:{password}\n")
        session["username"] = username
        return redirect(url_for("chat"))
    return render_template_string(REGISTER_PAGE, error=None)

# --- SocketIO Handlers ---
@socketio.on('connect')
def on_connect():
    emit('chat_log', chat_log)

@socketio.on('message')
def handle_message(data):
    # data = {user: "Theo", text: "hi"}
    user = data.get("user", "Unknown")
    text = data.get("text", "")
    full_msg = f"[{user}] {text}"
    print(full_msg)
    chat_log.append(full_msg)
    socketio.emit('new_message', full_msg)

# --- Terminal input loop ---
def terminal_loop():
    while True:
        msg = input("Say something: ")
        full_msg = f"[SERVER] {msg}"
        print(full_msg)
        chat_log.append(full_msg)
        socketio.emit('new_message', full_msg)

if __name__ == "__main__":
    threading.Thread(target=terminal_loop, daemon=True).start()
    socketio.run(app, host="127.0.0.1", port=5000)

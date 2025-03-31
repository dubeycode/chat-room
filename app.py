from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
import sqlite3
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "jkhlgfsjhd"
socketio = SocketIO(app)

# Create Database Table
def create_table():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            code TEXT PRIMARY KEY,
            messages TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM rooms WHERE code = ?", (code,))
        existing_code = cursor.fetchone()
        conn.close()
        if not existing_code:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == 'POST':
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        if join and not code:
            return render_template("home.html", error="Please enter the room code", code=code, name=name)

        room = code
        if create:
            room = generate_unique_code(4)
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO rooms (code, messages) VALUES (?, ?)", (room, "[]"))
            conn.commit()
            conn.close()
        else:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM rooms WHERE code = ?", (code,))
            existing_room = cursor.fetchone()
            conn.close()
            if not existing_room:
                return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))
    
    return render_template("home.html")

@app.route("/room")
def room():
    room_code = session.get("room")
    if not room_code or not session.get("name"):
        return redirect(url_for("home"))
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT messages FROM rooms WHERE code = ?", (room_code,))
    result = cursor.fetchone()
    conn.close()
    
    messages = eval(result[0]) if result and result[0] else []
    return render_template("room.html", code=room_code, messages=messages)

@socketio.on("message")
def message(data):
    room = session.get("room")
    if not room:
        return
    
    content = {"name": session.get("name"), "message": data["data"]}
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT messages FROM rooms WHERE code = ?", (room,))
    result = cursor.fetchone()
    messages = eval(result[0]) if result and result[0] else []
    messages.append(content)
    
    cursor.execute("UPDATE rooms SET messages = ? WHERE code = ?", (str(messages), room))
    conn.commit()
    conn.close()
    
    send(content, to=room)

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    send({"name": name, "message": "has left the room"}, to=room)

if __name__ == "__main__":
    socketio.run(app, debug=True)

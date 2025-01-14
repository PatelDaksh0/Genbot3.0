from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from ollama import chat

app = Flask(__name__)
app.config['SECRET_KEY'] = '31b946294fb505b1aa3a43da088ee8cd'  # Replace with your generated secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    chat_history = db.Column(db.Text, nullable=True)

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('chat'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/chat', methods=['GET', 'POST'], endpoint='chat')
def chat_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.filter_by(id=session['user_id']).first()
    if request.method == 'POST':
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        try:
            # Generate bot response using ollama
            response = chat(model='llama3.2', messages=[{'role': 'user', 'content': user_message}])
            bot_message = response['message']['content']
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        # Save chat history
        if user.chat_history:
            user.chat_history += f"\nUser: {user_message}\nBot: {bot_message}"
        else:
            user.chat_history = f"User: {user_message}\nBot: {bot_message}"
        db.session.commit()
        
        return jsonify({"response": bot_message})
    return render_template('index.html', chat_history=user.chat_history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(id=session['user_id']).first()
    user.chat_history = None
    db.session.commit()
    return jsonify({"response": "Chat history cleared"})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
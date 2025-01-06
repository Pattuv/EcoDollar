from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = "tsaslc2025"

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Gmail SMTP server
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Your Gmail username (stored as environment variable)
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Your Gmail password (stored as environment variable)
app.config['MAIL_DEFAULT_SENDER'] = 'ecodollarformsender@gmail.com'   # Default sender email

mail = Mail(app)

# Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_NOTIFICATIONS"] = False
db = SQLAlchemy(app)

# Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Routes

@app.route("/submit_recycling", methods=["POST"])
def submit_recycling():
    if "username" not in session:
        return redirect(url_for('auth'))  # Ensure user is logged in

    username = session["username"]  # Get the logged-in username
    materials = request.form.getlist("materials")
    weight = request.form["weight"]
    location = request.form["location"]
    description = request.form["description"]
    proof_file = request.files["proof"]

    try:
        # Compose email
        msg = Message(
            "New Recycling Submission",
            recipients=["ecodollara@gmail.com"]  # Admin email
        )
        msg.html = f"""
        <h2>Recycling submission from user: {username}</h2>
        <p><strong>Materials:</strong> {', '.join(materials)}</p>
        <p><strong>Weight:</strong> {weight} grams</p>
        <p><strong>Drop-off Location:</strong> {location}</p>
        <p><strong>Description:</strong> {description}</p>
        <p>Please review and validate this submission:</p>
        <a href="{url_for('dashboard', username=username, weight=weight, _external=True)}" style="text-decoration:none; padding:10px 20px; color:white; background-color:green; border-radius:5px;">Accept</a>
        <a href="{url_for('dashboard', _external=True)}" style="text-decoration:none; padding:10px 20px; color:white; background-color:red; border-radius:5px; margin-left:10px;">Decline</a>
        """

        # Attach the proof file (image or PDF)
        if proof_file:
            msg.attach(
                secure_filename(proof_file.filename),
                proof_file.content_type,
                proof_file.read()
            )

        # Send email to the admin
        mail.send(msg)

        return redirect(url_for('thank_you'))
    except Exception as e:
        print(f"Error: {e}")
        print(os.getenv('MAIL_USERNAME'))
        print(os.getenv('MAIL_PASSWORD'))
        return f"Error: {e}"



@app.route("/thank_you")
def thank_you():
    return render_template('thanks.html')

@app.route("/form")
def form():
    return render_template('form.html')

@app.route("/auth")
def auth():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template('auth.html')

@app.route("/login", methods=["POST"])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('auth.html', error="Invalid username or password.")

@app.route("/register",  methods=["POST"])
def register():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    
    if user:
        return render_template("auth.html", error="This username is already taken. Please choose another.")
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('dashboard'))

@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('home'))

@app.route("/logout")
def logout():
    session.pop('username',None)
    return redirect(url_for('home'))

@app.route("/")
def home():
    return render_template('home.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')

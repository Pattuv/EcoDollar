from flask import Flask, render_template, request, redirect, session, url_for
from flask_migrate import Migrate
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
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD') 
app.config['MAIL_DEFAULT_SENDER'] = 'ecodollarformsender@gmail.com'  

mail = Mail(app)

# Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_NOTIFICATIONS"] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'user' 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(225), nullable=False)
    total_recycled = db.Column(db.Integer, default=0)  
    points = db.Column(db.Integer, default=0)  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_recycling(self, weight):
        """Update total recycled and points when a recycling submission is made"""
        self.total_recycled += weight
        self.points += weight // 100 
        db.session.commit()


# Routes

@app.route("/submit_recycling", methods=["POST"])
def submit_recycling():
    if "username" not in session:
        return redirect(url_for('auth')) 

    username = session["username"] 
    materials = request.form.getlist("materials")
    weight = int(request.form["weight"]) 
    location = request.form["location"]
    description = request.form["description"]
    email = request.form["email"]  
    proof_file = request.files["proof"]

    try:
        # Compose email to admin
        msg = Message(
            "New Recycling Submission",
            recipients=["ecodollara@gmail.com"] 
        )
        msg.html = f"""
        <h2>Recycling submission from user: {username}</h2>
        <p><strong>Materials:</strong> {', '.join(materials)}</p>
        <p><strong>Weight:</strong> {weight} grams</p>
        <p><strong>Drop-off Location:</strong> {location}</p>
        <p><strong>Description:</strong> {description}</p>
        <p><strong>Submitter's Email:</strong> {email}</p>
        <p>Please review and validate this submission:</p>
        <a href="{url_for('accept', username=username, weight=weight, email=email, _external=True)}" style="text-decoration:none; padding:10px 20px; color:white; background-color:green; border-radius:5px;">Accept</a>

        <!-- Decline Form -->
        <form action="{url_for('decline', _external=True)}" method="POST" style="display:inline;">
            <label for="decline">Send a Decline Message if you are declining:</label>
            <textarea name="decline" required></textarea>
            <input type="hidden" name="username" value="{username}">
            <input type="hidden" name="email" value="{email}">
            <button type="submit" style="padding:10px 20px; color:white; background-color:red; border-radius:5px; margin-left:10px;">Decline</button>
        </form>
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
        return f"Error: {e}"



@app.route("/accept")
def accept():
    # Get the username, weight, and email from the URL query parameters
    username = request.args.get("username")
    weight = int(request.args.get("weight"))
    email = request.args.get("email")

    if not username or weight <= 0 or not email:
        return "Invalid submission data", 400


    user = User.query.filter_by(username=username).first()

    if user:

        user.total_recycled += weight
        user.points += weight // 10  
        db.session.commit()


        confirmation_msg = Message(
            "Recycling Submission Accepted",
            recipients=[email] 
        )
        confirmation_msg.html = f"""
        <h2>{username}, your recycling submission has been accepted!</h2>
        <p>We are happy to inform you that your recycling submission of {weight} grams has been successfully accepted.</p>
        <p>You have earned {weight // 10} points for your submission. Keep up the good work!</p>
        <p>Thank you for helping us recycle!</p>
        <p>Best Regards, EcoDollar Team.</p>
        """

        mail.send(confirmation_msg)


        return render_template('validate.html')
    else:
        return "User not found", 404


@app.route('/decline', methods=["POST"])
def decline():
    # Get the decline message and other parameters from the form
    decline_message = request.form.get('decline')
    username = request.form.get("username")
    email = request.form.get("email")

    # Send the decline confirmation message
    confirmation_msg = Message(
        "Recycling Submission Declined",
        recipients=[email] 
    )
    confirmation_msg.html = f"""
    <h2>Sorry {username}, your form was declined.</h2>
    <p>Here's why:</p>
    <p>Admin Said: {decline_message}</p>
    <p>Please review this and resubmit the form so it meets all requirements.</p>   
    <p>Best Regards, EcoDollar Team.</p>
    """
    mail.send(confirmation_msg)

    # Redirect to the validation page
    return render_template('validate.html')




@app.route("/thank_you")
def thank_you():
    if "username" in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            return render_template('thanks.html', username=user.username, total_recycled=user.total_recycled, points=user.points)
    return redirect(url_for('home'))

@app.route("/form")
def form():
    if "username" in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            return render_template('form.html')
    return redirect(url_for('home'))

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
        user = User.query.filter_by(username=session['username']).first()
        if user:
  
            rank = db.session.query(User).filter(User.total_recycled > user.total_recycled).count() + 1
            
            return render_template(
                'dashboard.html', 
                username=user.username, 
                total_recycled=user.total_recycled, 
                points=user.points, 
                rank=rank
            )
    return redirect(url_for('home'))



@app.route("/logout")
def logout():
    session.pop('username',None)
    return redirect(url_for('home'))

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/about")
def about():
    return render_template('about.html')




@app.route('/leaderboard')
def leaderboard():
    if "username" in session:
        user = User.query.filter_by(username=session['username']).first()
        top_users = User.query.order_by(User.total_recycled.desc()).limit(50).all()
        if user:
            rank = db.session.query(User).filter(User.total_recycled > user.total_recycled).count() + 1
            return render_template('leaderboard.html', users=top_users, rank=rank)
    return redirect(url_for('sharedboard'))
    
@app.route('/ecodollarleaderboard')
def sharedboard():
    top_users = User.query.order_by(User.total_recycled.desc()).limit(50).all()
    return render_template('sharedboard.html', users=top_users)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')

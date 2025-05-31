#app.py
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from story_utils import generate_caption, generate_story, speak_story
from PIL import Image
import sqlite3
import os
import random
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === App Configuration ===
app = Flask(__name__)
app.secret_key = "supersecretkey"

SENDER_EMAIL = "narrifyotp@gmail.com"
SENDER_PASS = "pmrlwcxmtgkhatcb"

DB_PATH = "users.db"

# === Email OTP ===
def send_otp_email(recipient, otp):
    message = MIMEMultipart("alternative")
    message["Subject"] = "Narrify Email Verification OTP"
    message["From"] = SENDER_EMAIL
    message["To"] = recipient

    html = f"""
    <html>
    <body>
      <h2>Verify Your Email</h2>
      <p>Use the following OTP to complete your registration:</p>
      <h1 style='color:#ff2c2c'>{otp}</h1>
      <p>This OTP is valid for 5 minutes.</p>
    </body>
    </html>
    """
    message.attach(MIMEText(html, "html"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, recipient, message.as_string())

# === DB Setup ===
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                image_path TEXT,
                caption TEXT,
                story TEXT,
                language TEXT,
                mode TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()


# === Flask-Login ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

    @staticmethod
    def get_by_id(user_id):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
            row = c.fetchone()
            return User(id_=row[0], username=row[1]) if row else None

    @staticmethod
    def get_by_username(username):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, username FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            return User(id_=row[0], username=row[1]) if row else None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# === Routes ===

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    language = request.form.get("language", "en")
    caption = story = None
    image_uploaded = False

    if request.method == "POST":
        file = request.files["image"]
        mode = request.form.get("mode", "story")

        if file:
            upload_path = os.path.join("uploads", "temp.png")
            os.makedirs("uploads", exist_ok=True)
            file.save(upload_path)

            img = Image.open(upload_path)
            img.thumbnail((800, 800))
            img.save("static/preview.png")

            image_uploaded = True
            caption = generate_caption(upload_path, language)
            story = generate_story(caption, mode=mode, language=language)
            speak_story(story, path="output.wav", language=language)
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO history (user_id, image_path, caption, story, language, mode) VALUES (?, ?, ?, ?, ?, ?)",
                    (current_user.id, upload_path, caption, story, language, mode)
                )
                conn.commit()

            return render_template("index.html", caption=caption, story=story, audio=True, image_uploaded=image_uploaded)

    return render_template("index.html", image_uploaded=False)

@app.route("/audio")
@login_required
def get_audio():
    return send_file("output.wav", mimetype="audio/wav")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("register"))

        otp = random.randint(100000, 999999)
        session["otp"] = str(otp)
        session["temp_user"] = {
            "username": username,
            "email": email,
            "password": generate_password_hash(password)
        }

        try:
            send_otp_email(email, otp)
            flash("An OTP has been sent to your email. Please verify.")
            return redirect(url_for("verify_otp"))
        except Exception as e:
            flash(f"Error sending email: {e}")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if "otp" not in session or "temp_user" not in session:
        flash("Session expired. Please register again.")
        return redirect(url_for("register"))

    if request.method == "POST":
        entered = request.form["otp"]
        if entered == session["otp"]:
            user = session["temp_user"]
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                              (user["username"], user["email"], user["password"]))
                    conn.commit()
                    flash("Registration successful. Please login.")
                except sqlite3.IntegrityError:
                    flash("Username or email already exists.")
                finally:
                    session.pop("otp", None)
                    session.pop("temp_user", None)
            return redirect(url_for("login"))
        else:
            flash("Incorrect OTP. Try again.")
            return redirect(url_for("verify_otp"))

    return render_template("verify_otp.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = True if request.form.get("remember") else False

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            row = c.fetchone()

        if row and check_password_hash(row[1], password):
            user = User(id_=row[0], username=username)
            login_user(user, remember=remember)
            flash("Logged in successfully.")
            return redirect(url_for("index"))

        flash("Invalid credentials.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)
# === Reset Password from Dashboard ===
def get_email_for_user(username):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        return row[0] if row else None

@app.route("/reset-password-request", methods=["GET", "POST"])
@login_required
def reset_password_request():
    if request.method == "POST":
        otp = random.randint(100000, 999999)
        session["reset_otp"] = str(otp)
        session["reset_email"] = get_email_for_user(current_user.username)

        try:
            send_otp_email(session["reset_email"], otp)
            flash("OTP sent to your registered email.")
            return redirect(url_for("reset_password_verify"))
        except Exception as e:
            flash(f"Error sending OTP: {e}")
            return redirect(url_for("dashboard"))

    return render_template("forgot_password.html")  # reuse form with only email input

@app.route("/reset-password-verify", methods=["GET", "POST"])
@login_required
def reset_password_verify():
    if request.method == "POST":
        entered_otp = request.form.get("otp")
        if entered_otp == session.get("reset_otp"):
            return redirect(url_for("reset_password_final"))

        flash("Incorrect OTP. Try again.")
        return redirect(url_for("reset_password_verify"))

    return render_template("verify_otp.html")

@app.route("/reset-password-final", methods=["GET", "POST"])
@login_required
def reset_password_final():
    if request.method == "POST":
        new_password = request.form["password"]
        email = session.get("reset_email")

        if len(new_password) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for("reset_password_final"))

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE email = ?",
                      (generate_password_hash(new_password), email))
            conn.commit()

        flash("Password updated successfully.")
        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        return redirect(url_for("dashboard"))

    return render_template("reset_password.html")
@app.route("/history")
@login_required
def history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT image_path, caption, story, language, mode, timestamp
            FROM history WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (current_user.id,))
        rows = c.fetchall()

    return render_template("history.html", history=rows)



# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)


import os, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-before-production")
DB = os.path.join(os.path.dirname(__file__), "academy.db")

COURSES = [
    ("Smart Money Concepts (SMC) Foundation", "Master the foundations of institutional market analysis.", 149.00),
    ("SMC Advanced", "Deepen your understanding of liquidity, FVGs, order blocks and execution.", 249.00),
    ("VIP Inner Circle", "Premium community access, live sessions and advanced education.", 399.00),
]

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'student',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS courses(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT,
      price REAL NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS lessons(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      course_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      content TEXT,
      video_url TEXT,
      position INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS enrollments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      created_at TEXT NOT NULL,
      UNIQUE(user_id, course_id)
    );
    CREATE TABLE IF NOT EXISTS progress(
      user_id INTEGER NOT NULL,
      lesson_id INTEGER NOT NULL,
      completed INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(user_id, lesson_id)
    );
    """)
    if con.execute("SELECT COUNT(*) c FROM courses").fetchone()["c"] == 0:
        for c in COURSES:
            con.execute("INSERT INTO courses(title,description,price) VALUES(?,?,?)", c)
        lessons = [
          (1,"Welcome to Dan_FX Academy","How the academy works and how to approach your trading education.","",1),
          (1,"Market Structure","Learn highs, lows, trends and Breaks of Structure (BOS).","",2),
          (1,"Liquidity Sweeps","Understand liquidity pools and sweep concepts.","",3),
          (1,"Fair Value Gaps (FVG)","Learn to identify and contextualize market imbalances.","",4),
          (1,"Order Blocks","Understand supply/demand zones and institutional context.","",5),
          (2,"Advanced Market Narrative","Combining structure and liquidity into a market narrative.","",1),
          (2,"Premium/Discount Arrays","Using dealing ranges for context.","",2),
          (3,"VIP Orientation","Community standards and live session workflow.","",1),
        ]
        con.executemany("INSERT INTO lessons(course_id,title,content,video_url,position) VALUES(?,?,?,?,?)", lessons)
    # Create admin only if it does not exist
    if not con.execute("SELECT 1 FROM users WHERE email=?", ("admin@danfx.local",)).fetchone():
        con.execute("INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)",
                    ("Dan_FX Admin","admin@danfx.local",generate_password_hash("ChangeMe123!"),"admin",datetime.utcnow().isoformat()))
    con.commit(); con.close()

def current_user():
    if not session.get("user_id"): return None
    con=db(); u=con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone(); con.close()
    return u

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "error"); return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        u=current_user()
        if not u or u["role"]!="admin":
            flash("Admin access required.", "error"); return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    con=db(); courses=con.execute("SELECT * FROM courses").fetchall(); con.close()
    return render_template("home.html", courses=courses, user=current_user())

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].lower().strip(); password=request.form["password"]
        if len(password)<8:
            flash("Password must be at least 8 characters.", "error"); return redirect(url_for("register"))
        try:
            con=db(); con.execute("INSERT INTO users(name,email,password,created_at) VALUES(?,?,?,?)",
                (name,email,generate_password_hash(password),datetime.utcnow().isoformat())); con.commit()
            uid=con.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]; con.close()
            session["user_id"]=uid; flash("Welcome to Dan_FX Trading Community!", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
    return render_template("register.html", user=current_user())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        con=db(); u=con.execute("SELECT * FROM users WHERE email=?", (request.form["email"].lower().strip(),)).fetchone(); con.close()
        if u and check_password_hash(u["password"], request.form["password"]):
            session["user_id"]=u["id"]; return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", user=current_user())

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    u=current_user(); con=db()
    enrollments=con.execute("""SELECT e.*, c.title,c.description,c.price FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=?""",(u["id"],)).fetchall()
    all_courses=con.execute("SELECT * FROM courses").fetchall()
    con.close()
    return render_template("dashboard.html", user=u, enrollments=enrollments, courses=all_courses)

@app.route("/course/<int:course_id>")
@login_required
def course(course_id):
    u=current_user(); con=db()
    c=con.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    e=con.execute("SELECT * FROM enrollments WHERE user_id=? AND course_id=? AND status='active'",(u["id"],course_id)).fetchone()
    if not c: con.close(); return "Course not found",404
    if not e and u["role"]!="admin":
        con.close(); flash("Please enroll in this course first.", "error"); return redirect(url_for("checkout", course_id=course_id))
    lessons=con.execute("""SELECT l.*, COALESCE(p.completed,0) completed FROM lessons l LEFT JOIN progress p ON p.lesson_id=l.id AND p.user_id=? WHERE l.course_id=? ORDER BY l.position""",(u["id"],course_id)).fetchall()
    con.close()
    return render_template("course.html", user=u, course=c, lessons=lessons)

@app.route("/checkout/<int:course_id>", methods=["GET","POST"])
@login_required
def checkout(course_id):
    con=db(); c=con.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone(); con.close()
    if not c: return "Course not found",404
    if request.method=="POST":
        # Demo checkout. Replace this block with Stripe/Paystack/Flutterwave server-side verification.
        con=db()
        con.execute("""INSERT INTO enrollments(user_id,course_id,status,created_at) VALUES(?,?, 'active',?)
          ON CONFLICT(user_id,course_id) DO UPDATE SET status='active'""",
          (current_user()["id"],course_id,datetime.utcnow().isoformat()))
        con.commit(); con.close()
        flash("Enrollment activated successfully. Configure a live payment provider before production.", "success")
        return redirect(url_for("course", course_id=course_id))
    return render_template("checkout.html", user=current_user(), course=c)

@app.route("/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    con=db(); con.execute("""INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,1)
      ON CONFLICT(user_id,lesson_id) DO UPDATE SET completed=1""",(current_user()["id"],lesson_id)); con.commit(); con.close()
    return jsonify({"ok":True})

@app.route("/admin")
@admin_required
def admin():
    con=db()
    users=con.execute("SELECT id,name,email,role,created_at FROM users ORDER BY id DESC").fetchall()
    courses=con.execute("SELECT * FROM courses").fetchall()
    enrollments=con.execute("""SELECT e.status,e.created_at,u.name,c.title FROM enrollments e JOIN users u ON u.id=e.user_id JOIN courses c ON c.id=e.course_id ORDER BY e.id DESC""").fetchall()
    con.close()
    return render_template("admin.html", user=current_user(), users=users,courses=courses,enrollments=enrollments)

@app.route("/admin/course", methods=["POST"])
@admin_required
def add_course():
    con=db(); con.execute("INSERT INTO courses(title,description,price) VALUES(?,?,?)",
      (request.form["title"],request.form["description"],float(request.form["price"])))
    con.commit(); con.close(); flash("Course added.", "success"); return redirect(url_for("admin"))

@app.route("/admin/lesson", methods=["POST"])
@admin_required
def add_lesson():
    con=db(); con.execute("INSERT INTO lessons(course_id,title,content,video_url,position) VALUES(?,?,?,?,?)",
      (request.form["course_id"],request.form["title"],request.form["content"],request.form.get("video_url",""),int(request.form.get("position",0))))
    con.commit(); con.close(); flash("Lesson added.", "success"); return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

print("🔥🔥🔥 THIS APP.PY IS RUNNING 🔥🔥🔥")

from settings import Config

import random
import os
import base64
from io import BytesIO
from datetime import datetime

import psycopg2
import qrcode

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    send_file
)

app = Flask(__name__)

app.secret_key = "nrsc_secret_key"

app.config.from_object(Config)


# ---------------- DB CONNECTION ----------------

def get_connection():

    return psycopg2.connect(
        dbname=app.config["DB_NAME"],
        user=app.config["DB_USER"],
        password=app.config["DB_PASSWORD"],
        host=app.config["DB_HOST"],
        port=app.config["DB_PORT"]
    )


# ---------------- DB HELPERS ----------------

def get_visitor_db():
    return get_connection()


def get_staff_db():
    return get_connection()


# ---------------- QR CODE HELPER ----------------

def generate_qr_code(visitor_id, name, visit_date, visit_duration):

    qr_data = f"""
Visitor ID: {visitor_id}
Name: {name}
Visit Date: {visit_date}
Duration: {visit_duration}
"""

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    img.save(buffer, format="PNG")

    return (
        "data:image/png;base64,"
        + base64.b64encode(buffer.getvalue()).decode()
    )
# ---------------- INIT VISITOR DB ----------------

def init_visitor_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS visitors (

            id SERIAL PRIMARY KEY,

            name TEXT,
            email TEXT,
            phone TEXT,
            organization TEXT,
            profession TEXT,
            address TEXT,

            visit_date TEXT,
            visit_duration TEXT,

            purpose TEXT,
            person TEXT,

            staff_email TEXT,
            staff_phone TEXT,

            group_count INTEGER,

            date TEXT,
            time TEXT,

            status TEXT,

            qr_code TEXT,

            photo TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- INIT STAFF DB ----------------

def init_staff_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (

            staff_id SERIAL PRIMARY KEY,

            login_id TEXT UNIQUE,

            password TEXT,

            name TEXT,

            role TEXT,

            email TEXT,

            division_head_email TEXT,

            phone TEXT
        )
    """)

    # ---------- DEFAULT STAFF ----------

    cur.execute("""
        INSERT INTO staff (

            login_id,
            password,
            name,
            role,
            email,
            division_head_email,
            phone
        )

        SELECT

            'NRSC101',
            'ADMIN123',
            'Gayatri',
            'Scientist',
            'gayatri@gmail.com',
            'head@gmail.com',
            '9876543210'

        WHERE NOT EXISTS (

            SELECT 1
            FROM staff
            WHERE login_id = 'NRSC101'
        )
    """)

    conn.commit()
    conn.close()

def init_admin_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (

            id SERIAL PRIMARY KEY,

            username TEXT,

            password TEXT
        )
    """)

    # ---------- DEFAULT ADMIN ----------

    cur.execute("""
        INSERT INTO admin (
            username,
            password
        )

        SELECT
            'admin',
            'admin123'

        WHERE NOT EXISTS (

            SELECT 1
            FROM admin
            WHERE username = 'admin'
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------- VISITOR OPTIONS ----------------

@app.route("/visitor/options")
def visitor_options():

    return render_template("visitor_options.html")


# ---------------- VISITOR FORM ----------------

@app.route("/visitor", methods=["GET", "POST"])
def visitor():

    # ---------- POST ----------

    if request.method == "POST":

        now = datetime.now()

        conn = get_visitor_db()
        cur = conn.cursor()

        # ---------- INSERT VISITOR ----------

        cur.execute(
            """
            INSERT INTO visitors (
                name,
                email,
                phone,
                organization,
                profession,
                address,
                visit_date,
                visit_duration,
                purpose,
                person,
                staff_email,
                staff_phone,
                group_count,
                date,
                time,
                status
            )

            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, 'Pending'
            )

            RETURNING id
            """,

            (
                request.form["name"],
                request.form["email"],
                request.form["phone"],
                request.form.get("organization"),
                request.form.get("profession"),
                request.form.get("address"),
                request.form["visit_date"],
                request.form["visit_duration"],
                request.form["purpose"],
                request.form["person"],
                None,
                None,
                int(request.form.get("group_size") or 1),
                now.strftime("%d-%m-%Y"),
                now.strftime("%H:%M:%S")
            )
        )

        visitor_id = cur.fetchone()[0]

        # ---------- SAVE DATABASE ----------

        conn.commit()

        # ---------- SAVE SESSION ----------

        session["visitor_id"] = visitor_id

        # ---------- GET STAFF DETAILS ----------

        staff_id = request.form["person"]

        staff_conn = get_staff_db()
        staff_cur = staff_conn.cursor()

        staff_cur.execute(
            """
            SELECT
                email,
                division_head_email,
                name,
                phone

            FROM staff

            WHERE staff_id = %s
            """,

            (staff_id,)
        )

        row = staff_cur.fetchone()

        if row:

            columns = [
                desc[0]
                for desc in staff_cur.description
            ]

            staff_data = dict(zip(columns, row))

        else:

            staff_data = None

        # ---------- CLOSE CONNECTIONS ----------

        staff_cur.close()
        staff_conn.close()

        cur.close()
        conn.close()

        # ---------- REDIRECT TO STATUS PAGE ----------

        return redirect("/visitor/status")

    # ---------- GET STAFF LIST ----------

    conn = get_staff_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            staff_id,
            name

        FROM staff
        """
    )

    columns = [
        desc[0]
        for desc in cur.description
    ]

    staff_list = [

        dict(zip(columns, row))

        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    # ---------- LOAD VISITOR FORM ----------

    return render_template(
        "visitor.html",
        staff_list=staff_list
    )


# ---------------- VISITOR STATUS ----------------

@app.route("/visitor/status")
def visitor_status():

    visitor_id = session.get("visitor_id")

    if not visitor_id:

        return redirect("/visitor")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            name,
            phone,
            person,
            purpose,
            status,
            qr_code

        FROM visitors

        WHERE id = %s
        """,

        (visitor_id,)
    )

    row = cur.fetchone()

    if row:

        columns = [
            desc[0]
            for desc in cur.description
        ]

        visitor = dict(zip(columns, row))

    else:

        visitor = None

    cur.close()
    conn.close()

    if not visitor:

        return "Visitor not found", 404

    return render_template(
        "visitor_status.html",
        visitor=visitor
    )


# ---------------- STAFF LOGIN ----------------

@app.route("/staff", methods=["GET", "POST"])
def staff_login():

    if request.method == "POST":

        login_id = request.form["staff_id"]
        password = request.form["password"]

        conn = get_visitor_db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM staff

            WHERE login_id = %s
            AND password = %s
            """,

            (login_id, password)
        )

        user = cur.fetchone()

        if user:

            session["staff_logged_in"] = True
            session["staff_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]

            cur.close()
            conn.close()

            return redirect("/staff/visitors")

        else:

            cur.close()
            conn.close()

            return render_template(
                "staff_login.html",
                error="Invalid Login ID or Password"
            )

    return render_template("staff_login.html")
# ---------------- STAFF VISITORS ----------------
@app.route("/staff/visitors")
def staff_visitors():

    if "staff_id" not in session:
        return redirect("/staff")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute(
    """
    SELECT *
    FROM visitors
    WHERE person = %s
    ORDER BY id DESC
    """,
    (str(session["staff_id"]),)
)

    columns = [desc[0] for desc in cur.description]

    visitors = [
        dict(zip(columns, row))
        for row in cur.fetchall()
    ]

    conn.close()

    staff = {
        "staff_id": session["staff_id"],
        "name": session["name"],
        "designation": session["role"]
    }

    return render_template(
        "staff_visitors.html",
        visitors=visitors,
        staff=staff
    )
# ---------------- STAFF APPROVE ----------------
@app.route("/staff/approve/<int:visitor_id>", methods=["GET", "POST"])
def staff_approve(visitor_id):
    if "staff_id" not in session:
        return redirect("/staff")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT name, visit_date, visit_duration FROM visitors WHERE id=%s",
        (visitor_id,)
    )

    row = cur.fetchone()

    if row:
        columns = [desc[0] for desc in cur.description]
        visitor = dict(zip(columns, row))
    else:
        visitor = None

    if visitor:
        qr = generate_qr_code(
            visitor_id,
            visitor["name"],
            visitor["visit_date"],
            visitor["visit_duration"]
        )

        cur.execute(
            "UPDATE visitors SET status='Approved', qr_code=%s WHERE id=%s",
            (qr, visitor_id)
        )

    conn.commit()
    conn.close()

    return redirect("/staff/visitors")


# ---------------- STAFF REJECT ----------------
@app.route("/staff/reject/<int:visitor_id>", methods=["GET", "POST"])
def staff_reject(visitor_id):
    if "staff_id" not in session:
        return redirect("/staff")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE visitors SET status='Rejected' WHERE id=%s",
        (visitor_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/staff/visitors")

# ---------------- GATE PASS ----------------
@app.route("/gate_pass/<int:visitor_id>")
def gate_pass(visitor_id):
    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM visitors WHERE id=%s",
        (visitor_id,)
    )

    row = cur.fetchone()

    # 🔥 FIX: convert to dict
    if row:
        columns = [desc[0] for desc in cur.description]
        visitor = dict(zip(columns, row))
    else:
        visitor = None

    conn.close()

    if not visitor:
        return "Visitor not found", 404

    if visitor["status"] != "Approved":
        return "Gate pass available only after approval", 403

    return render_template(
        "gate_pass.html",
        visitor=visitor
    )


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        conn = get_staff_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT username FROM admin WHERE username=%s AND password=%s",
            (request.form["username"], request.form["password"])
        )

        row = cur.fetchone()

        # 🔥 FIX: convert to dict
        if row:
            columns = [desc[0] for desc in cur.description]
            admin = dict(zip(columns, row))
        else:
            admin = None

        conn.close()

        if admin:
            session["admin_logged_in"] = True
            session["admin_name"] = admin["username"]
            return redirect("/admin_dashboard")

        return render_template("admin_login.html", error="Invalid credentials")

    return render_template("admin_login.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin_logged_in" not in session:
        return redirect("/admin_login")
    return render_template("admin_dashboard.html", admin_name=session["admin_name"])

# ---------------- ADMIN VISITORS ----------------
@app.route("/admin/visitors")
def admin_visitors():
    if "admin_logged_in" not in session:
        return redirect("/admin_login")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visitors ORDER BY id DESC")

    columns = [desc[0] for desc in cur.description]
    visitors = [dict(zip(columns, row)) for row in cur.fetchall()]

    conn.close()

    return render_template("admin_visitors.html", visitors=visitors)


# ---------------- ADMIN VIEW PDF ----------------
@app.route("/admin/view_pdf/<int:visitor_id>")
def admin_view_pdf(visitor_id):
    if "admin_logged_in" not in session:
        return redirect("/admin_login")

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    conn = get_visitor_db()
    cur = conn.cursor()

    # ✅ FIXED QUERY
    cur.execute("SELECT * FROM visitors WHERE id=%s", (visitor_id,))
    row = cur.fetchone()

    # ✅ convert to dict
    if row:
        columns = [desc[0] for desc in cur.description]
        v = dict(zip(columns, row))
    else:
        v = None

    conn.close()

    if not v:
        return "Visitor not found", 404

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width/2, height-40, "NRSC – VISITOR GATE PASS")

    # PHOTO
    photo_y = height - 220
    if v["photo"] and os.path.exists(v["photo"]):
        pdf.drawImage(
            ImageReader(v["photo"]),
            40, photo_y, width=120, height=150, mask="auto"
        )

    # DETAILS
    y = photo_y - 20
    pdf.setFont("Helvetica", 11)

    for label in [
        "name","email","phone","organization","profession",
        "address","purpose","person","visit_date",
        "visit_duration","group_count","date","time"
    ]:
        pdf.drawString(40, y, f"{label.replace('_',' ').title()} : {v[label]}")
        y -= 18

    # QR
    if v["qr_code"]:
        qr_img = ImageReader(
            BytesIO(base64.b64decode(v["qr_code"].split(",")[1]))
        )
        pdf.drawImage(qr_img, width-200, height-260, 140, 140)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        download_name=f"visitor_{visitor_id}.pdf",
        as_attachment=False
    )


# ---------------- ADMIN STAFF ----------------
@app.route("/admin/staff")
def admin_staff():
    if "admin_logged_in" not in session:
        return redirect("/admin_login")

    conn = get_staff_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM staff ORDER BY staff_id")

    columns = [desc[0] for desc in cur.description]
    staff = [dict(zip(columns, row)) for row in cur.fetchall()]  # ✅ FIXED NAME

    conn.close()

    return render_template("admin_staff.html", staff=staff)


# ---------------- ADMIN STAFF VISITOR COUNT ----------------
@app.route("/admin/staff-visitor-count")
def admin_staff_visitor_count():
    if "admin_logged_in" not in session:
        return redirect("/admin_login")

    conn = get_visitor_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        s.name AS staff_name,
        COUNT(v.id) AS visitor_count
    FROM visitors v
    JOIN staff s 
        ON v.person::INTEGER = s.staff_id
    GROUP BY s.name
    ORDER BY visitor_count DESC
""")
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]  # ✅ FIXED

    conn.close()

    return render_template("staff_visitor_count.html", data=data)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- SERVE UPLOADS ----------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

# ---------------- CSIF PAGE ----------------
# ---------------- CSIF / AADHAAR VERIFICATION (FINAL, STRICT) ----------------
import json
from datetime import datetime

# Load Aadhaar JSON database ONCE
with open("aadhaar_db.json", "r") as f:
    AADHAAR_DB = json.load(f)

# ✅ MAIN CSIF PAGE + ALL ALIASES
@app.route("/csif", methods=["GET", "POST"])
@app.route("/csif_verification", methods=["GET", "POST"])
@app.route("/visitor/aadhaar", methods=["GET", "POST"])
def csif():
    if request.method == "POST":
        aadhaar = request.form.get("aadhaar", "").strip()
        dob_input = request.form.get("dob", "").strip()  # comes as YYYY-MM-DD from date picker

        # ---------- STRICT VALIDATION ----------
        if not aadhaar or not dob_input:
            return render_template(
                "visitor_aadhaar.html",
                error="All fields are required."
            )

        if not (aadhaar.isdigit() and len(aadhaar) == 12):
            return render_template(
                "visitor_aadhaar.html",
                error="Aadhaar must be exactly 12 digits."
            )

        # 🔒 STRICT DATE FORMAT (HTML date input)
        try:
            dob_formatted = datetime.strptime(
                dob_input, "%Y-%m-%d"
            ).strftime("%Y-%m-%d")
        except ValueError:
            return render_template(
                "visitor_aadhaar.html",
                error="Invalid date format."
            )

        user = AADHAAR_DB.get(aadhaar)

        if not user:
            return render_template(
                "visitor_aadhaar.html",
                error="Aadhaar number not found."
            )

        if user["dob"] != dob_formatted:
            return render_template(
                "visitor_aadhaar.html",
                error="Date of Birth does not match."
            )

        # ✅ VERIFIED
        return render_template(
            "visitor_aadhaar.html",
            success=True,
            name=user["name"]
        )

    # GET request → show form
    return render_template("visitor_aadhaar.html")



# ---------------- RUN ----------------
if __name__ == "__main__":
    init_visitor_db()
    init_staff_db() 
    init_admin_db()   # (you added earlier)
    app.run(debug=True)

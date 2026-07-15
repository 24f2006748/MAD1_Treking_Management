from flask import Flask, render_template, request, redirect, url_for, session
from model import db, User, Trek, Booking
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy import or_


app = Flask(__name__)

app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trek.db"

db.init_app(app)

with app.app_context():
    db.create_all()

#  =============== CREATING ADMIN  ===============

    admin = User.query.filter_by(email="admin@trek.com").first()

    if not admin:
        admin = User(
        name="Admin",
        email="admin@trek.com",
        password=generate_password_hash("admin123"),
        role="admin",
        status="approved"
        )

        db.session.add(admin)
        db.session.commit()

# =============== HOME ROUTE ===============

@app.route("/")
def home():
    return render_template("home.html")

# =============== REGISTER ROUTE ===============

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form["name"]

        email = request.form["email"]
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            message = "Email already exists"
            return render_template("register.html", message=message)
        
        password = request.form["password"]
        role = request.form["role"]

        if role not in ["user", "staff"]:
            message = "Invalid Role"
            return render_template("register.html", message=message)

        if role == "staff":
            status = "Pending"
        else:
            status = "Approved"
         
        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name, 
            email=email, 
            password=hashed_password, 
            role=role,
            status=status
            )
        
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html", message=message)

# =============== LOGIN ROUTE ===============

@app.route("/login", methods=["GET", "POST"])
def login():

    message = ""

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

        # ---------- STAFF ----------
            if user.role == "staff":

                if user.status == "Pending":
                    message = "Your account is waiting for admin approval."
                    return render_template("login.html", message=message)

                elif user.status == "Blacklisted":
                    message = "Your account has been blacklisted. Please contact the administrator."
                    return render_template("login.html", message=message)

        # ---------- USER ----------
            elif user.role == "user":

                if user.status == "Blacklisted":
                    message = "Your account has been blacklisted. Please contact the administrator."
                    return render_template("login.html", message=message)

            session["user_id"] = user.id
            session["role"] = user.role
            session["name"] = user.name

            if user.role == "user":
                return redirect(url_for("user_dashboard"))

            elif user.role == "staff":
                return redirect(url_for("staff_dashboard"))

            elif user.role == "admin":
                return redirect(url_for("admin_dashboard"))

        else:
            message = "Invalid Email or Password"

    return render_template("login.html", message=message)


# =============== LOGOUT ROUTE ===============

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -------ADMIN----------ADMIN----------ADMIN----------ADMIN----------ADMIN----------ADMIN----------ADMIN----------ADMIN

# =============== ADMIN : DASHBOARD ===============

@app.route("/admin_dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role="user").count()
    total_staff = User.query.filter_by(role="staff",status="Approved").count()
    total_bookings = Booking.query.count()

    return render_template(
        "admin/admin_dashboard.html",
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings
    )


# =============== ADMIN : TREK OVERVIEW ===============

@app.route("/admin/trek")
def trek():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    # Search & Filter Values 
    search = request.args.get("search", "")
    difficulty = request.args.get("difficulty", "")
    status = request.args.get("status", "")
    staff = request.args.get("staff", "")
    participants = request.args.get("participants", "")

    #Base Query 
    treks = Trek.query

    # Search by Trek Name or Location
    if search:
        treks = treks.filter(
            (Trek.trek_name.ilike(f"%{search}%")) |
            (Trek.location.ilike(f"%{search}%"))
        )

    # Filter by Difficulty
    if difficulty:
        treks = treks.filter_by(difficulty=difficulty)

    # Filter by Status
    if status:
        treks = treks.filter_by(status=status)

    # Staff Assigned Filter
    if staff == "assigned":
        treks = treks.filter(Trek.assigned_staff_id != None)

    elif staff == "not_assigned":
        treks = treks.filter(Trek.assigned_staff_id == None)

    treks = treks.all()

    # Participant Coun
    for trek in treks:
        trek.participant_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.status != "Cancelled"
        ).count()

    # Participant Sorting 
    if participants == "high":
        treks.sort(
            key=lambda trek: trek.participant_count,
            reverse=True
        )

    elif participants == "low":
        treks.sort(key=lambda trek: trek.participant_count
                   )
    return render_template(
        "admin/trek.html",
        treks=treks
    )


# =============== ADMIN : MANAGE TREK ===============

@app.route("/admin/manage_trek")
def manage_trek():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    search = request.args.get("search", "").strip()
    difficulty = request.args.get("difficulty", "")
    status = request.args.get("status", "")
    staff = request.args.get("staff", "")
    participants = request.args.get("participants", "")

    treks = Trek.query

    if search:
        if search.isdigit():
            treks = treks.filter(Trek.id == int(search))
        else:
            treks = treks.filter(
                (Trek.trek_name.ilike(f"%{search}%")) |
                (Trek.location.ilike(f"%{search}%"))
            )

    if difficulty:
        treks = treks.filter_by(difficulty=difficulty)

    if status:
        treks = treks.filter_by(status=status)

    if staff == "assigned":
        treks = treks.filter(Trek.assigned_staff_id != None)
    elif staff == "not_assigned":
        treks = treks.filter(Trek.assigned_staff_id == None)

    treks = treks.order_by(Trek.id).all()

    for trek in treks:
        trek.participant_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.status != "Cancelled"
        ).count()

    if participants == "high":
        treks.sort(key=lambda trek: trek.participant_count, reverse=True)
    elif participants == "low":
        treks.sort(key=lambda trek: trek.participant_count)

    return render_template(
        "admin/manage_trek.html",
        treks=treks,
        search=search,
        difficulty=difficulty,
        status=status,
        staff=staff,
        participants=participants,
    )


# =============== ADMIN : ADD/CREATE TREK ===============

@app.route("/admin/add_trek", methods=["GET", "POST"])
def add_trek():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    if request.method == "POST":
        trek_name = request.form["trek_name"]
        location = request.form["location"]
        description = request.form["description"]
        difficulty = request.form["difficulty"]
        duration = request.form["duration"]
        available_slots = request.form["available_slots"]
        status = request.form["status"]
        start_date = datetime.strptime(request.form["start_date"],"%Y-%m-%d").date()
        end_date = datetime.strptime(request.form["end_date"],"%Y-%m-%d").date()

        today = date.today()

        if start_date < today:
            return redirect(url_for("add_trek"))
        if end_date < start_date:
            return redirect(url_for("add_trek"))

        new_trek = Trek(
            trek_name=trek_name,
            location=location,
            description=description,
            difficulty=difficulty,
            duration=duration,
            available_slots=available_slots,
            status=status,
            start_date=start_date,
            end_date=end_date
        )

        db.session.add(new_trek)
        db.session.commit()

        return redirect(url_for("manage_trek"))

    return render_template("admin/add_trek.html", today=date.today().isoformat())


# =============== ADMIN : EDIT TREK ===============

@app.route("/admin/edit_trek/<int:trek_id>", methods=["GET", "POST"])
def edit_trek(trek_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"
    
    trek = Trek.query.get_or_404(trek_id)
    if request.method == "POST":
        trek.trek_name = request.form["trek_name"]
        trek.location = request.form["location"]
        trek.description = request.form["description"]      
        trek.difficulty = request.form["difficulty"]
        trek.duration = request.form["duration"]
        trek.available_slots = request.form["available_slots"]
        trek.status = request.form["status"]        
        trek.start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        trek.end_date = datetime.strptime(request.form["end_date"],"%Y-%m-%d").date()

        # Validation
        if trek.end_date < trek.start_date:
            return redirect(url_for("edit_trek", trek_id=trek.id))

        db.session.commit()
        return redirect(url_for("manage_trek")) 
    
    return render_template(
        "admin/edit_trek.html",
        trek=trek
    )


# =============== ADMIN : DELETE TREK ===============

@app.route("/admin/delete_trek/<int:trek_id>", methods=["GET", "POST"])
def delete_trek(trek_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    # Don't allow completed treks to be deleted
    if trek.status == "Completed":
        return redirect(url_for("manage_trek"))

    if request.method == "POST":
        db.session.delete(trek)
        db.session.commit()
        return redirect(url_for("manage_trek"))

    return render_template(
        "admin/delete_trek.html",
        trek=trek
    )


# =============== ADMIN : ASSIGN STAFF TO TREK ===============

@app.route("/admin/assign_staff/<int:trek_id>", methods=["GET", "POST"])
def assign_staff(trek_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    # Prevent assigning staff to completed treks
    if trek.status == "Completed":
        return redirect(url_for("manage_trek"))

    staff_members = User.query.filter_by(role="staff", status="Approved").all()

    if request.method == "POST":

        selected_staff_id = request.form.get("staff_id")

        if selected_staff_id == "NA":
            trek.assigned_staff_id = None
        else:
            trek.assigned_staff_id = int(selected_staff_id)

        db.session.commit()

        return redirect(url_for("manage_trek"))

    return render_template(
        "admin/assign_staff.html",
        trek=trek,
        staff_members=staff_members
    )


# =============== ADMIN : MANAGE STAFF ===============
@app.route("/admin/manage_staff")
def manage_staff():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "All")

    staff = User.query.filter_by(role="staff")

    # Search 
    if search:

        if search.upper().startswith("S"):
            search = search[1:]

        if search.isdigit():
            staff = staff.filter(User.id == int(search))

        else:
            staff = staff.filter(User.name.ilike(f"%{search}%"))

    # Status Filter
    if status != "All":
        staff = staff.filter(User.status == status)

    staff = staff.order_by(User.id).all()

    return render_template(
        "admin/manage_staff.html",
        staff=staff
    )


# =============== ADMIN : APPROVE STAFF ===============

@app.route("/admin/approve_staff/<int:staff_id>", methods=["POST"])
def approve_staff(staff_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    staff = User.query.get_or_404(staff_id)

    if staff.role != "staff":
        return "Invalid Staff"

    staff.status = "Approved"

    db.session.commit()

    return redirect(url_for("manage_staff"))


# =============== ADMIN : BLACKLIST STAFF ===============

@app.route("/admin/blacklist_staff/<int:staff_id>", methods=["POST"])
def blacklist_staff(staff_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "admin":
        return "Access Denied"

    staff = User.query.get_or_404(staff_id)

    if staff.role != "staff":
        return "Invalid Staff"

    staff.status = "Blacklisted"

    db.session.commit()

    return redirect(url_for("manage_staff"))


# =============== ADMIN : MANAGE USERS ===============
@app.route("/admin/manage_users")
def manage_users():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "All")

    users = User.query.filter_by(role="user")

    # Search
    if search:

        if search.upper().startswith("U"):
            search = search[1:]

        if search.isdigit():
            users = users.filter(User.id == int(search))

        else:
            users = users.filter(User.name.ilike(f"%{search}%"))

    # Status Filter
    if status != "All":
        users = users.filter(User.status == status)

    users = users.order_by(User.id).all()

    return render_template(
        "admin/manage_users.html",
        users=users
    )


# =============== ADMIN : BLACKLIST USER ===============

@app.route("/admin/blacklist_user/<int:user_id>", methods=["POST"])
def blacklist_user(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    user = User.query.get_or_404(user_id)

    if user.role != "user":
        return "Invalid User"

    user.status = "Blacklisted"

    db.session.commit()

    return redirect(url_for("manage_users"))


# =============== ADMIN : VIEW ALL BOOKINGS ===============

@app.route("/admin/view_bookings")
def view_bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    # Get search and filter values
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "")

    # Base query
    bookings = Booking.query

    # Search by User Name, Trek Name or Location
    if search:
        bookings = bookings.join(Booking.user).join(Booking.trek).filter(
        or_(
            User.name.ilike(f"%{search}%"),
            Trek.trek_name.ilike(f"%{search}%"),
            Trek.location.ilike(f"%{search}%")
        )
    )

    # Filter by Booking Status
    if status:
        bookings = bookings.filter(
            Booking.status == status
        )

    # Latest bookings first
    bookings = bookings.order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "admin/view_bookings.html",
        bookings=bookings
    )


# =============== ADMIN : REPORTS ===============

@app.route("/admin/report")
def report():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "admin":
        return "Access Denied"

    # BOOKING STATISTICS________
    booked_count = Booking.query.filter_by(status="Booked").count()

    cancelled_count = Booking.query.filter_by(
        status="Cancelled"
    ).count()

    # STAFF STATISTICS_____
    approved_staff = User.query.filter_by(
        role="staff",
        status="Approved"
    ).count()

    pending_staff = User.query.filter_by(
        role="staff",
        status="Pending"
    ).count()

    blacklisted_staff = User.query.filter_by(
        role="staff",
        status="Blacklisted"
    ).count()

    # USER STATISTICS________
    approved_users = User.query.filter_by(
        role="user",
        status="Approved"
    ).count()

    blacklisted_users = User.query.filter_by(
        role="user",
        status="Blacklisted"
    ).count()

    # TREK STATUS________
    open_treks = Trek.query.filter_by(status="Open").count()

    closed_treks = Trek.query.filter_by(status="Closed").count()

    completed_treks = Trek.query.filter_by(
        status="Completed"
    ).count()

    # DIFFICULTY_______
    easy_count = Trek.query.filter_by(
        difficulty="Easy"
    ).count()

    moderate_count = Trek.query.filter_by(
        difficulty="Moderate"
    ).count()

    hard_count = Trek.query.filter_by(
        difficulty="Hard"
    ).count()


    # PARTICIPANT COUNT FOR EACH TREK_______
    treks = Trek.query.all()

    for trek in treks:
        trek.participant_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.status != "Cancelled"
        ).count()

    # MOST POPULAR TREK_________
    most_popular = None
    if treks:
        most_popular = max(
            treks,
            key=lambda x: x.participant_count
        )

    # LEAST POPULAR TREK________
    least_popular = None
    if treks:
        least_popular = min(
            treks,
            key=lambda x: x.participant_count
        )

    return render_template(

        "admin/report.html",

        booked_count=booked_count,
        cancelled_count=cancelled_count,

        approved_staff=approved_staff,
        pending_staff=pending_staff,
        blacklisted_staff=blacklisted_staff,

        approved_users=approved_users,
        blacklisted_users=blacklisted_users,

        open_treks=open_treks,
        closed_treks=closed_treks,
        completed_treks=completed_treks,

        easy_count=easy_count,
        moderate_count=moderate_count,
        hard_count=hard_count,

        most_popular=most_popular,
        least_popular=least_popular

    )


# -----STAFF----------STAFF----------STAFF----------STAFF----------STAFF----------STAFF----------STAFF----------STAFF


# =============== STAFF : DASHBOARD ===============

@app.route("/staff_dashboard")
def staff_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "staff":
        return "Access Denied"

    staff = User.query.get(session["user_id"])

    assigned_treks = Trek.query.filter_by(
        assigned_staff_id=staff.id
    ).all()

    total_assigned = len(assigned_treks)

    open_count = Trek.query.filter_by(
        assigned_staff_id=staff.id,
        status="Open"
    ).count()

    closed_count = Trek.query.filter_by(
        assigned_staff_id=staff.id,
        status="Closed"
    ).count()

    completed_count = Trek.query.filter_by(
        assigned_staff_id=staff.id,
        status="Completed"
    ).count()

    # Total participants across all assigned treks
    total_participants = 0

    for trek in assigned_treks:

        participant_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.status != "Cancelled"
        ).count()

        total_participants += participant_count


    return render_template(
        "staff/staff_dashboard.html",
        staff=staff,
        total_assigned=total_assigned,
        total_participants=total_participants,
        open_count=open_count,
        closed_count=closed_count,
        completed_count=completed_count
    )


# =============== STAFF : SHOW ALL ASSIGNED TREKS ===============

@app.route("/staff_treks")
def staff_treks():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "staff":
        return "Access Denied"

    # Get filter values
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    participants = request.args.get("participants", "")

    # Base Query
    treks = Trek.query.filter_by( assigned_staff_id=session["user_id"])

    # Search by Trek Name
    if search:
        treks = treks.filter(Trek.trek_name.ilike(f"%{search}%"))

    # Filter by Status
    if status:
        treks = treks.filter_by(status=status)

    treks = treks.all()

    # Add Participant Count
    for trek in treks:
        trek.participant_count = Booking.query.filter(
            Booking.trek_id == trek.id,
            Booking.status != "Cancelled"
        ).count()

    # Sort by Participants
    if participants == "high":
        treks.sort(
            key=lambda trek: trek.participant_count,
            reverse=True
        )

    elif participants == "low":
        treks.sort(
            key=lambda trek: trek.participant_count
        )

    return render_template(
        "staff/staff_treks.html",
        treks=treks
    )


# ================= STAFF : SHOW TREK DETAILS WITH GIVEN TREK ID =================

@app.route("/staff/manage_trek/<int:trek_id>", methods=["GET", "POST"])
def staff_manage_trek(trek_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "staff":
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    # Security Check
    if trek.assigned_staff_id != session["user_id"]:
        return "Access Denied"

    if request.method == "POST":

        trek.available_slots = int(request.form["available_slots"])
        trek.status = request.form["status"]

        # If trek is marked as Completed,
        # mark all active bookings as Completed
        if trek.status == "Completed":

            bookings = Booking.query.filter_by(
                trek_id=trek.id,
                status="Booked"
            ).all()

            for booking in bookings:
                booking.status = "Completed"

        db.session.commit()

        return redirect(url_for("staff_treks"))

    participants = Booking.query.filter_by(
        trek_id=trek.id,
    ).all()

    return render_template(
        "staff/staff_manage_treks.html",
        trek=trek,
        participants=participants
    )


# -----USER----------USER----------USER----------USER----------USER----------USER----------USER----------USER-----


# =============== USER : DASHBOARD ===============

@app.route("/user_dashboard")
def user_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    user = User.query.get_or_404(session["user_id"])

    return render_template("user/user_dashboard.html", user=user)


# =============== USER : PROFILE ===============

@app.route("/user/profile", methods=["GET", "POST"])
def user_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    user = User.query.get_or_404(session["user_id"])

    message = ""

    if request.method == "POST":
        user.name = request.form["name"]
        user.email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != "":

            if password != confirm_password:
                message = "Passwords do not match."

                return render_template("user/user_profile.html", user=user, message=message)

            user.password = generate_password_hash(password)

        db.session.commit()

        message = "Profile updated successfully."

    return render_template("user/user_profile.html", user=user, message=message)


# =============== USER : BROWSE TREKS ===============

@app.route("/user/user_browse_treks")
def user_browse_treks():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    # Search & Filters
    search = request.args.get("search", "")
    location = request.args.get("location", "")
    difficulty = request.args.get("difficulty", "")
    duration = request.args.get("duration", "")

    # Base Query
    treks = Trek.query.filter(
        Trek.status == "Open",
        Trek.available_slots > 0,
        Trek.start_date > date.today()
    )

    # Search by Trek Name or Location
    if search:
        treks = treks.filter(
            or_(
                Trek.trek_name.ilike(f"%{search}%"),
                Trek.location.ilike(f"%{search}%")
            )
        )

    # Location Filter
    if location:
        treks = treks.filter(Trek.location == location)

    # Difficulty Filter
    if difficulty:
        treks = treks.filter(Trek.difficulty == difficulty)

    # Duration Filter
    if duration:
        treks = treks.filter(Trek.duration == duration)

    # Sort by Start Date
    treks = treks.order_by(Trek.start_date).all()

    # Get Locations for Dropdown
    locations = (
        db.session.query(Trek.location)
        .filter(
            Trek.status == "Open",
            Trek.available_slots > 0,
            Trek.start_date > date.today()
        )
        .distinct()
        .all()
    )

    locations = [loc[0] for loc in locations]

    return render_template(
    "user/user_browse_treks.html",
    treks=treks,
    search=search,
    difficulty=difficulty,
    duration=duration,
    locations=locations,
    selected_location=location,
)


# =============== USER : REK BOOKING DETAILS ===============

@app.route("/user/user_trek_booking_details/<int:trek_id>", methods=["GET", "POST"])
def user_trek_booking_details(trek_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    # Check if trek can be booked
    if (
        trek.status != "Open"
        or trek.available_slots <= 0
        or trek.start_date <= date.today()
    ):
        return f"""
        <script>
            alert("This trek is no longer available for booking.");
            window.location.href = "{url_for('user_browse_treks')}";
        </script>
        """

    # Check if current user has already booked this trek
    existing_booking = Booking.query.filter_by(
        user_id=session["user_id"],
        trek_id=trek.id,
        status="Booked"
    ).first()

    already_booked = existing_booking is not None

    if request.method == "POST":

        # Security check (prevents manual form submission)
        if already_booked:
            return redirect(url_for("user_my_bookings"))

        # Check slots again before booking
        if trek.available_slots <= 0:

            return f"""
            <script>
                alert("Sorry! This trek is fully booked.");
                window.location.href="{url_for('user_browse_treks')}";
            </script>
            """

        # Create Booking
        booking = Booking(
            user_id=session["user_id"],
            trek_id=trek.id,
            booking_date=date.today(),
            status="Booked"
        )

        db.session.add(booking)

        # Reduce available slots
        trek.available_slots -= 1

        db.session.commit()

        return redirect(url_for("user_my_bookings"))

    return render_template(
        "user/user_trek_booking_details.html",
        trek=trek,
        already_booked=already_booked
    )


# =============== USER : MY BOOKINGS ===============

@app.route("/user/user_my_bookings")
def user_my_bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["role"] != "user":
        return "Access Denied"

    bookings = (
        Booking.query
        .join(Trek)
        .filter(
            Booking.user_id == session["user_id"],
            Booking.status == "Booked",
            Trek.status.in_(["Open", "Closed"])
        )
        .order_by(Booking.booking_date.desc())
        .all()
    )

    return render_template(
        "user/user_my_bookings.html",
        bookings=bookings,
        today=date.today()
    )


# =============== USER : CANCEL BOOKINGS ===============

@app.route("/user/user_cancel_booking/<int:booking_id>", methods=["GET", "POST"])
def user_cancel_booking(booking_id):

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    booking = Booking.query.get_or_404(booking_id)

    # Security Check
    if booking.user_id != session["user_id"]:
        return "Access Denied"

    trek = booking.trek

    if request.method == "POST":

        # Cancellation allowed only before trek starts
        if date.today() >= trek.start_date:
            return f"""
            <script>
                alert("Cancellation is not allowed because the trek has already started.");
                window.location.href = "{url_for('user_my_bookings')}";
            </script>
            """

        booking.status = "Cancelled"

        trek.available_slots += 1

        db.session.commit()

        return redirect(url_for("user_my_bookings"))

    return render_template(
        "user/user_cancel_booking.html",
        booking=booking,
        trek=trek
    )


# =============== USER : TREK HISTROY ===============

@app.route("/user/user_trek_history")
def user_trek_history():

    if "user_id" not in session:
        return redirect(url_for("login"))
    if session["role"] != "user":
        return "Access Denied"

    selected_status = request.args.get("status", "")

    # Completed treks
    completed_bookings = Booking.query.join(Trek).filter(
        Booking.user_id == session["user_id"],
        Trek.status == "Completed"
    )

    # Cancelled bookings
    cancelled_bookings = Booking.query.filter(
        Booking.user_id == session["user_id"],
        Booking.status == "Cancelled"
    )

    if selected_status == "Completed":
        bookings = completed_bookings

    elif selected_status == "Cancelled":
        bookings = cancelled_bookings
    else:
        bookings = completed_bookings.union(cancelled_bookings)

    bookings = bookings.order_by(
        Booking.booking_date.desc()
    ).all()

    return render_template(
        "user/user_trek_history.html",
        bookings=bookings,
        selected_status=selected_status
    )

if __name__ == "__main__":
    app.run(debug=True)
    
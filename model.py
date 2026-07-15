from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
    status = db.Column(db.String(20))

class Trek(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    trek_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)

    duration = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)

    status = db.Column(db.String(50), default="Open")

    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    description = db.Column(db.Text)

    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assigned_staff = db.relationship("User")

class Booking(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    trek_id = db.Column(db.Integer, db.ForeignKey("trek.id"), nullable=False)

    booking_date = db.Column(db.Date, nullable=False)

    status = db.Column(db.String(20), default="Booked")

    # Relationships
    user = db.relationship("User", backref="bookings")
    trek = db.relationship("Trek",backref="bookings")
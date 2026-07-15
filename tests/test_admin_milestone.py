import unittest
from datetime import date

from werkzeug.security import generate_password_hash

from app import app, db
from model import Trek, User


class AdminMilestoneTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        admin = User(
            name="Admin",
            email="admin@trek.com",
            password=generate_password_hash("admin123"),
            role="admin",
            status="approved",
        )
        db.session.add(admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_manage_trek_search_filters_results(self):
        Trek(
            trek_name="Everest Base Camp",
            location="Nepal",
            description="High-altitude trek",
            difficulty="Hard",
            duration=14,
            available_slots=8,
            status="Open",
            start_date="2026-08-01",
            end_date="2026-08-15",
        ).save() if False else None

        trek_one = Trek(
            trek_name="Everest Base Camp",
            location="Nepal",
            description="High-altitude trek",
            difficulty="Hard",
            duration=14,
            available_slots=8,
            status="Open",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 15),
        )
        trek_two = Trek(
            trek_name="Langtang Valley",
            location="Nepal",
            description="Alpine trek",
            difficulty="Moderate",
            duration=7,
            available_slots=10,
            status="Open",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 17),
        )
        db.session.add_all([trek_one, trek_two])
        db.session.commit()

        self.client.post(
            "/login",
            data={"email": "admin@trek.com", "password": "admin123"},
            follow_redirects=True,
        )

        response = self.client.get("/admin/manage_trek?search=Everest")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Everest Base Camp", response.data)
        self.assertNotIn(b"Langtang Valley", response.data)


if __name__ == "__main__":
    unittest.main()

import pytest

from app import create_app, db, bcrypt
from app.models import User, Job


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()

        hashed = bcrypt.generate_password_hash("password123").decode("utf-8")
        user1 = User(username="elene", email="elene@test.ge", password=hashed)
        user2 = User(username="nino", email="nino@test.ge", password=hashed)
        db.session.add_all([user1, user2])
        db.session.commit()

        job = Job(
            title="Python Developer",
            company="TBC Bank",
            location="თბილისი",
            salary="3000 GEL",
            category="IT",
            short_description="Backend დეველოპერი",
            full_description="სრული აღწერა",
            author=user1,
        )
        db.session.add(job)
        db.session.commit()

        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password="password123"):
    return client.post("/login",
                       data={"email": email, "password": password},
                       follow_redirects=True)


# ── 1. Route ტესტი ──────────────────────────────────

def test_public_pages_load(client):
    assert client.get("/jobs").status_code == 200
    assert client.get("/about").status_code == 200
    assert client.get("/job/1").status_code == 200
    assert client.get("/user/elene").status_code == 200


def test_missing_job_returns_404(client):
    assert client.get("/job/999").status_code == 404


# ── 2. Login ტესტი ──────────────────────────────────

def test_login_grants_access_to_protected_page(client):
    # ავტორიზაციამდე დაცული გვერდი გადამისამართებას იძლევა
    response = client.get("/profile")
    assert response.status_code == 302

    # სწორი მონაცემებით შესვლის შემდეგ — იხსნება
    login(client, "elene@test.ge")
    assert client.get("/profile").status_code == 200


def test_login_fails_with_wrong_password(client):
    login(client, "elene@test.ge", "wrong-password")
    # სესია არ შეიქმნა, ამიტომ დაცული გვერდი ისევ დახურულია
    assert client.get("/profile").status_code == 302


def test_logout_ends_session(client):
    login(client, "elene@test.ge")
    client.get("/logout")
    assert client.get("/profile").status_code == 302


# ── 3. უფლებების ტესტი ──────────────────────────────

def test_cannot_edit_or_delete_others_job(client):
    login(client, "nino@test.ge")

    assert client.get("/job/1/update").status_code == 403
    assert client.post("/job/1/delete").status_code == 403


def test_owner_can_edit_own_job(client):
    login(client, "elene@test.ge")
    assert client.get("/job/1/update").status_code == 200


def test_others_job_survives_delete_attempt(app, client):
    login(client, "nino@test.ge")
    client.post("/job/1/delete")

    with app.app_context():
        assert db.session.get(Job, 1) is not None
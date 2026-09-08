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
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=True)


# 1. Route ტესტი
def test_jobs_page_loads(client):
    response = client.get("/jobs")
    assert response.status_code == 200

    response = client.get("/about")
    assert response.status_code == 200


# 2. Login ტესტი
def test_login_success_and_failure(client):
    response = login(client, "elene@test.ge")
    assert response.status_code == 200
    assert b"Logout" in response.data

    client.get("/logout")

    response = login(client, "elene@test.ge", "wrong-password")
    assert b"Logout" not in response.data


# 3. უფლებების ტესტი
def test_cannot_edit_others_job(client):
    login(client, "nino@test.ge")

    response = client.get("/job/1/update")
    assert response.status_code == 403

    response = client.post("/job/1/delete")
    assert response.status_code == 403


def test_owner_can_edit_own_job(client):
    login(client, "elene@test.ge")
    response = client.get("/job/1/update")
    assert response.status_code == 200
import os
import secrets

import requests
from flask import (Blueprint, render_template, url_for, flash, redirect,
                   request, abort, current_app)
from flask_login import login_user, current_user, logout_user, login_required

from app import db, bcrypt
from app.models import User, Job
from app.forms import (RegistrationForm, LoginForm, JobForm,
                       UpdateProfileForm)

main = Blueprint("main", __name__)


# ── დამხმარე ფუნქციები ──────────────────────────────

def fetch_remote_jobs(limit=6):
    """Remotive API-დან დისტანციური ვაკანსიების წამოღება."""
    url = "https://remotive.com/api/remote-jobs"

    try:
        response = requests.get(url, params={"limit": limit}, timeout=8)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for item in data.get("jobs", [])[:limit]:
            jobs.append({
                "title": item.get("title", "—"),
                "company": item.get("company_name", "—"),
                "category": item.get("category", "—"),
                "job_type": item.get("job_type", "—"),
                "location": item.get("candidate_required_location", "Remote"),
                "salary": item.get("salary") or "მითითებული არ არის",
                "url": item.get("url", "#"),
            })
        return jobs

    except (requests.RequestException, KeyError, ValueError) as e:
        current_app.logger.error(f"API request error: {e}")
        return None


def save_picture(form_picture):
    """სურათს ინახავს შემთხვევითი სახელით, აბრუნებს ფაილის სახელს."""
    random_hex = secrets.token_hex(8)
    _, ext = os.path.splitext(form_picture.filename)
    filename = random_hex + ext

    folder = os.path.join(current_app.root_path, "static", "avatars")
    os.makedirs(folder, exist_ok=True)
    form_picture.save(os.path.join(folder, filename))
    return filename


# ── საჯარო გვერდები ─────────────────────────────────

@main.route("/")
@main.route("/jobs")
def jobs():
    category = request.args.get("category")
    sort = request.args.get("sort", "newest")
    search = request.args.get("search", "").strip()

    query = Job.query

    if category and category != "all":
        query = query.filter_by(category=category)

    if search:
        query = query.filter(Job.title.ilike(f"%{search}%"))

    if sort == "oldest":
        query = query.order_by(Job.date_posted.asc())
    else:
        query = query.order_by(Job.date_posted.desc())

    all_jobs = query.all()
    categories = ["IT", "Design", "Marketing", "Finance", "Other"]

    return render_template("jobs.html", jobs=all_jobs, categories=categories,
                           active_category=category, active_sort=sort,
                           search=search)


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/remote-jobs")
def remote_jobs():
    external_jobs = fetch_remote_jobs()
    return render_template("remote_jobs.html", jobs=external_jobs)


@main.route("/job/<int:job_id>")
def job_detail(job_id):
    job = db.get_or_404(Job, job_id)
    return render_template("job_detail.html", job=job)


@main.route("/user/<string:username>")
def user_jobs(username):
    user = User.query.filter_by(username=username).first_or_404()
    user_job_list = (Job.query.filter_by(author=user)
                     .order_by(Job.date_posted.desc()).all())
    return render_template("user_jobs.html", jobs=user_job_list, user=user)


# ── ავტორიზაცია ─────────────────────────────────────

@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.jobs"))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(username=form.username.data, email=form.email.data,
                    password=hashed)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"ახალი რეგისტრაცია: {user.email}")
        flash("რეგისტრაცია წარმატებულია, შედით სისტემაში.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.jobs"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            current_app.logger.info(f"წარმატებული ავტორიზაცია: {user.email}")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.jobs"))

        current_app.logger.warning(f"წარუმატებელი ავტორიზაცია: {form.email.data}")
        flash("ავტორიზაცია ვერ მოხერხდა. შეამოწმეთ ელფოსტა და პაროლი.", "danger")

    return render_template("login.html", form=form)


@main.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.jobs"))


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = UpdateProfileForm()

    if form.validate_on_submit():
        if form.picture.data:
            current_user.image_file = save_picture(form.picture.data)
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        current_app.logger.info(f"პროფილი განახლდა: {current_user.email}")
        flash("პროფილი განახლდა.", "success")
        return redirect(url_for("main.profile"))

    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    my_jobs = (Job.query.filter_by(author=current_user)
               .order_by(Job.date_posted.desc()).all())

    return render_template("profile.html", form=form, my_jobs=my_jobs)


# ── ვაკანსიების CRUD ────────────────────────────────

@main.route("/job/new", methods=["GET", "POST"])
@login_required
def new_job():
    form = JobForm()
    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            company=form.company.data,
            location=form.location.data,
            salary=form.salary.data,
            category=form.category.data,
            short_description=form.short_description.data,
            full_description=form.full_description.data,
            author=current_user,
        )
        db.session.add(job)
        db.session.commit()
        current_app.logger.info(
            f"ვაკანსია დაემატა: '{job.title}' — {current_user.username}")
        flash("ვაკანსია დაემატა.", "success")
        return redirect(url_for("main.job_detail", job_id=job.id))

    return render_template("job_form.html", form=form, legend="ახალი ვაკანსია")


@main.route("/job/<int:job_id>/update", methods=["GET", "POST"])
@login_required
def update_job(job_id):
    job = db.get_or_404(Job, job_id)
    if job.author != current_user:
        abort(403)

    form = JobForm()
    if form.validate_on_submit():
        job.title = form.title.data
        job.company = form.company.data
        job.location = form.location.data
        job.salary = form.salary.data
        job.category = form.category.data
        job.short_description = form.short_description.data
        job.full_description = form.full_description.data
        db.session.commit()
        current_app.logger.info(
            f"ვაკანსია განახლდა: id={job.id} — {current_user.username}")
        flash("ვაკანსია განახლდა.", "success")
        return redirect(url_for("main.job_detail", job_id=job.id))

    elif request.method == "GET":
        form.title.data = job.title
        form.company.data = job.company
        form.location.data = job.location
        form.salary.data = job.salary
        form.category.data = job.category
        form.short_description.data = job.short_description
        form.full_description.data = job.full_description

    return render_template("job_form.html", form=form,
                           legend="ვაკანსიის რედაქტირება")


@main.route("/job/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    job = db.get_or_404(Job, job_id)
    if job.author != current_user:
        abort(403)

    current_app.logger.info(
        f"ვაკანსია წაიშალა: id={job.id} '{job.title}' — {current_user.username}")
    db.session.delete(job)
    db.session.commit()
    flash("ვაკანსია წაიშალა.", "success")
    return redirect(url_for("main.jobs"))
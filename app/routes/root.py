from flask import Blueprint, render_template, redirect, url_for, request
import subprocess

root_bp = Blueprint("root", __name__)

@root_bp.route("/")
def home():
    return render_template("index.html")

@root_bp.route("/manual_refresh", methods=["POST"])
def manual_refresh():
    subprocess.run(["/home/tim/_rfidpi/update.sh"])
    return redirect(url_for("root.home"))

@root_bp.route("/manual_refresh_dev", methods=["POST"])
def manual_refresh_dev():
    subprocess.run(["/home/tim/test_rfidpi/update_dev.sh"])
    return redirect(url_for("root.home"))



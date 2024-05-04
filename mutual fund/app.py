from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_mysqldb import MySQL
import requests
import re
import bcrypt

app = Flask(__name__)
app.secret_key = "Vijay@006"

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Vijay@006'
app.config['MYSQL_DB'] = 'mutual_fund'

mysql = MySQL(app)

fundsi = "https://api.mfapi.in/mf/"

def isLoggedIn():
    return "username" in session

def is_password_strong(password):
    # Check length (at least 8 characters)
    if len(password) < 8:
        return False
    
    # Check for at least one uppercase letter
    if not re.search("[A-Z]", password):
        return False
    
    # Check for at least one lowercase letter
    if not re.search("[a-z]", password):
        return False
    
    # Check for at least one digit
    if not re.search("[0-9]", password):
        return False
    
    # Check for at least one special character
    if not re.search("[!@#$%^&*()-_=+{};:,<.>?]", password):
        return False
    
    return True

@app.route("/funds", methods=["GET", "POST"])
def funds():
    if not isLoggedIn():
        return redirect(url_for('login'))
    Name=request.form.get("Name")

    user_list = []
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM mutual_details where Name=%s",)
    data = cur.fetchall()
    cur.close()
    for i in data:
        id = i[0]
        Name = i[1]
        fund_code = i[2]
        invested_amount = i[3]
        units_held = i[4]
        complete_url = requests.get(fundsi + str(fund_code))
        fund_name = complete_url.json().get("meta")["fund_house"]
        nav = complete_url.json().get("data")[0].get("nav")
        current_value = float(nav) * float(invested_amount)
        growth = current_value - float(units_held)
        fund_dict = {
            "id": id,
            "Name": Name,
            "fund_name": fund_name,
            "invested_amount": invested_amount,
            "units_held": units_held,
            "nav": nav,
            "current_value": current_value,
            "growth": growth
        }
        user_list.append(fund_dict)

    # Get the username and name from the session
    username = session.get("username")
    name = session.get("name")

    return render_template("index.html", datas=user_list, username=username, name=name)

@app.route("/add", methods=["GET", "POST"])
def add_form():
    if request.method == "POST":
        Name = request.form.get("Name")
        Fund_code = request.form.get("fund_code")
        Invested_Amount = request.form.get("invested_amount")
        Units_held = request.form.get("units_held")

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO mutual_details (Name, fund_code, invested_amount, units_held) VALUES (%s, %s, %s, %s)",
                    (Name, Fund_code, Invested_Amount, Units_held))
        mysql.connection.commit()
        cur.close()
        flash("User created successfully", "success")  # Provide flash message and category
        return redirect(url_for("funds"))

    return render_template("add.html")

@app.route("/edit/<string:id>", methods=["GET", "POST"])
def edit_form(id):
    if request.method == "POST":
        Name = request.form.get("Name")
        Fund_code = request.form.get("fund_code")
        Invested_Amount = request.form.get("invested_amount")
        Units_held = request.form.get("units_held")

        cur = mysql.connection.cursor()
        cur.execute("UPDATE mutual_details SET Name=%s, fund_code=%s, invested_amount=%s, units_held=%s WHERE id=%s",
                    (Name, Fund_code, Invested_Amount, Units_held, id))
        mysql.connection.commit()
        cur.close()
        flash("Update successful", "success")  # Provide flash message and category
        return redirect(url_for("funds"))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM mutual_details WHERE id = %s", (id,))
    data = cur.fetchone()
    cur.close()

    return render_template("edit.html", data=data)

@app.route("/", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if password is strong
        if not is_password_strong(password):
            flash("Password is not strong enough. Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.", "danger")
            return redirect(url_for('signup'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM login WHERE username=%s", (username,))
        data = cur.fetchone()
        cur.close()
        if data:
            flash("Username already exists", "danger")
            return redirect(url_for('signup'))
        else:
            # Hash the password before storing it
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO login (username, password) VALUES (%s, %s)", (username, hashed_password))
            mysql.connection.commit()
            cur.close()
            session["username"] = username
            session["name"] = username  # Set name same as username
            flash("Signup successful. You are now logged in.", "success")
            return redirect(url_for('funds'))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM login WHERE username = %s", (username,))
        data = cur.fetchone()  # Changed to fetchone
        cur.connection.commit()
        cur.close()
        if data:
            stored_password = data[2]  # Assuming password is stored in the third column
            # Check if the entered password matches the stored hashed password
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                session["username"] = username
                session["name"] = username  # Set name same as username
                flash("Login successful", "success")
                return redirect(url_for('funds'))
            else:
                flash("Username or Password mismatch", "danger")
        else:
            flash("Username or Password mismatch", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("name", None)  # Clear name from session
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete(id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM mutual_details WHERE id=%s", (id,))
        mysql.connection.commit()
        flash("Successfully deleted", "success")
    except Exception as e:
        flash(f"Error occurred: {str(e)}", "danger")
    finally:
        cur.close()

    return redirect(url_for('funds'))

if __name__ == "__main__":
    app.run(debug=True)

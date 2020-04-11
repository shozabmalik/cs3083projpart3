from flask import Flask, render_template, request, session, url_for, redirect, send_file
import pymysql.cursors
import hashlib
from functools import wraps
import os
import time

app = Flask(__name__)

conn = pymysql.connect(host='localhost',
                       port=8888,
                       user='root',
                       password='root',
                       db='FinstagramTableDefsDpr20',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor,
                       autocommit=True)

@app.route('/')
def index():
    if ("username" in session):
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

def login_required(par):
    @wraps(par)
    def d(*args, **kwargs):
        if (not "username" in session):
            return redirect(url_for("login"))
        return par(*args, **kwargs)
    return d

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

SALT = "cs3083"

@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    if (request.form):
        username = request.form['username']
        password = request.form['password']
        newPassword = password + SALT
        checksumPassword  = hashlib.sha256(newPassword.encode("utf-8")).hexdigest()

        cursor = conn.cursor()
        query = 'SELECT * FROM Person WHERE username = %s and password = %s'
        cursor.execute(query, (username, checksumPassword))
        data = cursor.fetchone()
        cursor.close()
        error = None
        if (data):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = 'Invalid login or username'
            return render_template('login.html', error=error)
    error = "Unkown error. Try again."
    return render_template("register.html", error=error)

@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    if (request.form):
        username = request.form['username']
        password = request.form['password']
        newPassword = password + SALT
        checksumPassword = hashlib.sha256(newPassword.encode("utf-8")).hexdigest()
        try:
            cursor = conn.cursor()
            query = "INSERT INTO Person (username, password) VALUES (%s, %s)"
            cursor.execute(query, (username, checksumPassword))
        except pymysql.err.IntegrityError:
            error = "Someone with the username %s already exists." % (username)
            return render_template('register.html', error=error)
        return redirect(url_for("login"))

    error = "Unkown error. Try again."
    return render_template("register.html", error=error)

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    followers = 0
    if request.files:
        file = request.files.get("imageToUpload", "")
        name = file.filename
        path = os.path.join(IMAGES_DIR, name)
        file.save(path)
        username = session["username"]
        if (request.form["allFollowers"] == "True"):
            followers = 1

        query = "INSERT INTO Photo (postingdate, filePath, allFollowers, poster) VALUES (%s, %s, %s, %s)"
        with conn.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), path, followers, username))
        message = "Success!"
        return render_template('upload.html', message=message)
    else:
        message = "Failed. Try again."
        return render_template('upload.html', message=message)


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')

app.secret_key = 'some key that you will never guess'
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=False)
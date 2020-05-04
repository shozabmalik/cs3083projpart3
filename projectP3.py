from flask import Flask, render_template, request, session, url_for, redirect, send_file, flash
import pymysql.cursors
import hashlib
from functools import wraps
import os
import secrets
import time
from PIL import Image

app = Flask(__name__)
IMAGES_DIR = os.path.join(os.getcwd(), "images")


conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password='PanKalbi',
                       db='DatabasesFinsta',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

app.secret_key = 'some key that you will never guess'
SALT = "cs3083"

def login_required(par):
    @wraps(par)
    def d(*args, **kwargs):
        if (not "username" in session):
            return redirect(url_for("login"))
        return par(*args, **kwargs)
    return d



@app.route('/')
def index():
    if ("username" in session):
        return redirect(url_for("home"))
    return render_template("index.html")



@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session['username'])



@app.route('/login')#, methods=['GET'])
def login():
    return render_template('login.html')



@app.route('/register')#, methods=['GET'])
def register():
    return render_template('register.html')



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
            error = 'login or username is invalid'
            return render_template('login.html', error=error)
    error = "Unkown error. Try again."
    return render_template("login.html", error=error)

@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    username = request.form['username']
    password = request.form['password']
    newPassword = password + SALT
    checksumPassword = hashlib.sha256(newPassword.encode("utf-8")).hexdigest()
    firstName = request.form['fname']
    lastName = request.form['lname']

    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    data = cursor.fetchone()
    error = None
    if(data):
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = "INSERT INTO Person (username, password, firstName, lastName) VALUES (%s, %s, %s, %s)"
        cursor.execute(ins, (username, checksumPassword, firstName, lastName))
        conn.commit()
        cursor.close()
        return render_template('index.html')


"""def savePhoto(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/images', picture_fn)
    output_size = (400, 500)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn
"""

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    followers = 0
    if request.files:
        file = request.files.get("imageToUpload", "")
        image_name = file.filename
        path = os.path.join(IMAGES_DIR, image_name)
        file.save(path)
        caption = request.form["caption"]
        #path = savePhoto(file)
        username = session["username"]
        if (request.form["allFollowers"] == "True"):
            followers = 1
        print('3')
        query = "INSERT INTO Photo (postingDate, filePath, allFollowers, caption, poster) VALUES (%s, %s, %s, %s, %s)"
        with conn.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), path, followers, caption, username))
            print('4')
        message = "Success!"
        return render_template('upload.html',message = message)
    else:
        message = "Failed. Try again."
        return render_template('upload.html', message = message)

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    username = session["username"]
    return render_template("upload.html", username=username)


@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')



@app.route('/images', methods=["GET"])
@login_required
def images():

    username = session["username"]
    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    data = cursor.fetchone()
    firstName = data["firstName"]
    lastName = data["lastName"]
    # get the photos visible to the username
    query = 'SELECT pID,postingDate,filePath,caption,poster FROM Photo WHERE poster = %s OR pID IN (SELECT pID FROM Photo WHERE poster != %s AND allFollowers = 1 AND poster IN (SELECT followee FROM Follow WHERE follower = %s AND followee = poster AND followStatus = 1)) OR pID IN (SELECT pID FROM SharedWith NATURAL JOIN BelongTo NATURAL JOIN Photo WHERE username = %s AND poster != %s) ORDER BY postingDate DESC'
    cursor.execute(query, (username, username, username, username, username))
    data = cursor.fetchall()
    for post in data:  # post is a dictionary within a list of dictionaries for all the photos
        query = 'SELECT username, firstName, lastName FROM Tag NATURAL JOIN Person WHERE pID = %s'
        cursor.execute(query, (post['pID']))
        result = cursor.fetchall()
        print('hello')
        if (result):
            post['tagees'] = result
        query = 'SELECT firstName, lastName FROM Person WHERE username = %s'
        cursor.execute(query, (post['poster']))
        ownerInfo = cursor.fetchone()
        post['firstName'] = ownerInfo['firstName']
        post['lastName'] = ownerInfo['lastName']

    cursor.close()
    return render_template('images.html', posts=data)    

@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(location):
        return send_file(location, mimetype="image/jpg")


@app.route("/react", methods=["POST"])
@login_required
def react():
    username = session["username"]
    #query = "INSERT IGNORE INTO Likes (username, photoID, liketime) values (%s, %s, %s)"
    query = "INSERT INTO ReactTo(username, pID, reactionTime, emoji) values (%s, %s, %s)"
    pID = request.form["pID"]
    with conn.cursor() as cursor:
        cursor.execute(query,(username, pID, time.strftime('%Y-%m-%d %H:%M:%S')))
    return render_template("images.html")


@app.route("/follow", methods=["GET", "POST"])
@login_required
def follow():
    if request.form:
       username = request.form['username']
       cursor = conn.cursor()
       query = 'SELECT * FROM Person WHERE username = %s'
       cursor.execute(query, (username))
       data = cursor.fetchone()
       error = None
       if (data): 
           query = "SELECT * FROM Follow WHERE followee = %s AND follower = %s"
           cursor.execute(query, (username, session['username']))
           data = cursor.fetchone()
           if (data):
               if (data["followStatus"] == 1):
                   error = "You are already following this user"
               else:
                   error = "Request is still pending"
               return render_template("follow.html", message=error)
           else:
               query = "INSERT INTO Follow VALUES(%s, %s, 0)"
               conn.commit()
               cursor.execute(query, (username, session['username']))
               message = "Successfully sent follow request"
               return render_template("follow.html", message = message)
       else:
           # returns an error message to the html page
           error = 'Invalid username'
       cursor.close()
       return render_template('follow.html', message = error)
    return render_template('follow.html')


@app.route("/manageRequests", methods=["GET","POST"])
@login_required
def manageRequests():
   cursor = conn.cursor()
   query = "SELECT follower FROM Follow WHERE followee = %s AND followStatus = 0"
   cursor.execute(query, (session["username"]))
   data = cursor.fetchall()
   if request.form:
       chosenUsers = request.form.getlist("chooseUsers")
       for user in chosenUsers:
           if request.form['action'] ==  "Accept":
               query = "UPDATE Follow SET followStatus = 1 WHERE followee=%s\
               AND follower = %s"
               cursor.execute(query, (session['username'], user))
               conn.commit()
               flash("The selected friend requests have been accepted!")
           elif request.form['action'] == "Decline":
               query = "DELETE FROM Follow WHERE followee = %s\
               AND follower = %s"
               cursor.execute(query, (session['username'], user))
               conn.commit()
               flash("The selected friend requests have been deleted")
       return redirect(url_for("manageRequests"))
   cursor.close()
   return render_template("manageRequests.html", followers = data)


@app.route("/createFriendGroup", methods=["GET", "POST"])
@login_required
def createFriendGroup():
   print('FIRST')
   if request.form:
       print('SECOND')
       groupName = request.form["groupName"]
       description = request.form["description"]
       cursor = conn.cursor()
       query = "SELECT * FROM FriendGroup WHERE groupCreator = %s\
       AND groupName = %s"
       cursor.execute(query, (session["username"], groupName))
       print('THIRD')
       data = cursor.fetchone()
       if data: # bad, return error message
           error = f"You already have a friend group called {groupName}"
           return render_template("createFriendGroup.html", message = error)
       else: # good, add group into database
           query = "INSERT INTO FriendGroup VALUES(%s,%s,%s)"
           cursor.execute(query, (groupName, session['username'], description))

           conn.commit()
           flash(f"Successfully created the {groupName} friend group")
           return redirect(url_for("createFriendGroup"))
   return render_template("createFriendGroup.html")

@app.route("/groups")
@login_required
def friend_groups():
    username = session["username"]
    query = "SELECT DISTINCT username, groupName FROM BelongTo WHERE username = %s OR username = %s"
    with conn.cursor() as cursor:
        cursor.execute(query, (username, username))
    data = cursor.fetchall()

    return render_template("groups.html", groups=data)


@app.route("/addToGroup", methods=["POST"])
@login_required
def add_user():
    username = session["username"]
    userToAdd = request.form["userToAdd"]
    groups = request.form.getlist("groups[]")
    # print(groups)
    userQuery = "SELECT * FROM Person WHERE username = %s"
    addToQuery = "INSERT INTO BelongTo VALUES (%s, %s, %s)"
    with conn.cursor() as cursor:
        cursor.execute(userQuery, userToAdd)
    data = cursor.fetchone()
    if (data is None):
        print("debugging user not found functionality")
        message = "User could not be added to selected group - Check if user exists"
        return message
        #return render_template("groups.html", message=message)
    else:
        try:
            print("trying")
            with conn.cursor() as cursor:
                cursor.execute(addToQuery, (userToAdd, username, groups[0]))
            message = "User successfully added to selected group"
            return message
            #return render_template("groups.html", message=message)
        except:
            print("except")
            message = "User could not be added to selected group - Already a member"
            return message
            #return render_template("groups.html", message=message)

@app.route("/searchPoster", methods=["GET"])
def searchPoster():
    return render_template("searchPoster.html")


# CODE FOR SEARCH BY POSTER
@app.route("/searchAuth", methods=["POST"])
def searchAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]

        with conn.cursor() as cursor:
            query = "SELECT * FROM Photo WHERE poster = %s"
            cursor.execute(query, username)
        data = cursor.fetchall()
        if data:
            session["username"] = username
            return render_template("images.html", username=username, posts=data)
        error = username + " does not have any posts."
        return render_template("searchPoster.html", error=error)
    error = "An unknown error has occurred. Please try again."
    return render_template("searchPoster.html", error=error)


if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
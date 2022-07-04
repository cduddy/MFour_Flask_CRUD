from flask import Flask, request
from flask_mysqldb import MySQL
import re
app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password1234!'
app.config['MYSQL_DB'] = 'mfourdb'

mysql = MySQL(app)

regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'


@app.route("/users/create", methods=['POST'])
def create_user():
    """
    This function creates and adds a user to our database

    This function expects the following request fields to be provided via JSON or FORM:
    :request 'first': The first name of the new user
    :request 'last' : The last name of the new user
    :request 'email': The email of the new user

    Returns a string indicating success or failure.
    """
    # Initialize our data
    error = None
    first = None
    last  = None
    email = None

    if request.method == 'POST':
        # Determine where we should source our data from (Either JSON or FORM)
        request_data = request.get_json(silent=True)
        if not request_data:
            request_data = request.form

        # Verify we have all fields present
        if 'first_name' not in request_data:
            return "No first name provided!"
        if 'last_name' not in request_data:
            return "No last name provided!"
        if 'email' not in request_data:
            return "No email provided!"

        first = request_data['first_name']
        last  = request_data['last_name']
        email = request_data['email']
            
        # Perform verification of the e-mail. This should verify the e-mail address is valid, and that it
        # doesn't already exist within our database
        result = _verify_email(email)
        if result > 0:
            match result:
                case 1:
                    error = "An entry for this e-mail already exists!"
                case 2:
                    error = "E-mail is invalid!"
                case _:
                    error = "Connection error. Please try again." 
            return error

        # All checks pass, add the user to the database
        cursor = mysql.connection.cursor()
        cursor.execute(''' INSERT INTO mfourdb.users(first_name,last_name,email) VALUES(%s,%s,%s)''', (first, last, email))
        mysql.connection.commit()
        cursor.close()
        error = "User was successfully added!"
    return error
    
@app.route("/users/update/<int:id>", methods=['POST'])
def update_user(id):
    """
    This function updates a specified field for the user provided

    This function expects at least one of the following request fields to be provided via JSON or FORM:
    :request 'first_name': The new first of the user
    :request 'last_name': The new last name of the user
    :request 'email': The new email of the user

    Returns a string indicating success or failure.
    """
    if request.method == "POST":
        # Initialize our data
        first_name = None
        last_name = None
        email = None

        # Determine where we should source our data from (Either JSON or FORM)
        request_data = request.get_json(silent=True)
        if not request_data:
            request_data = request.form

        # Verify we have properly formed data
        for data in request_data:
            result = _verify_field(data, request_data[data])
            if result > 0:
                match result:
                    case 1:
                        return "An invalid field was provided!"
                    case 2:
                        return "An invalid value for the specified field was provided."

        if mysql.connection:
            cursor = mysql.connection.cursor()

            # Verify the user exists
            sql = " SELECT * FROM  mfourdb.users WHERE id = '%i'" % id
            cursor.execute(sql)
            result = cursor.fetchall()
            if len(result) == 0:
                return "User ID provided does not match any user within the database."
            cursor.close()

            for data in request_data:
                # Update the user
                cursor = mysql.connection.cursor()
                sql = "UPDATE mfourdb.users SET %(field)s = '%(value)s' WHERE id='%(id)i'" % {"field" : data, "value" : request_data[data], "id" : id }
                cursor.execute(sql)
                mysql.connection.commit()
                cursor.close()

            error = "User was successfully updated!"
            return error
        else:
            error = "Connection error. Please try again."
            return error
    else:
        return None


@app.route("/users", methods=['GET'])
def users():
    """
    This function retrieves a dictionary of all users in the database.

    Returns the dictionary, if found, with all entries indexed by their user id.
    Or returns
    """
    if request.method == 'GET':
        if mysql.connection:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT * FROM mfourdb.users')
            results = cursor.fetchall()
            cursor.close()
            result = {}
            for user in results:
                result[user[0]] = user[1:]
            return result
    return None


def _verify_email(email):
    """
    This function verifies that a provided e-mail address is well-formed and that the e-mail address does not already
    exist within the database
    
    :param email: The email under verification

    Returns error codes based on email verification .
    :return 0: Success;
    :return 1: Failure: E-mail already exists in the database;
    :return 2: Failure: E-mail address is malformed;
    :return 3: Failure: Database connection failed;
    """
    # Verify the email provided is well-formed
    if not re.fullmatch(regex, email):
        return 2

    # Verify we have a valid database connection before attempting to retrieve from it
    if mysql.connection:
        cursor = mysql.connection.cursor()
        sql = " SELECT * FROM mfourdb.users WHERE email='%s'" % email
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()

        # Check if this email already exists in our user database
        if len(results) > 0:
            return 1

        return 0
    else:
        return 3


def _verify_field(field, value):
    """
    This function verifies that the provided field exists in our database and that teh value provided is valid for the
    field

    :param field: The field we want to update
    :param value: The value we want to set it to

    Returns error codes based on whether the form values were provided.
    :return 0: Success;
    :return 3: Failure: Field provided does not exist within our database;
    :return 4: Failure: Value provided is incorrect for field provided;
    """
    # Note: an alternative to this would be to query the database for the specified field and see if a matching column
    # exists. For simplicity, I have opted not to do that here.
    match field:
        # Verify the first name provided is a string
        case 'first_name':
            if not isinstance(value, str):
                return 2
        # Verify the last name provided is a string
        case 'last_name':
            if not isinstance(value, str):
                return 2
        # Verify the email provided is well-formed
        case 'email':
            # Verify the email provided is well-formed
            if not re.fullmatch(regex, value):
                return 2
        # The provided field is invalid
        case _:
            return 1
    return 0

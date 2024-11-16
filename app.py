import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    return conn

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def checkIfUserExists(username, email):
    conn = get_db_connection()
    cur = conn.cursor()

    # Assuming you have a table called 'your_table' with columns 'column1' and 'column2'
    select_query = f"SELECT count(*) from digitmile_users where username = '{username}' and email = '{email}'"
    cur.execute(select_query)
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result[0] > 0:
        return True
    return False

def checkIfPasswordValid(username, email, password):
    conn = get_db_connection()
    cur = conn.cursor()

    # Assuming you have a table called 'your_table' with columns 'column1' and 'column2'
    select_query = f"SELECT count(*) from digitmile_users where username = '{username}' and email = '{email}' and user_password = '{password}'"
    cur.execute(select_query)
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result[0] > 0:
        return True
    return False

@app.route('/api/checkUserLogin', methods=['POST'])
@cross_origin()
def checkUserLogin():
    if not request.is_json:
        return jsonify({"error": "Invalid input: Expected JSON"}), 400

    # Get the JSON data sent by Unity
    data = request.get_json()

    check = checkIfUserExists(data['user'], data['email'])
    passwordValid = checkIfPasswordValid(data['user'], data['email'], data['password'])

    if check and passwordValid:
        return jsonify({"message": "User login verified successfully"}), 201
    else:
        return jsonify({"message": "User login verification failed"}), 401

@app.route('/api/registerUser', methods=['POST'])
@cross_origin()
def registerUser():
    if not request.is_json:
        return jsonify({"error": "Invalid input: Expected JSON"}), 400

    # Get the JSON data sent by Unity
    data = request.get_json()
    print(data)
    username = data['user']
    email = data['email']
    password = data['password']

    check = checkIfUserExists(username, email)

    if check:
        return jsonify({"message": "User already exists"}), 401
    else:
        insert_query = "INSERT INTO digitmile_users (username, email, user_password) VALUES (%s, %s, %s)"
        conn = get_db_connection()
        cur = conn.cursor()

        # Assuming you have a table called 'your_table' with columns 'column1' and 'column2'
        cur.execute(insert_query, (username,email,password))

        # Commit the transaction
        conn.commit()

        # Close the connection
        cur.close()
        conn.close()
        return jsonify({"message": "User successfully registered"}), 201


@app.route('/api/insertLevelStatistics', methods=['POST'])
@cross_origin()
def insert_data():
    try:
        # Check if request is in JSON format
        if not request.is_json:
            return jsonify({"error": "Invalid input: Expected JSON"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Get the JSON data sent by Unity
        data = request.get_json()
        print(data)
        levelstatistics = data['levelStatistics']


        select_query = f"SELECT id FROM digitmile_users WHERE username = '{data['user']}';"
        cur.execute(select_query)
        user_id = cur.fetchone()
        insert_query = f"INSERT INTO userlevelstatistics (level_user, level_number, score, place, correctMoves, wrongMoves, timeElapsed) VALUES (%s, %s, %s, %s, %s, %s, %s);"
        cur.execute(insert_query, (user_id, levelstatistics.get('level'), levelstatistics.get('score'), levelstatistics.get('place'), levelstatistics.get('correctMoves'), levelstatistics.get('wrongMoves'), levelstatistics.get('timeElapsed')))

        # Commit the transaction
        conn.commit()

        # Close the connection
        cur.close()
        conn.close()

        # Return success response
        return jsonify({"message": "Data inserted successfully"}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)



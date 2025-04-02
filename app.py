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
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=int(DB_PORT)
    )
    return conn

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def checkIfUserExists(username, email):
    conn = get_db_connection()
    cur = conn.cursor()
    # Use parameterized query to avoid SQL injection
    select_query = "SELECT COUNT(*) FROM digitmile_users WHERE username = %s AND email = %s"
    cur.execute(select_query, (username, email))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] > 0

def checkIfPasswordValid(username, email, password):
    conn = get_db_connection()
    cur = conn.cursor()
    select_query = "SELECT COUNT(*) FROM digitmile_users WHERE username = %s AND email = %s AND user_password = %s"
    cur.execute(select_query, (username, email, password))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] > 0

@app.route('/api/checkUserLogin', methods=['POST'])
@cross_origin()
def checkUserLogin():
    if not request.is_json:
        return jsonify({"error": "Invalid input: Expected JSON"}), 400

    data = request.get_json()
    user_exists = checkIfUserExists(data['user'], data['email'])
    password_valid = checkIfPasswordValid(data['user'], data['email'], data['password'])

    if user_exists and password_valid:
        return jsonify({"message": "User login verified successfully"}), 201
    else:
        return jsonify({"message": "User login verification failed"}), 401

@app.route('/api/registerUser', methods=['POST'])
@cross_origin()
def registerUser():
    if not request.is_json:
        return jsonify({"error": "Invalid input: Expected JSON"}), 400

    data = request.get_json()
    username = data['user']
    email = data['email']
    password = data['password']

    print("Checking if user exists...")
    if checkIfUserExists(username, email):
        print("Exists")
        return jsonify({"message": "User already exists"}), 401
    else:
        print("Doesn't exist")
        insert_query = "INSERT INTO digitmile_users (username, email, user_password) VALUES (%s, %s, %s)"
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(insert_query, (username, email, password))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "User successfully registered"}), 201

@app.route('/api/insertLevelStatistics', methods=['POST'])
@cross_origin()
def insert_data():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid input: Expected JSON"}), 400

        data = request.get_json()
        levelstatistics = data['levelStatistics']

        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve user id safely
        select_query = "SELECT id FROM digitmile_users WHERE username = %s"
        cur.execute(select_query, (data['user'],))
        user_row = cur.fetchone()
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        user_id = user_row[0]

        insert_query = """
            INSERT INTO userlevelstatistics 
            (level_user, level_number, score, place, correctMoves, wrongMoves, timeElapsed) 
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        cur.execute(insert_query, (
            user_id,
            levelstatistics.get('level'),
            levelstatistics.get('score'),
            levelstatistics.get('place'),
            levelstatistics.get('correctMoves'),
            levelstatistics.get('wrongMoves'),
            levelstatistics.get('timeElapsed')
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data inserted successfully"}), 201

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

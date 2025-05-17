import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import psycopg2
from dotenv import load_dotenv
import traceback # Import the traceback module
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

def checkIfClassroomKeyExists(classroomKey):
    conn = get_db_connection()
    cur = conn.cursor()
    # Use parameterized query to avoid SQL injection
    select_query = "SELECT id FROM CLASSROOM WHERE classroom_key = %s"
    cur.execute(select_query, (classroomKey,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def fetchStudentsForClassroom(classroomId):
    conn = get_db_connection()
    cur = conn.cursor()
    # Use parameterized query to avoid SQL injection
    select_query = "SELECT full_name FROM STUDENT WHERE classroom_ref = %s"
    cur.execute(select_query, (classroomId,))
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


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

@app.route('/api/checkClassroomKey', methods=['POST'])
@cross_origin()
def checkClassroomKey():
    if not request.is_json:
        return jsonify({"error": "Invalid input: Expected JSON"}), 400

    data = request.get_json()
    classroomKeyExists = checkIfClassroomKeyExists(data["classroomKey"])

    if classroomKeyExists:
        print(classroomKeyExists)
        students = fetchStudentsForClassroom(classroomKeyExists[0])
        students = [student[0] for student in students]
        print(students)
        return jsonify({"students": students}), 201
    else:
        return jsonify({"message": "User login verification failed"}), 401
@app.route('/api/insertLevelStatistics', methods=['POST'])
@cross_origin()
def insert_data():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid input: Expected JSON"}), 400

        data = request.get_json()
        print(data)
        print(data['user'])
        levelstatistics = data['levelStatistics']

        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve user id safely
        select_query = "SELECT id FROM STUDENT WHERE full_name = %s"
        cur.execute(select_query, (data['user'],))
        user_row = cur.fetchone()
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        user_id = user_row[0]
        print(user_id)
        won = levelstatistics['place'] == 1
        insert_query = """
            INSERT INTO run_statistics 
            (student_ref,player_won) 
            VALUES (%s, %s);
        """

        cur.execute(insert_query, (
            user_id,
            won
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Data inserted successfully"}), 201

        # insert_query = """
        #     INSERT INTO userlevelstatistics
        #     (level_user, level_number, score, place, correctMoves, wrongMoves, timeElapsed)
        #     VALUES (%s, %s, %s, %s, %s, %s, %s);
        # """
        # cur.execute(insert_query, (
        #     user_id,
        #     levelstatistics.get('level'),
        #     levelstatistics.get('score'),
        #     levelstatistics.get('place'),
        #     levelstatistics.get('correctMoves'),
        #     levelstatistics.get('wrongMoves'),
        #     levelstatistics.get('timeElapsed')
        # ))
        # conn.commit()
        # cur.close()
        # conn.close()
        # return jsonify({"message": "Data inserted successfully"}), 201

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()  # This line will print the full traceback
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

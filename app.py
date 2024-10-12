import os

from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql
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

@app.route('/api/insertdata', methods=['POST'])
def insert_data():
    try:
        # Check if request is in JSON format
        if not request.is_json:
            return jsonify({"error": "Invalid input: Expected JSON"}), 400

        # Get the JSON data sent by Unity
        data = request.get_json()

        # Example data extraction (adjust fields as per your use case)
        test = data.get('test')

        if not test:
            return jsonify({"error": "Missing data in the request"}), 400

        # Insert data into the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Assuming you have a table called 'your_table' with columns 'column1' and 'column2'
        insert_query = "INSERT INTO test (test) VALUES (%s)"
        cur.execute(insert_query, (test,))

        # Commit the transaction
        conn.commit()

        # Close the connection
        cur.close()
        conn.close()

        # Return success response
        return jsonify({"message": "Data inserted successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/getdata', methods=['GET'])
def get_data():
    return jsonify({'Success': 'Get data reached!'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))



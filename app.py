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
    return jsonify({'Success': 'Insert data reached!'}), 200

@app.route('/api/getdata', methods=['GET'])
def get_data():
    return jsonify({'Success': 'Get data reached!'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)



from flask import Flask, jsonify
import pymysql
import traceback
import logging
import os
from flask import request
import hashlib
from decimal import Decimal



app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


def get_database_connection() -> pymysql.connections.Connection:
    # Use details from your environment variables
    return pymysql.connect(
        host=os.environ.get('DATABASE_HOST'),
        user=os.environ.get('DATABASE_USER'),
        password=os.environ.get('DATABASE_PASSWORD'),
        db=os.environ.get('DATABASE_NAME'),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():
    return "Welcome to the Flask Server!"

@app.route('/create_user_table', methods=['GET'])
def create_user_table():
    try:
        # Connect to your MySQL database
        connection = pymysql.connect(
            host='sql11.freesqldatabase.com',
            user='sql11694019',
            password='wIJB3Bvi5t',
            db='sql11694019',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # SQL statement to create  users table
            sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                phone_number VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            );
            """
            cursor.execute(sql)
            connection.commit()

        return jsonify({"success": "Table 'users' created successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/register', methods=['POST'])
def register_user():
    print("Request to /register endpoint")
    try:
        data = request.json
        username = data['username']
        phone_number = data['number']
        hashed_password = hash_password(data['password'])

        # Connect to your MySQL database
        connection = pymysql.connect(
            host='sql11.freesqldatabase.com',
            user='sql11694019',
            password='wIJB3Bvi5t',
            db='sql11694019',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"error": "Username already exists"}), 409

            # Insert new user into database
            sql = "INSERT INTO users (username, phone_number, password) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, phone_number, hashed_password))
            connection.commit()

        return jsonify({"success": "User registered successfully"}), 201
    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed.")

@app.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.json
        username = data['username']
        password = hash_password(data['password'])

        connection = get_database_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                           (username, password))
            result = cursor.fetchone()

            if result is None:
                return jsonify({"error": "Invalid username or password"}), 401

        return jsonify({"success": "Login successful", "user": result}), 200
    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed.")


@app.route('/get_data', methods=['GET'])
def get_data():
    connection = None  # Initialize connection to None
    try:
        connection = get_database_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
            return jsonify(result)
    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed.")



@app.route('/get_family_data/<int:family_id>', methods=['GET'])
def get_family_data(family_id):
    try:
        connection = get_database_connection()
        with connection.cursor() as cursor:
            query = "SELECT * FROM families WHERE id = %s"
            cursor.execute(query, (family_id,))
            result = cursor.fetchone()
            if result:
                logging.info(f"Family data retrieved: {result}")
                return jsonify(result)
            else:
                return jsonify({"error": "Family not found"}), 404
    except Exception as e:
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed.")


@app.route('/donate', methods=['POST'])
def donate():
    try:
        data = request.json
        username = data['username']
        donation_amount = Decimal(data['donation_amount'])
        
        connection = get_database_connection()
        with connection.cursor() as cursor:
            # Start transaction
            connection.begin()
            
            # Retrieve current amount
            cursor.execute("SELECT SUM(amount) as total_credit FROM transactions WHERE customer_name = %s AND status = 'complete'", (username,))

            result = cursor.fetchone()
            if result is None or result['total_credit'] is None:
                connection.rollback()  # Rollback transaction
                return jsonify({"No credit found or user not found"}), 404
            
            current_credit = Decimal(result['amount'])
            if donation_amount > current_credit:
                connection.rollback()  # Rollback transaction
                return jsonify({"error": "Insufficient funds"}), 400

            new_credit = current_credit - donation_amount
            
            # Record the donation as  new transaction with negative amount
            cursor.execute("INSERT INTO transactions (phone_number, amount, timestamp, status, customer_name) VALUES (%s, %s, NOW(), 'complete', %s)",
                           (data['phone_number'], -donation_amount, username))
            connection.commit()  # Commit transaction
            
            return jsonify({"success": "Donation successful", "remaining_credit": str(new_credit)}), 200
    except Exception as e:
        if connection:
            connection.rollback()
        logging.error(f"Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)

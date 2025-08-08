#!/usr/bin/env python3
"""
Script to create admin users for the Lemon Health application using direct SQL.

Usage:
    python scripts/create_admin_sql.py

This script will prompt for admin user details and create an admin account using SQL queries.
"""

import psycopg2
import bcrypt
import sys
import os
from getpass import getpass
from datetime import datetime

# Database connection parameters
DB_HOST = "15.235.50.88"
DB_PORT = 5433
DB_USER = "postgres"
DB_NAME = "lemonhealth_db"

def get_db_connection():
    """Create database connection"""
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=input("Enter database password: "),
            database=DB_NAME
        )
        return connection
    except psycopg2.Error as e:
        print(f"❌ Error connecting to database: {e}")
        return None

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_user_exists(cursor, mobile_number: str, country_code: str, email: str = None) -> tuple[bool, bool]:
    """Check if user with mobile number or email already exists"""
    mobile_exists = False
    email_exists = False
    
    # Check mobile number
    cursor.execute(
        "SELECT id FROM users WHERE mobile_number = %s AND country_code = %s",
        (mobile_number, country_code)
    )
    if cursor.fetchone():
        mobile_exists = True
    
    # Check email if provided
    if email:
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            email_exists = True
    
    return mobile_exists, email_exists

def create_admin_user():
    """Create an admin user interactively using SQL"""
    print("=== Lemon Health Admin User Creation (SQL) ===\n")
    
    # Get user input
    first_name = input("First Name: ").strip()
    if not first_name:
        print("❌ First name is required")
        return False
    
    last_name = input("Last Name: ").strip()
    if not last_name:
        print("❌ Last name is required")
        return False
    
    mobile_number = input("Mobile Number (without country code): ").strip()
    if not mobile_number:
        print("❌ Mobile number is required")
        return False
    
    country_code = input("Country Code (default: +91): ").strip() or "+91"
    
    email = input("Email (optional): ").strip() or None
    
    password = getpass("Password: ")
    if not password:
        print("❌ Password is required")
        return False
    
    confirm_password = getpass("Confirm Password: ")
    if password != confirm_password:
        print("❌ Passwords do not match")
        return False
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters long")
        return False
    
    # Confirm creation
    print(f"\n=== Admin User Details ===")
    print(f"Name: {first_name} {last_name}")
    print(f"Mobile: {country_code}{mobile_number}")
    print(f"Email: {email or 'Not provided'}")
    print(f"Admin: Yes")
    print(f"Verified: Yes")
    print(f"Active: Yes")
    
    confirm = input("\nCreate this admin user? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Admin user creation cancelled")
        return False
    
    # Connect to database
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Check if user already exists
        mobile_exists, email_exists = check_user_exists(cursor, mobile_number, country_code, email)
        
        if mobile_exists:
            print(f"❌ User with mobile number {country_code}{mobile_number} already exists")
            return False
        
        if email_exists:
            print(f"❌ User with email {email} already exists")
            return False
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create admin user using SQL
        current_time = datetime.utcnow()
        
        insert_query = """
        INSERT INTO users (
            first_name, last_name, mobile_number, country_code, hashed_password,
            email, is_active, is_verified, is_admin, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        
        cursor.execute(insert_query, (
            first_name,
            last_name,
            mobile_number,
            country_code,
            hashed_password,
            email,
            True,  # is_active
            True,  # is_verified
            True,  # is_admin
            current_time,
            current_time
        ))
        
        # Get the created user ID
        user_id = cursor.fetchone()[0]
        
        # Commit the transaction
        connection.commit()
        
        print(f"\n✅ Admin user created successfully!")
        print(f"Admin ID: {user_id}")
        print(f"Mobile: {country_code}{mobile_number}")
        print(f"Email: {email or 'Not provided'}")
        print(f"\nYou can now log in to the admin panel using these credentials.")
        
        return True
        
    except psycopg2.Error as e:
        connection.rollback()
        print(f"❌ Error creating admin user: {e}")
        return False
    finally:
        if connection:
            connection.close()

def list_admin_users():
    """List all admin users using SQL"""
    print("=== Admin Users List ===\n")
    
    connection = get_db_connection()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, first_name, last_name, mobile_number, country_code, 
                   email, is_active, is_verified, created_at
            FROM users 
            WHERE is_admin = TRUE 
            ORDER BY created_at
        """)
        
        admin_users = cursor.fetchall()
        
        if not admin_users:
            print("No admin users found.")
            return
        
        for user in admin_users:
            user_id, first_name, last_name, mobile_number, country_code, email, is_active, is_verified, created_at = user
            print(f"ID: {user_id}")
            print(f"Name: {first_name} {last_name}")
            print(f"Mobile: {country_code}{mobile_number}")
            print(f"Email: {email or 'Not provided'}")
            print(f"Active: {'Yes' if is_active else 'No'}")
            print(f"Verified: {'Yes' if is_verified else 'No'}")
            print(f"Created: {created_at}")
            print("-" * 50)
            
    except psycopg2.Error as e:
        print(f"❌ Error listing admin users: {e}")
    finally:
        if connection:
            connection.close()

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "list":
            list_admin_users()
        elif command == "create":
            create_admin_user()
        else:
            print("Usage:")
            print("  python scripts/create_admin_sql.py create  # Create new admin user")
            print("  python scripts/create_admin_sql.py list    # List admin users")
    else:
        # Default to create
        create_admin_user()

if __name__ == "__main__":
    main() 
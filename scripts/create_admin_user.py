#!/usr/bin/env python3
"""
Script to create admin users for the Lemon Health application.

Usage:
    python scripts/create_admin_user.py

This script will prompt for admin user details and create an admin account.
"""

import asyncio
import sys
import os
from getpass import getpass

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from apps.core.db import AsyncSessionLocal
from apps.auth.models import User
from apps.core.security import get_password_hash
# Import Profile model to resolve relationship
from apps.profile.models import Profile


async def create_admin_user():
    """Create an admin user interactively"""
    print("=== Lemon Health Admin User Creation ===\n")
    
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
    
    # Create admin user
    async with AsyncSessionLocal() as db:
        try:
            # Check if mobile number already exists
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.mobile_number == mobile_number)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"❌ User with mobile number {country_code}{mobile_number} already exists")
                return False
            
            # Check if email already exists (if provided)
            if email:
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                existing_email = result.scalar_one_or_none()
                
                if existing_email:
                    print(f"❌ User with email {email} already exists")
                    return False
            
            # Tax ID validation removed - not needed for MVP
            
            # Create admin user
            hashed_password = get_password_hash(password)
            
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                mobile_number=mobile_number,
                country_code=country_code,
                hashed_password=hashed_password,
                email=email,
                is_admin=True,
                is_verified=True,  # Admin users are auto-verified
                is_active=True
            )
            
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            
            print(f"\n✅ Admin user created successfully!")
            print(f"Admin ID: {admin_user.id}")
            print(f"Mobile: {country_code}{mobile_number}")
            print(f"Email: {email or 'Not provided'}")
            print(f"\nYou can now log in to the admin panel using these credentials.")
            
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating admin user: {str(e)}")
            return False


async def list_admin_users():
    """List all admin users"""
    print("=== Admin Users List ===\n")
    
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.is_admin == True).order_by(User.created_at)
            )
            admin_users = result.scalars().all()
            
            if not admin_users:
                print("No admin users found.")
                return
            
            for user in admin_users:
                print(f"ID: {user.id}")
                print(f"Name: {user.first_name} {user.last_name}")
                print(f"Mobile: {user.country_code}{user.mobile_number}")
                print(f"Email: {user.email or 'Not provided'}")
                print(f"Tax ID: Not needed for MVP")
                print(f"Active: {'Yes' if user.is_active else 'No'}")
                print(f"Verified: {'Yes' if user.is_verified else 'No'}")
                print(f"Created: {user.created_at}")
                print("-" * 50)
        except Exception as e:
            print(f"❌ Error listing admin users: {str(e)}")


def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "list":
            asyncio.run(list_admin_users())
        elif command == "create":
            asyncio.run(create_admin_user())
        else:
            print("Usage:")
            print("  python scripts/create_admin_user.py create  # Create new admin user")
            print("  python scripts/create_admin_user.py list    # List admin users")
    else:
        # Default to create
        asyncio.run(create_admin_user())


if __name__ == "__main__":
    main() 


"""
TO RUN THE SCRIPT: Use the following commands to create an admin user or list all admin users.

python scripts/create_admin_user.py create
python scripts/create_admin_user.py list

"""

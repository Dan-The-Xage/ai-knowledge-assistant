#!/usr/bin/env python
"""Test script to debug registration issues."""

import sys
sys.path.insert(0, '.')

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, Role

def test_registration():
    """Test user registration logic directly."""
    print("Starting registration test...")
    
    db = SessionLocal()
    try:
        # Check for user role
        print("Checking for 'user' role...")
        user_role = db.query(Role).filter(Role.name == "user").first()
        
        if not user_role:
            print("ERROR: 'user' role not found!")
            return
        
        print(f"Found role: {user_role.name} (id={user_role.id})")
        
        # Check if test user exists
        test_email = "debug_test@example.com"
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            print(f"Test user already exists, deleting...")
            db.delete(existing)
            db.commit()
        
        # Create test user
        print("Creating test user...")
        hashed_password = get_password_hash("TestPassword123")
        print(f"Password hashed: {hashed_password[:20]}...")
        
        user = User(
            email=test_email,
            full_name="Debug Test User",
            hashed_password=hashed_password,
            department="Test",
            job_title="Tester",
            role_id=user_role.id,
            is_active=True,
            is_verified=True
        )
        
        print("Adding user to session...")
        db.add(user)
        
        print("Committing...")
        db.commit()
        
        print("Refreshing...")
        db.refresh(user)
        
        print(f"SUCCESS! User created with id={user.id}")
        print(f"User details: email={user.email}, role={user.role.name if user.role else 'None'}")
        
        # Cleanup
        print("Cleaning up test user...")
        db.delete(user)
        db.commit()
        print("Test user deleted.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_registration()


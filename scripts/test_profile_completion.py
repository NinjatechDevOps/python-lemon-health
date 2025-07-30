#!/usr/bin/env python3
"""
Test script for profile completion functionality
"""
import asyncio
import sys
import os
import uuid
import random

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from apps.core.config import settings
from apps.chat.profile_completion import ProfileCompletionService
from apps.auth.models import User
from apps.profile.models import Profile


async def test_profile_completion():
    """Test the profile completion functionality"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    
    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Test 1: Check profile completeness for non-existent user
        print("Test 1: Checking profile completeness for non-existent user...")
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness(db, 999)
        print(f"Is complete: {is_complete}")
        print(f"Missing fields: {missing_fields}")
        assert not is_complete
        assert missing_fields == ['date_of_birth', 'height', 'weight', 'gender']
        print("✅ Test 1 passed")
        
        # Test 2: Create a test user and profile with unique mobile number
        print("\nTest 2: Creating test user and profile...")
        unique_mobile = f"1234567{random.randint(100, 999)}"
        test_user = User(
            first_name="Test",
            last_name="User",
            mobile_number=unique_mobile,
            country_code="+1",
            hashed_password="test_hash",
            is_verified=True
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        # Create incomplete profile
        test_profile = Profile(
            user_id=test_user.id,
            date_of_birth=None,
            height=None,
            weight=None,
            gender=None
        )
        db.add(test_profile)
        await db.commit()
        await db.refresh(test_profile)
        print(f"✅ Test user created with ID: {test_user.id}")
        
        # Test 3: Check profile completeness for incomplete profile
        print("\nTest 3: Checking profile completeness for incomplete profile...")
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness(db, test_user.id)
        print(f"Is complete: {is_complete}")
        print(f"Missing fields: {missing_fields}")
        assert not is_complete
        assert len(missing_fields) == 4
        print("✅ Test 3 passed")
        
        # Test 4: Extract profile information from user message
        print("\nTest 4: Testing profile information extraction...")
        user_message = "I'm 30 years old, 175cm tall, weigh 70kg, and I'm male"
        conversation_history = []
        
        extracted_data = await ProfileCompletionService.extract_profile_info(
            user_message=user_message,
            conversation_history=conversation_history,
            missing_fields=missing_fields,
            user=test_user
        )
        print(f"Extracted data: {extracted_data}")
        assert len(extracted_data) > 0
        print("✅ Test 4 passed")
        
        # Test 5: Update profile with extracted data
        print("\nTest 5: Testing profile update...")
        success = await ProfileCompletionService.update_profile(db, test_user.id, extracted_data)
        print(f"Profile update success: {success}")
        assert success
        print("✅ Test 5 passed")
        
        # Test 6: Check profile completeness after update
        print("\nTest 6: Checking profile completeness after update...")
        is_complete, missing_fields = await ProfileCompletionService.check_profile_completeness(db, test_user.id)
        print(f"Is complete: {is_complete}")
        print(f"Missing fields: {missing_fields}")
        assert is_complete
        assert len(missing_fields) == 0
        print("✅ Test 6 passed")
        
        # Test 7: Test profile completion with real conversation
        print("\nTest 7: Testing profile completion with conversation...")
        chat_id = str(uuid.uuid4())
        user_message = "I'm 25 years old and female"
        
        profile_response, profile_updated = await ProfileCompletionService.process_with_profile_completion(
            db=db,
            user_id=test_user.id,
            user_message=user_message,
            conversation_history=[],
            user=test_user
        )
        print(f"Profile response: {profile_response}")
        print(f"Profile updated: {profile_updated}")
        print("✅ Test 7 passed")
        
        print("\n🎉 All profile completion tests passed!")


if __name__ == "__main__":
    asyncio.run(test_profile_completion()) 
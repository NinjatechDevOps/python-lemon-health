#!/usr/bin/env python3
"""
Script to seed initial prompts in the database
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from apps.chat.models import Prompt, PromptType
from apps.core.config import settings

async def seed_prompts():
    """Seed initial prompts in the database"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    
    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if prompts already exist
        existing_prompts = await session.execute(text("SELECT COUNT(*) FROM prompts"))
        count = existing_prompts.scalar()
        
        if count > 0:
            print(f"Database already has {count} prompts. Skipping seeding.")
            return
        
        # Define initial prompts
        prompts = [
            {
                "name": "Booking",
                "description": "Book appointments and services",
                "prompt_type": PromptType.BOOKING,
                "system_prompt": "You are Lemon, a booking assistant. Help users book appointments, services, and manage their schedule. Be helpful and efficient in scheduling."
            },
            {
                "name": "Shop",
                "description": "Browse and purchase health products",
                "prompt_type": PromptType.SHOP,
                "system_prompt": "You are Lemon, a shopping assistant. Help users find and purchase health products, supplements, and wellness items. Provide recommendations based on their needs."
            },
            {
                "name": "Nutrition",
                "description": "Get personalized nutrition advice",
                "prompt_type": PromptType.NUTRITION,
                "system_prompt": "You are Lemon, a nutrition expert assistant. Provide helpful, evidence-based nutrition advice tailored to user needs. Focus on healthy eating habits, balanced diets, and nutritional information."
            },
            {
                "name": "Exercise",
                "description": "Get personalized exercise recommendations",
                "prompt_type": PromptType.EXERCISE,
                "system_prompt": "You are Lemon, a fitness expert assistant. Provide helpful, safe exercise recommendations and fitness advice. Consider different fitness levels and goals when responding."
            },
            {
                "name": "Documents",
                "description": "Upload and analyze health documents",
                "prompt_type": PromptType.DOCUMENTS,
                "system_prompt": "You are Lemon, a medical document analysis assistant. Help users understand medical documents, reports, and terminology in simple language."
            },
            {
                "name": "Prescriptions",
                "description": "Manage your prescriptions",
                "prompt_type": PromptType.PRESCRIPTIONS,
                "system_prompt": "You are Lemon, a prescription management assistant. Help users understand and manage their prescriptions and medications safely."
            }
        ]
        
        # Create and add prompts
        for prompt_data in prompts:
            prompt = Prompt(**prompt_data)
            session.add(prompt)
        
        await session.commit()
        print(f"Successfully seeded {len(prompts)} prompts in the database.")

if __name__ == "__main__":
    asyncio.run(seed_prompts()) 
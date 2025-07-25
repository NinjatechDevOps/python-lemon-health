import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from apps.core.config import settings
from apps.chat.models import Prompt, PromptType, Base

PROMPTS = [
    {
        "name": "Booking",
        "description": "Book appointments and services",
        "prompt_type": PromptType.BOOKING,
        "system_prompt": "You are Lemon, a booking assistant. Help users book appointments, services, and manage their schedule."
    },
    {
        "name": "Shop",
        "description": "Browse and purchase health products",
        "prompt_type": PromptType.SHOP,
        "system_prompt": "You are Lemon, a shopping assistant. Help users find and purchase health products and supplements."
    },
    {
        "name": "Nutrition",
        "description": "Get personalized nutrition advice",
        "prompt_type": PromptType.NUTRITION,
        "system_prompt": "You are Lemon, a nutrition expert assistant. Provide helpful, evidence-based nutrition advice tailored to the user's needs. Focus on healthy eating habits, balanced diets, and nutritional information."
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
        "system_prompt": "You are Lemon, a prescription management assistant. Help users understand and manage their prescriptions and medications."
    },
]

async def seed_prompts():
    # Use asyncpg for async SQLAlchemy
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=True)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        # Ensure the prompts table exists
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for prompt in PROMPTS:
            exists = await session.execute(
                Prompt.__table__.select().where(Prompt.prompt_type == prompt["prompt_type"]))
            if exists.scalar():
                print(f"Prompt '{prompt['name']}' already exists. Skipping.")
                continue
            p = Prompt(**prompt)
            session.add(p)
        await session.commit()
        print("Prompts seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_prompts()) 
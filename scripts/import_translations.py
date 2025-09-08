#!/usr/bin/env python3
"""
Script to import translations from messages.json into the database.
This script reads the messages.json file and creates/updates translation entries
in the database with is_deletable set to False.

Usage:
    python scripts/import_translations.py

Requirements:
    - The messages.json file should be in the project root
    - DATABASE_URL environment variable should be set
    - Database should be accessible and migrations should be up to date
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, select
from sqlalchemy.orm import DeclarativeBase
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class Translation(Base):
    __tablename__ = "translations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    keyword = Column(String, nullable=False, unique=True, index=True)
    en = Column(String, nullable=False)
    es = Column(String, nullable=False)
    is_deleted = Column(Boolean, default=False)
    is_deletable = Column(Boolean, default=True)
    created_by = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def load_json_messages(file_path: str) -> list:
    """Load messages from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            messages = json.load(file)
            logger.info(f"Loaded {len(messages)} messages from {file_path}")
            return messages
    except FileNotFoundError:
        logger.error(f"File {file_path} not found")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON file: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading JSON file: {e}")
        return []


async def check_translation_exists(db: AsyncSession, keyword: str) -> Translation | None:
    """Check if a translation with the given keyword already exists."""
    query = select(Translation).where(Translation.keyword == keyword)
    result = await db.execute(query)
    return result.scalars().first()


async def create_translation(
    db: AsyncSession, 
    keyword: str, 
    en: str, 
    es: str, 
    is_deletable: bool = False
) -> Translation:
    """Create a new translation entry."""
    translation = Translation(
        keyword=keyword,
        en=en,
        es=es,
        is_deleted=False,
        is_deletable=is_deletable,
        created_by=1,  # Default system user ID
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(translation)
    return translation


async def update_translation(
    db: AsyncSession,
    translation: Translation,
    en: str,
    es: str,
    is_deletable: bool = False
) -> Translation:
    """Update an existing translation entry."""
    translation.en = en
    translation.es = es
    translation.is_deletable = is_deletable
    translation.updated_at = datetime.utcnow()
    return translation


async def get_database_session():
    """Create async database session."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Convert sync postgres URL to async if needed
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
    
    logger.info(f"Connecting to database with async driver...")
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


async def import_translations_to_db(messages: list) -> dict:
    """
    Import translations from messages list to database.
    
    Returns:
        dict: Statistics about the import process
    """
    stats = {
        'total_processed': 0,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'skipped': 0
    }
    
    db = await get_database_session()
    
    try:
        for message in messages:
            stats['total_processed'] += 1
            
            # Validate message structure
            if not all(key in message for key in ['keyword', 'en', 'es']):
                logger.warning(f"Skipping invalid message structure: {message}")
                stats['skipped'] += 1
                continue
            
            keyword = message['keyword'].strip()
            en_text = message['en'].strip()
            es_text = message['es'].strip()
            
            if not keyword or not en_text or not es_text:
                logger.warning(f"Skipping message with empty fields: {message}")
                stats['skipped'] += 1
                continue
            
            try:
                # Check if translation already exists
                existing_translation = await check_translation_exists(db, keyword)
                
                if existing_translation:
                    # Update existing translation with new values
                    await update_translation(
                        db, existing_translation, en_text, es_text, is_deletable=False
                    )
                    stats['updated'] += 1
                    logger.info(f"Updated existing translation: {keyword}")
                    logger.debug(f"  EN: {existing_translation.en} -> {en_text}")
                    logger.debug(f"  ES: {existing_translation.es} -> {es_text}")
                else:
                    # Create new translation
                    await create_translation(
                        db, keyword, en_text, es_text, is_deletable=False
                    )
                    stats['created'] += 1
                    logger.info(f"Created new translation: {keyword}")
                    
            except Exception as e:
                logger.error(f"Error processing translation '{keyword}': {e}")
                stats['errors'] += 1
                continue
        
        # Commit all changes
        await db.commit()
        logger.info("All translations committed to database successfully")
        
    except Exception as e:
        logger.error(f"Database error during import: {e}")
        await db.rollback()
        raise
    finally:
        await db.close()
    
    return stats


async def main():
    """Main function to run the translation import script."""
    logger.info("Starting translation import script...")
    
    # Define the path to the messages.json file
    json_file_path = project_root / "messages.json"
    
    if not json_file_path.exists():
        logger.error(f"messages.json file not found at {json_file_path}")
        sys.exit(1)
    
    # Load messages from JSON file
    messages = load_json_messages(str(json_file_path))
    
    if not messages:
        logger.error("No messages loaded from JSON file. Exiting...")
        sys.exit(1)
    
    # Import translations to database
    try:
        stats = await import_translations_to_db(messages)
        
        # Print summary
        logger.info("Translation import completed!")
        logger.info("="*50)
        logger.info(f"Total processed: {stats['total_processed']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("="*50)
        
        if stats['errors'] > 0:
            logger.warning(f"Import completed with {stats['errors']} errors. Please check the logs.")
            sys.exit(1)
        else:
            logger.info("Import completed successfully!")
            
    except Exception as e:
        logger.error(f"Import failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
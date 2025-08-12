import json
import uuid
import mimetypes
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import asyncio

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from apps.chat.models import Document
import PyPDF2

from apps.chat.models import Document, DocumentAnalysis, DocumentType
from apps.chat.llm_connector import process_query_with_prompt
from apps.chat.prompts import DOCUMENT_ANALYSIS_PROMPT
from apps.core.config import settings
from apps.core.logging_config import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for handling document uploads, extraction, and analysis"""
    
    ALLOWED_EXTENSIONS = {
        'pdf': DocumentType.PDF
    }
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_file(file: UploadFile) -> DocumentType:
        """Validate uploaded file and return document type"""
        # Check file size
        if file.size and file.size > DocumentService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {DocumentService.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Check file extension
        file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
        if file_extension not in DocumentService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' is not supported. Only PDF files are allowed."
            )
        
        return DocumentService.ALLOWED_EXTENSIONS[file_extension]
    
    @staticmethod
    async def save_uploaded_file(file: UploadFile, user_id: int) -> Document:
        """Save uploaded file and create document record"""
        # Create documents directory if it doesn't exist
        documents_dir = Path(settings.MEDIA_ROOT) / "documents" / str(user_id)
        documents_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = documents_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Get file size
        file_size = len(content)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file.filename or '')
        mime_type = mime_type or 'application/pdf'
        
        # Create document record
        document = Document(
            user_id=user_id,
            original_filename=file.filename or 'unknown',
            llm_generated_filename=file.filename or 'unknown',  # Set initial filename to original
            stored_filename=unique_filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=DocumentService.ALLOWED_EXTENSIONS[file_extension],
            mime_type=mime_type
        )
        
        return document
    
    @staticmethod
    async def extract_text_from_document(document: Document) -> str:
        """Extract text content from uploaded PDF document"""
        try:
            file_path = Path(document.file_path)
            
            if not file_path.exists():
                raise Exception(f"File not found: {file_path}")
            
            if document.file_type == DocumentType.PDF:
                return await DocumentService._extract_from_pdf(file_path)
            else:
                raise Exception(f"Unsupported file type: {document.file_type}")
                
        except Exception as e:
            raise Exception(f"Error extracting text from document: {str(e)}")
    
    @staticmethod
    async def _extract_from_pdf(file_path: Path) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    @staticmethod
    async def analyze_document_content(content: str, user) -> Dict[str, Any]:
        """Analyze document content using LLM"""
        try:
            # Use the prompt from prompts module
            system_prompt = DOCUMENT_ANALYSIS_PROMPT.format(content=content[:5000])  # Limit content length

            # Process with LLM using optimized parameters for document analysis
            response = await process_query_with_prompt(
                user_message="Please analyze this document and provide filename and tags.",
                system_prompt=system_prompt,
                conversation_history=[],
                user=user,
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=1500   # More tokens for detailed analysis
            )
            
            logger.debug(f"DEBUG: LLM Response: {response}")
            
            # Parse JSON response
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                else:
                    analysis_data = json.loads(response)
                
                logger.debug(f"DEBUG: Parsed analysis data: {analysis_data}")
                
                result = {
                    "filename": analysis_data.get("filename", "document.pdf"),
                    "tags": analysis_data.get("tags", [])
                }
                
                logger.debug(f"DEBUG: Returning result: {result}")
                return result
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"DEBUG: JSON parsing error: {e}")
                # Fallback: create basic filename and tags
                return {
                    "filename": "document.pdf",
                    "tags": ["document", "analysis", "content"]
                }
                
        except Exception as e:
            raise Exception(f"Error analyzing document content: {str(e)}")
    
    @staticmethod
    async def process_document_analysis(document: Document, db: AsyncSession, user) -> DocumentAnalysis:
        """Process document analysis asynchronously"""
        try:
            # Update status to processing
            analysis = await DocumentService.get_or_create_analysis(document.id, db)
            analysis.analysis_status = "processing"
            await db.commit()
            
            # Extract content
            extracted_content = await DocumentService.extract_text_from_document(document)
            
            # Analyze content
            analysis_result = await DocumentService.analyze_document_content(extracted_content, user)
            logger.debug(f"DEBUG: Analysis result: {analysis_result}")
            
            # Update analysis record
            analysis.extracted_content = extracted_content
            analysis.generated_tags = json.dumps(analysis_result["tags"])
            analysis.analysis_status = "completed"
            analysis.updated_at = datetime.now(timezone.utc)
            
            # Update document with LLM-generated filename
            document.llm_generated_filename = analysis_result["filename"]
            logger.debug(f"DEBUG: Updated document.llm_generated_filename to: {analysis_result['filename']}")
            
            await db.commit()
            await db.refresh(analysis)
            
            return analysis
            
        except Exception as e:
            # Update analysis record with error
            analysis = await DocumentService.get_or_create_analysis(document.id, db)
            analysis.analysis_status = "failed"
            analysis.error_message = str(e)
            analysis.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(analysis)
            
            raise e

    @staticmethod
    async def process_document_analysis_async(document: Document, user) -> None:
        """Process document analysis in background with new database session"""
        from apps.core.db import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            try:
                # Re-query the document in the new session
                result = await db.execute(
                    select(Document).where(Document.id == document.id)
                )
                document_in_session = result.scalar_one()
                logger.debug(f"DEBUG: Re-queried document in new session, id: {document_in_session.id}")
                
                # Update status to processing
                analysis = await DocumentService.get_or_create_analysis(document_in_session.id, db)
                analysis.analysis_status = "processing"
                await db.commit()
                
                # Extract content
                extracted_content = await DocumentService.extract_text_from_document(document_in_session)
                
                # Analyze content
                analysis_result = await DocumentService.analyze_document_content(extracted_content, user)
                logger.debug(f"DEBUG: Async analysis result: {analysis_result}")
                
                # Update analysis record
                analysis.extracted_content = extracted_content
                analysis.generated_tags = json.dumps(analysis_result["tags"])
                analysis.analysis_status = "completed"
                analysis.updated_at = datetime.now(timezone.utc)
                
                # Update document with LLM-generated filename
                document_in_session.llm_generated_filename = analysis_result["filename"]
                logger.debug(f"DEBUG: Async updated document.llm_generated_filename to: {analysis_result['filename']}")
                
                await db.commit()
                await db.refresh(analysis)
                
            except Exception as e:
                # Update analysis record with error
                analysis = await DocumentService.get_or_create_analysis(document.id, db)
                analysis.analysis_status = "failed"
                analysis.error_message = str(e)
                analysis.updated_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(analysis)
    
    @staticmethod
    async def get_or_create_analysis(document_id: int, db: AsyncSession) -> DocumentAnalysis:
        """Get existing analysis or create new one"""
        result = await db.execute(
            select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id)
        )
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            analysis = DocumentAnalysis(document_id=document_id)
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
        
        return analysis
    
    @staticmethod
    async def get_user_documents(
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        per_page: int = 20,
        search: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """Get user's documents with pagination and search"""
        # Build base query for documents
        base_query = (
            select(Document)
            .options(selectinload(Document.analysis))
            .where(Document.user_id == user_id)
        )
        
        # Add search filter if provided
        if search:
            # Search in original filename and LLM-generated filename only
            from sqlalchemy import or_
            search_filter = or_(
                Document.original_filename.ilike(f"%{search}%"),
                Document.llm_generated_filename.ilike(f"%{search}%")
            )
            base_query = base_query.where(search_filter)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get documents with pagination
        offset = (page - 1) * per_page
        documents_query = (
            base_query
            .order_by(Document.uploaded_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        
        documents_result = await db.execute(documents_query)
        documents = documents_result.scalars().all()
        
        return documents, total 
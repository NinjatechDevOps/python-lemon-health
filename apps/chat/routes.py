import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File, Header
from fastapi.responses import  JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.core.db import get_db
from apps.auth.deps import get_current_mobile_verified_user
from apps.auth.models import User
from apps.chat.models import Document
from apps.chat.models import PromptType
from apps.auth.services import AuthService
from apps.chat.schemas import (
    PromptListResponse, BaseResponse, ChatRequest, ChatResponse, ChatHistoryResponse,
    ChatHistoryListResponse, PaginationInfo, DocumentUploadResponse, DocumentResponse,
    DocumentListResponse, DocumentAnalysisRequest, PromptResponse, DocumentAnalysisResponse
)
from apps.chat.document_service import DocumentService
from apps.chat.chat_service import ChatService
from apps.chat.utils import convert_file_path_to_complete_url
import asyncio
import math
import json
from apps.core.logging_config import get_logger

logger = get_logger(__name__)

# Create separate routers with different tags
chat_router = APIRouter(tags=["Chat"])
document_router = APIRouter(tags=["Documents"])

# Chat Endpoints
@chat_router.get("/prompts", response_model=BaseResponse[PromptListResponse])
async def get_prompts(
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
) -> Dict[str, Any]:
    """
    Get a list of all available prompts from the database.
    This endpoint does not require authentication.
    """
    logger.info(f"url : /prompts [GET] - public endpoint")
    try:
        prompt_list = await ChatService.get_prompts(db)
        logger.info(f"Retrieved {len(prompt_list)} prompts.")
        # Get translated message
        message = await AuthService.get_translation_by_keyword(db, "prompts_retrieved_successfully", app_language)
        if not message:
            message = AuthService.get_message_from_json("prompts_retrieved_successfully", app_language)
        return {
            "success": True,
            "message": message,
            "data": PromptListResponse(prompts=prompt_list)
        }
    except Exception as e:
        logger.error(f"Error retrieving prompts: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_retrieving_prompts", app_language) or AuthService.get_message_from_json("error_retrieving_prompts", app_language),
                "data": None
            }
        )

@chat_router.post("/", response_model=BaseResponse[ChatResponse])
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_mobile_verified_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Process a user query and return a response from the LLM.
    Supports both streaming and non-streaming responses.
    Includes profile completion functionality.
    
    For default prompts (when prompt_id is None):
    - Uses LLM to classify if query is related to nutrition or exercise
    - Other queries will be denied with a polite message from LLM
    """
    try:
        logger.info(f"url : /  for chat [POST]")
        logger.info(f"request by user_id : {current_user.id}")
        logger.info(f"chat_request: {chat_request.model_dump()}")
        # Streamed or non-streamed response
        if chat_request.streamed:
            return await ChatService.process_streaming_chat(chat_request, current_user, db)
        else:
            result = await ChatService.process_chat_with_profile_completion(chat_request, current_user, db)
            return result
    except HTTPException as e:
        logger.error(f"HTTPException: {e}")
        # Handle specific HTTP exceptions (like query not related to nutrition/exercise)
        if e.status_code == 400 and str(e.detail) == "query_not_related_nutrition_exercise":
            # Use LLM to generate denial response
            from apps.chat.prompts import DEFAULT_PROMPT_GUARDRAILS
            from apps.chat.llm_connector import process_query_with_prompt
            
            guardrails_prompt = DEFAULT_PROMPT_GUARDRAILS.format(
                user_query=chat_request.user_query,
                conversation_history="No previous conversation"  # First message, no history
            )
            
            denial_response = await process_query_with_prompt(
                user_message=chat_request.user_query,
                system_prompt=guardrails_prompt,
                conversation_history=[],
                user=current_user,
                temperature=0.3,  # Low temperature for consistent denial messages
                max_tokens=100    # Short denial message
            )
            
            # Create conversation and store messages with is_out_of_scope=True
            try:
                conversation, _ = await ChatService.create_default_conversation(
                    conv_id=chat_request.conv_id,
                    user_id=current_user.id,
                    user_query=chat_request.user_query,
                    db=db
                )
                # Store both messages as out-of-scope
                await ChatService.store_user_message(
                    conversation_id=conversation.id,
                    user_id=current_user.id,
                    content=chat_request.user_query,
                    db=db,
                    is_out_of_scope=True
                )
                await ChatService.store_assistant_message(
                    conversation_id=conversation.id,
                    content=denial_response,
                    db=db,
                    is_out_of_scope=True
                )
            except Exception as persist_error:
                logger.error(f"Failed to persist out-of-scope messages: {persist_error}")
            
            return {
                "success": True,
                "message": await AuthService.get_translation_by_keyword(db, "query_not_related_nutrition_exercise", app_language) or AuthService.get_message_from_json("query_not_related_nutrition_exercise", app_language),
                "data": ChatResponse(
                    conv_id=chat_request.conv_id,
                    prompt_id=chat_request.prompt_id,  # Include prompt_id in response
                    user_query=chat_request.user_query,
                    response=denial_response,
                    streamed=False
                )
            }
            
        # For other HTTPExceptions, translate the error message if it's a keyword
        detail = str(e.detail)
        if detail in ["invalid_conv_id_format", "conversation_not_found", "prompt_not_found", 
                      "default_prompt_not_found", "prompt_not_allowed"]:
            translated_message = await AuthService.get_translation_by_keyword(db, detail, app_language)
            if not translated_message:
                translated_message = AuthService.get_message_from_json(detail, app_language)
            raise HTTPException(status_code=e.status_code, detail=translated_message)
        else:
            raise
    except Exception as e:
        logger.error(f"An error occurred while processing your request: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_processing_request", app_language) or AuthService.get_message_from_json("error_processing_request", app_language),
                "data": None
            }
        )

@chat_router.get("/history/{conv_id}", response_model=BaseResponse[ChatHistoryResponse])
async def get_chat_history(
    conv_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_mobile_verified_user),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Get chat history for a specific conv_id.
    Only returns history for conversations owned by the current user.
    """
    try:
        chat_history = await ChatService.get_chat_history_by_conv_id(conv_id, current_user, db)
        return {
            "success": True,
            "message": await AuthService.get_translation_by_keyword(db, "chat_history_fetched_successfully", app_language) or AuthService.get_message_from_json("chat_history_fetched_successfully", app_language),
            "data": chat_history
        }
    except HTTPException as e:
        # Translate the error message if it's a keyword
        detail = str(e.detail)
        if detail in ["invalid_conv_id_format", "conversation_not_found"]:
            translated_message = await AuthService.get_translation_by_keyword(db, detail, app_language)
            if not translated_message:
                translated_message = AuthService.get_message_from_json(detail, app_language)
            raise HTTPException(status_code=e.status_code, detail=translated_message)
        else:
            raise
    except Exception as e:
        logger.error(f"An error occurred while fetching chat history: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_fetching_chat_history", app_language) or AuthService.get_message_from_json("error_fetching_chat_history", app_language),
                "data": None
            }
        )

@chat_router.get("/history", response_model=BaseResponse[ChatHistoryListResponse])
async def get_user_chat_history(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of conversations per page (max 100)"),
    search: Optional[str] = Query(None, description="Search conversations by title or content"),
    prompt_type: Optional[PromptType] = Query(None, description="Filter by prompt type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_mobile_verified_user),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Get all chat history for the current user with pagination.
    Returns conversation list without messages (for chat history overview).
    Supports search and filtering by prompt type.
    """
    try:
        chat_history_list = await ChatService.get_user_chat_history_list(
            current_user=current_user,
            db=db,
            page=page,
            per_page=per_page,
            search=search,
            prompt_type=prompt_type
        )
        
        return {
            "success": True,
            "message": await AuthService.get_translation_by_keyword(db, "chat_history_retrieved_successfully", app_language) or AuthService.get_message_from_json("chat_history_retrieved_successfully", app_language),
            "data": chat_history_list
        }
        
    except Exception as e:
        logger.error(f"An error occurred while fetching chat history: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_fetching_chat_history", app_language) or AuthService.get_message_from_json("error_fetching_chat_history", app_language),
                "data": None
            }
        )

# Document Endpoints
@document_router.post("/upload", response_model=BaseResponse[DocumentUploadResponse])
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_mobile_verified_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Upload a PDF document for analysis.
    Only PDF files are supported.
    """
    try:
        # Validate file
        document_type = DocumentService.validate_file(file)
        
        # Save file and create document record
        document = await DocumentService.save_uploaded_file(file, current_user.id)
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Start analysis in background with new session
        asyncio.create_task(
            DocumentService.process_document_analysis_async(document, current_user)
        )
        
        return {
            "success": True,
            "message": await AuthService.get_translation_by_keyword(db, "document_uploaded_successfully", app_language) or AuthService.get_message_from_json("document_uploaded_successfully", app_language),
            "data": DocumentUploadResponse(
                doc_id=document.doc_id,
                original_filename=document.original_filename,
                llm_generated_filename=document.llm_generated_filename,
                file_size=document.file_size,
                file_type=document.file_type,
                uploaded_at=str(document.uploaded_at),
                analysis_status="pending",
                pdf_url=convert_file_path_to_complete_url(document.file_path)
            )
        }
        
    except HTTPException as http_exc:
        # Translate the error message if it's a keyword
        detail = str(http_exc.detail)
        if detail in ["file_size_exceeds_limit", "file_type_not_supported"]:
            translated_message = await AuthService.get_translation_by_keyword(db, detail, app_language)
            if not translated_message:
                translated_message = AuthService.get_message_from_json(detail, app_language)
            # For file_size_exceeds_limit, format with max size
            if detail == "file_size_exceeds_limit":
                max_size = DocumentService.MAX_FILE_SIZE // (1024*1024)
                translated_message = translated_message.format(max_size=max_size)
            # For file_type_not_supported, format with file type
            elif detail == "file_type_not_supported":
                file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
                translated_message = translated_message.format(file_type=file_extension)
            raise HTTPException(status_code=http_exc.status_code, detail=translated_message)
        else:
            raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_uploading_document", app_language) or AuthService.get_message_from_json("error_uploading_document", app_language),
                "data": None
            }
        )

@document_router.get("/", response_model=BaseResponse[DocumentListResponse])
async def get_user_documents(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(20, ge=1, le=100, description="Number of documents per page (max 100)"),
    search: Optional[str] = Query(None, description="Search documents by original filename or LLM-generated filename"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_mobile_verified_user),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Get all documents uploaded by the current user with pagination.
    Supports search by original filename or LLM-generated filename.
    """
    try:
        documents, total = await DocumentService.get_user_documents(db, current_user.id, page, per_page, search)
        
        # Calculate pagination info
        total_pages = math.ceil(total / per_page) if total > 0 else 0
        
        # Build response data
        document_items = []
        for doc in documents:
            # Get analysis if exists
            analysis_response = None
            if doc.analysis:
                analysis_response = {
                    "analysis_id": doc.analysis.analysis_id,
                    "extracted_content": doc.analysis.extracted_content,
                    "generated_tags": json.loads(doc.analysis.generated_tags) if doc.analysis.generated_tags else None,
                    "analysis_status": doc.analysis.analysis_status,
                    "error_message": doc.analysis.error_message,
                    "created_at": str(doc.analysis.created_at),
                    "updated_at": str(doc.analysis.updated_at)
                }
            
            document_items.append(
                DocumentResponse(
                    doc_id=doc.doc_id,
                    original_filename=doc.original_filename,
                    llm_generated_filename=doc.llm_generated_filename,
                    file_size=doc.file_size,
                    file_type=doc.file_type,
                    uploaded_at=str(doc.uploaded_at),
                    pdf_url=convert_file_path_to_complete_url(doc.file_path),
                    analysis=analysis_response
                )
            )
        
        # Build pagination info
        pagination = PaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        return {
            "success": True,
            "message": await AuthService.get_translation_by_keyword(db, "documents_retrieved_successfully", app_language) or AuthService.get_message_from_json("documents_retrieved_successfully", app_language),
            "data": DocumentListResponse(
                documents=document_items,
                pagination=pagination
            )
        }
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_retrieving_documents", app_language) or AuthService.get_message_from_json("error_retrieving_documents", app_language),
                "data": None
            }
        )

@document_router.post("/analyze", response_model=BaseResponse[Dict[str, Any]])
async def analyze_document(
    request: DocumentAnalysisRequest,
    current_user: User = Depends(get_current_mobile_verified_user),
    db: AsyncSession = Depends(get_db),
    app_language: str = Header("en", alias="App-Language")
):
    """
    Manually trigger analysis for a specific document.
    """
    try:
        # Get document
        result = await db.execute(
            select(Document)
            .where(Document.doc_id == request.doc_id, Document.user_id == current_user.id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": await AuthService.get_translation_by_keyword(db, "document_not_found", app_language) or AuthService.get_message_from_json("document_not_found", app_language),
                    "data": None
                }
            )
        
        # Process analysis
        analysis = await DocumentService.process_document_analysis(document, db, current_user)
        
        return {
            "success": True,
            "message": await AuthService.get_translation_by_keyword(db, "document_analysis_completed", app_language) or AuthService.get_message_from_json("document_analysis_completed", app_language),
            "data": {
                "doc_id": document.doc_id,
                "analysis_id": analysis.analysis_id,
                "analysis_status": analysis.analysis_status,
                "tags": json.loads(analysis.generated_tags) if analysis.generated_tags else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": await AuthService.get_translation_by_keyword(db, "error_analyzing_document", app_language) or AuthService.get_message_from_json("error_analyzing_document", app_language),
                "data": None
            }
        )

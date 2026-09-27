import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.competency import Competency
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.enums import (
    DocumentStatus,
    QuestionDifficulty,
    QuestionStatus,
    ReviewAction,
)
from app.models.question import Question
from app.models.question_review import QuestionReview
from app.models.user import User
from app.schemas.question import QuestionGenerateRequest, QuestionReviewRequest
from app.services.embedding_service import EmbeddingConfigurationError, EmbeddingService
from app.services.llm_service import LLMConfigurationError, LLMService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class QuestionService:
    """Service orchestrating RAG-based MCQ generation, quality validation,
    traceability attribution, and single-transaction persistence.
    """

    @classmethod
    def generate_questions(
        cls,
        db: Session,
        request: QuestionGenerateRequest,
        current_user: User,
    ) -> List[Question]:
        """Executes the complete RAG MCQ generation flow:
        1. Validates document status (must be PROCESSED).
        2. Validates and loads competency constraint if requested.
        3. Retrieves relevant grounding chunks via ChromaDB similarity search (primary retriever).
        4. Cross-references chunks with PostgreSQL document_chunks for relational metadata & chunk IDs.
        5. Calls LLM with structured output and strict grounding prompt.
        6. Enforces concrete structural, distinctness, and source chunk attribution validations.
        7. Deduplicates question texts within the batch.
        8. Persists questions with status PENDING_REVIEW and increments document.generation_count
           in a single atomic transaction.
        """
        # 1. Document validation
        document = db.query(Document).filter(Document.id == request.document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {request.document_id} was not found.",
            )

        if document.status != DocumentStatus.PROCESSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Document '{document.filename}' has status '{document.status.value}'. "
                    f"MCQs can only be generated from PROCESSED documents."
                ),
            )

        # 2. Competency constraint loading (PostgreSQL)
        competency: Optional[Competency] = None
        if request.competency_id is not None:
            competency = (
                db.query(Competency)
                .filter(Competency.id == request.competency_id)
                .first()
            )
            if not competency:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Competency with ID {request.competency_id} was not found.",
                )
            if not competency.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Competency '{competency.name}' is inactive and cannot be used for generation.",
                )

        # 3. Vector Retrieval via ChromaDB (Primary Retrieval Mechanism)
        chunk_count = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .count()
        )
        if chunk_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document '{document.filename}' contains no processed chunks in storage.",
            )

        # Query construction
        if competency:
            query_text = f"Competency {competency.name}: {competency.description or ''}"
        else:
            query_text = (
                f"Statistical definitions, indicators, surveys, methodology, and facts in {document.filename}"
            )

        try:
            query_embedding = EmbeddingService.embed_query(query_text)
        except EmbeddingConfigurationError as ece:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Embedding service error: {str(ece)}",
            )
        except Exception as e:
            logger.error(f"Error generating query embedding for document {document.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate query embedding: {str(e)}",
            )

        top_k = min(max(request.num_questions * 2, 5), chunk_count)
        try:
            hits = VectorStoreService.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                document_id=document.id,
            )
        except Exception as e:
            logger.error(f"ChromaDB retrieval error for document {document.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Vector store retrieval failed: {str(e)}",
            )

        if not hits:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching vector chunks retrieved from vector store for this document.",
            )

        retrieved_chroma_ids = [hit["chroma_id"] for hit in hits if hit.get("chroma_id")]

        # 4. Relational Metadata Lookup from PostgreSQL document_chunks
        db_chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document.id,
                DocumentChunk.chroma_id.in_(retrieved_chroma_ids),
            )
            .all()
        )

        chunk_by_chroma_id: Dict[str, DocumentChunk] = {
            c.chroma_id: c for c in db_chunks if c.chroma_id
        }
        chunk_by_id: Dict[int, DocumentChunk] = {c.id: c for c in db_chunks}

        chunks_for_prompt: List[Dict[str, Any]] = []
        for hit in hits:
            cid = hit.get("chroma_id")
            db_chunk = chunk_by_chroma_id.get(cid)
            if db_chunk:
                chunks_for_prompt.append({
                    "id": db_chunk.id,  # PostgreSQL integer chunk ID
                    "page_number": db_chunk.page_number or 1,
                    "text": hit.get("content", ""),
                })

        if not chunks_for_prompt:
            logger.error(
                f"ChromaDB retrieved {len(hits)} hits but no corresponding document_chunks found in PostgreSQL."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal traceability mismatch between vector store and relational metadata.",
            )

        valid_chunk_ids: Set[int] = {c["id"] for c in chunks_for_prompt}

        # 5. Invoke Mistral LLM with structured output
        try:
            raw_items = LLMService.generate_mcqs_from_context(
                chunks=chunks_for_prompt,
                num_questions=request.num_questions,
                difficulty=request.difficulty,
                competency_name=competency.name if competency else None,
                competency_description=competency.description if competency else None,
            )
        except LLMConfigurationError as lce:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM service configuration error: {str(lce)}",
            )
        except Exception as e:
            logger.error(f"Error during LLM question generation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI generation failed: {str(e)}",
            )

        if not raw_items:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI generation service returned no questions from the provided context.",
            )

        # 6. Quality Validation, Distinctness, Grounding Verification & Batch Deduplication
        persisted_questions: List[Question] = []
        seen_question_texts: Set[str] = set()

        for item in raw_items:
            # 6a. Text sanitization & formatting
            q_text = (item.question_text or "").strip()
            if not q_text:
                continue
            if not q_text.endswith("?"):
                q_text = f"{q_text}?"

            # 6b. Batch Deduplication (Directive 7)
            normalized_q_key = " ".join(q_text.lower().split())
            if normalized_q_key in seen_question_texts:
                logger.info(f"Filtered duplicate question within batch: '{q_text}'")
                continue
            seen_question_texts.add(normalized_q_key)

            # 6c. Validate options: 4 distinct non-empty choices
            opt_a = (item.option_a or "").strip()
            opt_b = (item.option_b or "").strip()
            opt_c = (item.option_c or "").strip()
            opt_d = (item.option_d or "").strip()

            if not (opt_a and opt_b and opt_c and opt_d):
                logger.warning(f"Skipping question with empty option choice: '{q_text}'")
                continue

            unique_opts = {
                opt_a.lower(),
                opt_b.lower(),
                opt_c.lower(),
                opt_d.lower(),
            }
            if len(unique_opts) < 4:
                logger.warning(f"Skipping question with duplicate option choices: '{q_text}'")
                continue

            # 6d. Validate correct option key
            correct_key = (item.correct_option or "").strip().upper()
            if correct_key not in {"A", "B", "C", "D"}:
                logger.warning(f"Skipping question with invalid correct_option '{correct_key}': '{q_text}'")
                continue

            # 6e. Validate explicit source chunk attribution (Directive 4)
            # Backend MUST validate that the referenced source chunk was actually in the retrieved set.
            ref_chunk_id = item.source_chunk_id
            if ref_chunk_id not in valid_chunk_ids:
                logger.warning(
                    f"Skipping question: referenced source_chunk_id {ref_chunk_id} not in retrieved set {valid_chunk_ids}"
                )
                continue

            matched_chunk = chunk_by_id[ref_chunk_id]
            source_page = matched_chunk.page_number

            # Determine final difficulty
            assigned_diff = item.difficulty or request.difficulty or QuestionDifficulty.MEDIUM

            # Build Question entity
            question_entity = Question(
                document_id=document.id,
                competency_id=request.competency_id,
                question_text=q_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct_key,
                difficulty=assigned_diff,
                explanation=(item.explanation or "").strip() or None,
                source_page=source_page,
                source_chunk_id=matched_chunk.id,
                generation_model=settings.MISTRAL_LLM_MODEL,
                status=QuestionStatus.PENDING_REVIEW,
                created_by=current_user.id,
            )
            persisted_questions.append(question_entity)

            # Cap generation to the requested volume
            if len(persisted_questions) >= request.num_questions:
                break

        if not persisted_questions:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="All generated questions failed structural quality or source chunk attribution checks.",
            )

        # 7. Single-Transaction Persistence & Generation Count Increment (Directive 6)
        try:
            for q in persisted_questions:
                db.add(q)
            document.generation_count = (document.generation_count or 0) + len(persisted_questions)
            db.commit()

            for q in persisted_questions:
                db.refresh(q)

            logger.info(
                f"Successfully committed {len(persisted_questions)} MCQs for document {document.id} in a single atomic transaction. "
                f"Updated generation_count={document.generation_count}"
            )
            return persisted_questions

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist generated questions in database: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist questions to database: {str(e)}",
            )

    @staticmethod
    def list_questions(
        db: Session,
        document_id: Optional[int] = None,
        status: Optional[QuestionStatus] = None,
        competency_id: Optional[int] = None,
        difficulty: Optional[QuestionDifficulty] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Question]]:
        """Queries questions with optional filters and pagination."""
        query = db.query(Question)

        if document_id is not None:
            query = query.filter(Question.document_id == document_id)
        if status is not None:
            query = query.filter(Question.status == status)
        if competency_id is not None:
            query = query.filter(Question.competency_id == competency_id)
        if difficulty is not None:
            query = query.filter(Question.difficulty == difficulty)

        total = query.count()
        items = (
            query.order_by(Question.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return total, items

    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
        """Retrieves a single question by its primary key."""
        return db.query(Question).filter(Question.id == question_id).first()

    @classmethod
    def review_question(
        cls,
        db: Session,
        question_id: int,
        review_request: QuestionReviewRequest,
        current_user: User,
    ) -> Tuple[QuestionReview, Question]:
        """Reviews an MCQ and records an auditable decision (APPROVE or REJECT).

        Lifecycle rules:
        1. Question must exist (raises 404 Not Found).
        2. Question must currently have status PENDING_REVIEW (raises 400 Bad Request if already APPROVED or REJECTED).
        3. Target status mapped deterministically:
           - ReviewAction.APPROVE -> QuestionStatus.APPROVED
           - ReviewAction.REJECT -> QuestionStatus.REJECTED
        4. Auditable QuestionReview record created with reviewer_id, action, and comment.
        5. Atomically persists review record and updates question.status in a single transaction.
        """
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {question_id} was not found.",
            )

        if question.status != QuestionStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Question {question_id} has status '{question.status.value}' and cannot be reviewed. "
                    "Only questions in PENDING_REVIEW status can be reviewed."
                ),
            )

        target_status = (
            QuestionStatus.APPROVED
            if review_request.action == ReviewAction.APPROVE
            else QuestionStatus.REJECTED
        )

        review_record = QuestionReview(
            question_id=question.id,
            reviewer_id=current_user.id,
            action=review_request.action,
            comment=review_request.comment.strip() if review_request.comment else None,
        )

        try:
            db.add(review_record)
            question.status = target_status
            db.commit()
            db.refresh(review_record)
            db.refresh(question)
            logger.info(
                f"Question {question.id} reviewed by user {current_user.id}: action={review_request.action.value}, "
                f"new status={question.status.value}"
            )
            return review_record, question
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit review for question {question_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record question review: {str(e)}",
            )

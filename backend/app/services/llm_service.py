import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from app.core.config import settings
from app.models.enums import QuestionDifficulty
from app.schemas.question import MCQGenerationBatch, MCQGenerationItem

logger = logging.getLogger(__name__)


class LLMConfigurationError(Exception):
    """Raised when the Mistral LLM service is misconfigured or missing API credentials."""
    pass


class LLMService:
    """Service wrapper for generating structured multiple choice questions using Mistral AI."""

    _instance: Optional[Any] = None

    @classmethod
    def get_llm_client(cls) -> Any:
        """Instantiates or returns the configured ChatMistralAI client."""
        if cls._instance is not None:
            return cls._instance

        api_key = settings.MISTRAL_API_KEY
        if not api_key or not api_key.strip():
            logger.error("Mistral API key is missing from environment configuration.")
            raise LLMConfigurationError(
                "MISTRAL_API_KEY is not configured. Please set MISTRAL_API_KEY in environment variables."
            )

        model_name = settings.MISTRAL_LLM_MODEL or "mistral-large-latest"
        temp = settings.MISTRAL_TEMPERATURE

        logger.info(
            f"Initializing ChatMistralAI client with model='{model_name}', temperature={temp}"
        )
        cls._instance = ChatMistralAI(
            model=model_name,
            temperature=temp,
            api_key=api_key.strip(),
        )
        return cls._instance

    @classmethod
    def set_llm_client(cls, client: Optional[Any]) -> None:
        """Allows injecting or mocking the LLM client for tests."""
        cls._instance = client

    @staticmethod
    def build_system_prompt() -> str:
        """Constructs the system prompt enforcing MoSPI context, strict factual grounding,
        explicit chunk citation, 4 distinct options, and no invented facts.
        """
        return (
            "You are an expert assessment specialist and curriculum developer for the "
            "Ministry of Statistics and Programme Implementation (MoSPI), Government of India.\n"
            "Your objective is to generate high-quality, rigorously grounded Multiple Choice Questions (MCQs) "
            "for training Indian Statistical Service (ISS) and Subordinate Statistical Service (SSS) officers.\n\n"
            "STRICT GROUNDING & QUALITY RULES:\n"
            "1. FACTUAL GROUNDING: Rely SOLELY and EXCLUSIVELY on the clear facts explicitly stated in the provided SOURCE CONTEXT. "
            "Do NOT extrapolate, assume, or inject external knowledge outside the provided context. If a fact cannot be established "
            "from the context, do not create a question about it.\n"
            "2. EXPLICIT SOURCE CHUNK ATTRIBUTION: Every question MUST be derived from one of the provided chunks. "
            "Each question object MUST include `source_chunk_id` as the exact integer ID from the `[CHUNK ID: X, PAGE: Y]` header of that chunk.\n"
            "3. QUESTION INTEGRITY:\n"
            "   - The question text must be unambiguous and end with a question mark ('?').\n"
            "   - Provide exactly 4 distinct, non-empty options: option_a, option_b, option_c, option_d.\n"
            "   - Do NOT use generic or non-specific options such as 'All of the above', 'None of the above', 'Both A and B', or 'Neither'.\n"
            "   - Exactly one option must be the correct answer based on the source text.\n"
            "   - The `correct_option` field must be strictly one of: 'A', 'B', 'C', or 'D'.\n"
            "4. EDUCATIONAL EXPLANATION:\n"
            "   - Provide a concise explanation clearly citing the facts from the source text that verify the correct option.\n"
            "5. DIFFICULTY CALIBRATION:\n"
            "   - EASY: Direct recall of definitions, terminology, or clearly stated statistics.\n"
            "   - MEDIUM: Conceptual interpretation, relationship between concepts, or methodology application.\n"
            "   - HARD: Detailed comparative analysis, nuanced distinction between similar statistical classifications or formulas.\n"
        )

    @staticmethod
    def build_user_prompt(
        chunks: List[Dict[str, Any]],
        num_questions: int,
        difficulty: Optional[QuestionDifficulty] = None,
        competency_name: Optional[str] = None,
        competency_description: Optional[str] = None,
    ) -> str:
        """Constructs the user prompt containing grounding context chunks with explicit chunk IDs and constraints."""
        context_blocks = []
        for c in chunks:
            chunk_id = c["id"]
            page_no = c.get("page_number") or 1
            text = c.get("text") or ""
            context_blocks.append(
                f"[CHUNK ID: {chunk_id}, PAGE: {page_no}]\n{text.strip()}\n"
            )

        context_str = "\n".join(context_blocks)

        constraints = [f"- Generate exactly {num_questions} unique MCQs."]
        if difficulty:
            constraints.append(f"- Target difficulty level: {difficulty.value}.")
        if competency_name:
            constraints.append(
                f"- Competency Focus: {competency_name}"
                + (f" ({competency_description})" if competency_description else "")
                + ". Prioritize questions that test knowledge relevant to this competency area."
            )

        constraints_str = "\n".join(constraints)

        return (
            "=== SOURCE CONTEXT CHUNKS ===\n"
            f"{context_str}\n"
            "=== GENERATION CONSTRAINTS ===\n"
            f"{constraints_str}\n\n"
            "Generate the requested MCQs based exclusively on the facts stated in the chunks above. "
            "For each question, ensure the question object includes `source_chunk_id` set to the exact integer CHUNK ID corresponding to the chunk used."
        )

    @classmethod
    def generate_mcqs_from_context(
        cls,
        chunks: List[Dict[str, Any]],
        num_questions: int,
        difficulty: Optional[QuestionDifficulty] = None,
        competency_name: Optional[str] = None,
        competency_description: Optional[str] = None,
    ) -> List[MCQGenerationItem]:
        """Calls Mistral LLM with structured output to produce a batch of grounded MCQs."""
        if not chunks:
            logger.warning("No grounding chunks provided for MCQ generation.")
            return []

        client = cls.get_llm_client()
        system_prompt = cls.build_system_prompt()
        user_prompt = cls.build_user_prompt(
            chunks=chunks,
            num_questions=num_questions,
            difficulty=difficulty,
            competency_name=competency_name,
            competency_description=competency_description,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            structured_llm = client.with_structured_output(MCQGenerationBatch)
            response = structured_llm.invoke(messages)

            # Response can be an instance of MCQGenerationBatch or dict depending on client/mock
            if isinstance(response, MCQGenerationBatch):
                items = response.questions
            elif isinstance(response, dict):
                batch = MCQGenerationBatch.model_validate(response)
                items = batch.questions
            elif hasattr(response, "questions"):
                items = response.questions
            else:
                logger.error(f"Unexpected response structure from LLM: {type(response)}")
                items = []

            logger.info(f"LLM generated {len(items)} structured MCQ items.")
            return items

        except LLMConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Mistral LLM MCQ generation failed: {e}")
            raise RuntimeError(f"Mistral LLM MCQ generation failed: {str(e)}")

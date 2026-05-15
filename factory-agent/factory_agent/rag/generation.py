import json
import logging
from typing import List, Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from factory_agent.config import Settings, get_settings
from factory_agent.llm import build_rag_answer_chat_model
from factory_agent.rag.schemas import Chunk, SourceCitation, AnswerResult

logger = logging.getLogger(__name__)

ANSWER_PROMPT = """
You are eMAS Assistant, an expert in industrial maintenance, safety, and operations.

Answer the user's question using ONLY the provided context. Do not use prior knowledge.
If the context does not contain enough information to answer, say so clearly.

Rules:
- Be concise and direct
- Use numbered steps for procedures
- Cite source numbers using superscript format like [^1] after each claim
- Do not include any safety warnings or "Safety Warning:" text in this answer; a separate advisory block will be handled by the system.
- Do not speculate beyond the context

Context:
{context}

{api_data_section}

User question: {query}

Answer:
"""

API_DATA_SECTION_TEMPLATE = """
Live system data (from API):
{api_data}

Use this live data together with the document context to give a complete answer.
"""

SAFETY_WARNING_BLOCK = """
:::safety
**SAFETY WARNING**: This topic involves high-risk procedures.
Always follow your site's approved SOP, obtain required permits, and consult your safety officer before proceeding.
:::
"""

class AnswerGenerator:
    """
    Implements Phase 4 — Answer Generation.
    Builds context, calls LLM to generate answer, and formats citations/safety warnings.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.llm = build_rag_answer_chat_model(self.settings)

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Deserializes JSON strings in metadata back to lists/dicts."""
        clean = {}
        for k, v in metadata.items():
            if isinstance(v, str) and (v.startswith('[') or v.startswith('{')):
                try:
                    clean[k] = json.loads(v)
                except:
                    clean[k] = v
            else:
                clean[k] = v
        return clean

    def generate(
        self, 
        query: str, 
        chunks: List[Chunk], 
        api_data: Optional[Dict[str, Any]] = None,
        route: str = "RAG_ONLY"
    ) -> AnswerResult:
        """
        Generates an answer based on retrieved chunks and optional API data.
        """
        if not chunks and not api_data:
            return AnswerResult(
                answer="No relevant documents or data found for this query.",
                sources=[],
                safety_warning=False,
                route_used=route
            )

        # Clean metadata for all chunks
        for chunk in chunks:
            chunk.metadata = self._clean_metadata(chunk.metadata)

        try:
            # Identify unique documents and map each chunk to a document-level source number
            doc_id_to_num = {}
            unique_doc_chunks = []
            chunk_source_numbers = []

            for chunk in chunks:
                # Use doc_id if available, fallback to title
                d_id = chunk.metadata.get("doc_id") or chunk.metadata.get("title") or "Unknown"
                if d_id not in doc_id_to_num:
                    new_num = len(unique_doc_chunks) + 1
                    doc_id_to_num[d_id] = new_num
                    unique_doc_chunks.append(chunk)
                
                chunk_source_numbers.append(doc_id_to_num[d_id])

            # 1. Build context with document-level source numbers
            context = self.build_context(chunks, chunk_source_numbers)

            # 2. Build API section
            api_section = ""
            if api_data:
                api_section = API_DATA_SECTION_TEMPLATE.format(
                    api_data=json.dumps(api_data, indent=2)
                )

            # 3. Format prompt
            prompt = ANSWER_PROMPT.format(
                context=context,
                api_data_section=api_section,
                query=query
            )

            # 4. Call LLM
            messages = [
                SystemMessage(content="You are an industrial maintenance assistant."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            answer_text = response.content

            # 5. Check for high risk
            has_high_risk = any(c.metadata.get("risk_level") == "high" for c in chunks)
            
            safety_text = None
            if has_high_risk:
                safety_text = "This topic involves high-risk industrial procedures. Always follow your site's approved SOP, obtain required permits, and consult your safety officer before proceeding."
                if SAFETY_WARNING_BLOCK.strip() not in answer_text:
                    answer_text = f"{SAFETY_WARNING_BLOCK.strip()}\n\n{answer_text}".strip()

            # 6. Build citations (one per unique document)
            sources = [self.build_source_citation(c, i + 1) for i, c in enumerate(unique_doc_chunks)]
            
            logger.info(f"Generated {len(sources)} sources for query. Top source: {sources[0].title if sources else 'None'}")
            if sources:
                logger.debug(f"Source 1 details: {sources[0].model_dump()}")

            return AnswerResult(
                answer=answer_text,
                sources=sources,
                safety_warning=has_high_risk,
                safety_content=safety_text,
                route_used=route
            )

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            # A9: Fallback message
            fallback_answer = "Unable to generate a detailed answer. Please check the following sources directly."
            
            # Recalculate unique docs for fallback
            doc_id_to_num = {}
            unique_doc_chunks = []
            for chunk in chunks:
                d_id = chunk.metadata.get("doc_id") or chunk.metadata.get("title") or "Unknown"
                if d_id not in doc_id_to_num:
                    doc_id_to_num[d_id] = len(unique_doc_chunks) + 1
                    unique_doc_chunks.append(chunk)

            sources = [self.build_source_citation(c, i + 1) for i, c in enumerate(unique_doc_chunks)]
            has_high_risk = any(c.metadata.get("risk_level") == "high" for c in chunks)
            return AnswerResult(
                answer=fallback_answer,
                sources=sources,
                safety_warning=has_high_risk,
                safety_content="Safety data may be relevant but could not be fully processed." if has_high_risk else None,
                route_used=route
            )

    def build_context(self, chunks: List[Chunk], source_numbers: Optional[List[int]] = None) -> str:
        """
        Format selected chunks into a structured context block (6.1).
        Uses provided source_numbers to ensure chunks from the same doc share a citation ID.
        """
        if source_numbers is None:
            source_numbers = list(range(1, len(chunks) + 1))
        context_parts = []
        for chunk, src_num in zip(chunks, source_numbers):
            meta = chunk.metadata
            license_tag = f" [{meta.get('license', 'internal')}]"
            if meta.get("license") == "restricted":
                license_tag = " [restricted — internal use only]"
            
            context_parts.append(
                f"[SOURCE {src_num}: {meta.get('title', 'Unknown')}\n"
                f" Organization: {meta.get('organization', 'Unknown')}\n"
                f" Authority: {meta.get('authority_level', 'Unknown')}\n"
                f" Domain: {meta.get('domain', 'Unknown')} / {meta.get('subdomain', 'Unknown')}\n"
                f" Risk Level: {meta.get('risk_level', 'Unknown')}\n"
                f" License:{license_tag}]\n"
                f"{chunk.text}"
            )
        return "\n\n---\n\n".join(context_parts)

    def build_source_citation(self, chunk: Chunk, source_number: int) -> SourceCitation:
        """
        Creates a formatted SourceCitation from chunk metadata (6.4).
        """
        meta = chunk.metadata
        return SourceCitation(
            source_number=source_number,
            doc_id=meta.get("doc_id", "Unknown"),
            title=meta.get("title", "Unknown"),
            organization=meta.get("organization", "Unknown"),
            authority_level=meta.get("authority_level", "Unknown"),
            domain=meta.get("domain", "Unknown"),
            version=meta.get("version", "N/A"),
            license=meta.get("license", "internal"),
            retrieved_date=meta.get("retrieved_date", "")
        )

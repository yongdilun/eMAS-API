import json
import logging
import time
from typing import List, Dict, Any, Optional

from factory_agent.config import Settings, get_settings
from factory_agent.llm.models import build_bge_reranker
from factory_agent.rag.schemas import Chunk, ScoredChunk

logger = logging.getLogger(__name__)


class LLMReranker:
    """
    Implements Phase 3 — Reranking using BGE-Reranker-v2-m3.
    Replaces general LLM reasoning with a high-performance semantic model.
    """

    QUERY_TYPE_TO_DO_NOT_USE = {
        "API_ONLY": [
            "live factory status lookup", "live job scheduling decision",
            "machine availability lookup", "inventory quantity lookup",
            "live machine lock status lookup", "real-time permit approval"
        ],
        "RAG_ONLY": [],
        "API_THEN_RAG": [
            "legal or compliance certification",
            "automatic schedule approval"
        ]
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.model = build_bge_reranker(self.settings)

    def rerank(
        self, 
        query: str, 
        candidates: List[ScoredChunk], 
        route: str, 
        top_k: Optional[int] = None
    ) -> List[Chunk]:
        """
        Main entry point for reranking using BGE Cross-Encoder.
        """
        if not candidates:
            return []
            
        top_k = top_k or self.settings.rag_reranker_top_k
        start_time = time.time()
        
        try:
            # 1. Prepare pairs for BGE
            # We include metadata summary in the doc text to help BGE understand context
            pairs = []
            for sc in candidates:
                meta = sc.chunk.metadata
                context_text = f"Source: {meta.get('title')} Authority: {meta.get('authority_level')} {sc.chunk.text}"
                pairs.append([query, context_text])
            
            # 2. Compute semantic scores
            scores = self.model.compute_score(pairs, max_length=1024)
            
            # 3. Apply industrial boosts (Authority and Safety)
            # We combine the semantic BGE score with our rule-based boosts
            scored_candidates = []
            for idx, sc in enumerate(candidates):
                # BGE scores are typically unbounded; we use them as the base
                base_score = float(scores[idx])
                
                # Apply rules similar to HybridRetriever to maintain safety alignment
                boost = 0.0
                meta = sc.chunk.metadata
                
                # Rule: High Authority boost
                auth = meta.get("authority_level")
                if auth == "mandatory_procedure":
                    boost += 2.0 # Significant boost for BGE scale
                elif auth == "official_public_guidance":
                    boost += 0.8
                
                # Rule: Safety boost
                if meta.get("risk_level") == "high" and any(t in query.lower() for t in ["safe", "loto", "hazard"]):
                    boost += 1.5
                
                sc.boosted_score = base_score + boost
                scored_candidates.append(sc)

            # 4. Sort and filter based on hard rules
            # We sort by our combined BGE + Boost score
            sorted_candidates = sorted(scored_candidates, key=lambda x: x.boosted_score, reverse=True)
            
            # 5. Enforce strict safety rules and filter
            final_chunks = self._process_candidates(query, route, sorted_candidates, top_k)
            
            duration = time.time() - start_time
            logger.info(f"BGE Reranking completed in {duration:.2f}s. Selected {len(final_chunks)} chunks.")
            
            return final_chunks

        except Exception as e:
            logger.error(f"BGE Reranker failed: {e}. Falling back to initial boosted scores.")
            return self._fallback_rerank(candidates, top_k)

    def _process_candidates(
        self, 
        query: str, 
        route: str,
        candidates: List[ScoredChunk],
        top_k: int
    ) -> List[Chunk]:
        """Validates and enforces strict rules on ranked candidates."""
        blocked_phrases = self.QUERY_TYPE_TO_DO_NOT_USE.get(route, [])
        final_chunks = []
        
        for sc in candidates:
            meta = sc.chunk.metadata
            
            # Strict do_not_use_for enforcement
            doc_do_not_use = [phrase.lower() for phrase in meta.get("do_not_use_for", [])]
            if any(blocked in doc_do_not_use for blocked in blocked_phrases):
                continue
            
            final_chunks.append(sc.chunk)
            if len(final_chunks) >= top_k:
                break
                
        # Safety retention fallback
        is_safety_query = any(term in query.lower() for term in ["safe", "loto", "guarding", "confined", "hazard"])
        if is_safety_query:
            high_risk_candidates = [sc.chunk for sc in candidates if sc.chunk.metadata.get("risk_level") == "high"]
            for hr_chunk in high_risk_candidates:
                if hr_chunk not in final_chunks:
                    final_chunks.insert(0, hr_chunk) # Prioritize safety
                    if len(final_chunks) > top_k + 1:
                        final_chunks.pop()

        return final_chunks[:top_k+1]

    def _fallback_rerank(self, candidates: List[ScoredChunk], top_k: int) -> List[Chunk]:
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: x.boosted_score or x.fusion_score or 0.0, 
            reverse=True
        )
        return [sc.chunk for sc in sorted_candidates[:top_k]]

import os
import requests
import re
from typing import List

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Enhanced rule-based classification for medical/document Q&A
RETRIEVAL_INDICATORS = [
    # Medical/scientific content indicators
    r'\b(study|research|trial|patient|treatment|therapy|drug|medication|dose|effect|result|finding|data|analysis|outcome|survival|risk|factor|method|procedure|diagnosis|symptom|condition|disease|cancer|tumor|stage|grade)\b',
    
    # Document-specific questions
    r'\b(according to|in the (study|paper|document|article|research)|based on|mentioned|discussed|reported|shown|demonstrated|indicated|found|concluded)\b',
    r'\b(table|figure|chart|graph|image|appendix|section|chapter|page)\b',
    r'\b(what (did|does|is|was|were)|how (did|does|is|was|were)|when (did|does|is|was|were)|where (did|does|is|was|were)|why (did|does|is|was|were))\b',
    
    # Comparison and analysis questions
    r'\b(compare|comparison|difference|versus|vs|between|among|correlation|association|relationship)\b',
    r'\b(efficacy|effectiveness|safety|toxicity|adverse|side effect|contraindication|indication)\b',
    
    # Statistical and numerical queries
    r'\b(percentage|percent|rate|ratio|number|count|frequency|prevalence|incidence|probability|p-value|confidence|interval|significant|statistic)\b',
    
    # Specific medical terminology
    r'\b(pathology|histology|molecular|genetic|biomarker|protocol|guideline|recommendation|criteria|classification|scoring)\b'
]

DIRECT_INDICATORS = [
    # Simple greetings and basic interactions
    r'^\s*(hello|hi|hey|good morning|good afternoon|good evening|thanks|thank you|bye|goodbye)\s*[.!?]*\s*$',
    
    # Meta questions about the system
    r'\b(how are you|who are you|what can you do|help me|what is this|how does this work)\b',
    
    # Very simple factual questions (but be conservative)
    r'^\s*(yes|no|ok|okay|sure|maybe|perhaps)\s*[.!?]*\s*$'
]

def classify_intent_rules(query: str) -> str:
    """
    Rule-based intent classification optimized for medical/document Q&A.
    Defaults to 'retrieval' to be safe.
    """
    query_lower = query.lower().strip()
    
    # Check for direct intent patterns (be very conservative)
    for pattern in DIRECT_INDICATORS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return "direct"
    
    # Check for retrieval patterns (be generous)
    for pattern in RETRIEVAL_INDICATORS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return "retrieval"
    
    # Default to retrieval for safety - better to retrieve unnecessarily than miss important document content
    return "retrieval"

def classify_intent_hybrid(query: str) -> str:
    """
    Hybrid approach: use rules first, fall back to ML if uncertain
    """
    # First try rule-based classification
    rule_result = classify_intent_rules(query)
    
    # For very short queries or uncertain cases, we could use ML as backup
    if len(query.strip()) < 10:
        return rule_result  # Stick with rules for short queries
    
    return rule_result

def classify_intent(query: str) -> str:
    """
    Main intent classification function.
    Uses rule-based approach optimized for medical document Q&A.
    """
    return classify_intent_hybrid(query)

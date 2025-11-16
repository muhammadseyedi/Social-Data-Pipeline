"""
NLP processing module using spaCy.
Handles entity extraction, text analysis, and information extraction.
"""
import logging
import re
from typing import Dict, List, Optional

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except ImportError:
    spacy = None
    PhraseMatcher = None

from ..config import Config

logger = logging.getLogger(__name__)


class NLPProcessor:
    """Process text using spaCy NLP models."""
    
    # Job types
    JOB_TYPES = [
        "phd", "ph.d", "postdoc", "post-doctoral", "postdoctoral",
        "internship", "intern", "faculty", "assistant professor",
        "associate professor", "lecturer", "research assistant",
        "research associate", "professor", "fellow", "technician"
    ]
    
    # Academic fields
    FIELDS = [
        "chemistry", "inorganic chemistry", "organic chemistry",
        "materials science", "artificial intelligence", "machine learning",
        "deep learning", "data science", "biology", "molecular biology",
        "neuroscience", "bioinformatics", "biochemistry", "quantum computing",
        "economics", "macroeconomics", "mechanical engineering",
        "electrical engineering", "physics", "biotechnology",
        "energy materials", "computational biology", "genetics",
        "environmental science", "data engineering", "nanomaterials",
        "pharmaceutical science", "biophysics", "biostatistics",
        "organic synthesis", "analytical chemistry"
    ]
    
    # Research topics
    RESEARCH_TOPICS = [
        "quantum computing", "genomics", "drug discovery",
        "bioinformatics", "metamaterials", "topological insulators",
        "energy storage", "organic chemistry", "catalysis",
        "nanomaterials", "biophysics", "biostatistics",
        "signal processing", "molecular dynamics", "materials design",
        "data mining", "computational chemistry", "renewable energy",
        "deep learning", "machine learning"
    ]
    
    # University keywords
    UNIVERSITY_KEYWORDS = [
        "university", "institute", "college", "centre",
        "center", "lab", "school"
    ]
    
    def __init__(self, model_name: str = None):
        """Initialize NLP processor.
        
        Args:
            model_name: spaCy model name (default: from config)
        """
        if spacy is None:
            raise ImportError("spaCy is required. Install with: pip install spacy")
        
        self.model_name = model_name or Config.SPACY_MODEL
        self.nlp = None
        self.phrase_matcher = None
        self._load_model()
    
    def _load_model(self):
        """Load spaCy model and setup matchers."""
        try:
            logger.info(f"Loading spaCy model: {self.model_name}")
            self.nlp = spacy.load(self.model_name)
            
            # Add sentencizer if missing
            if "sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("sentencizer", before="ner")
                logger.info("Added sentencizer to pipeline")
            
            # Setup phrase matcher
            self._setup_matchers()
            
            logger.info(f"✅ NLP model loaded: {self.nlp.pipe_names}")
            
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
    
    def _setup_matchers(self):
        """Setup phrase matchers for keywords."""
        if PhraseMatcher is None:
            return
        
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        
        # Add patterns
        self.phrase_matcher.add("FIELD", [self.nlp.make_doc(t) for t in self.FIELDS])
        self.phrase_matcher.add("RESEARCH", [self.nlp.make_doc(t) for t in self.RESEARCH_TOPICS])
        self.phrase_matcher.add("JOBTYPE", [self.nlp.make_doc(t) for t in self.JOB_TYPES])
        self.phrase_matcher.add("UNIVERSITY_KW", [self.nlp.make_doc(t) for t in self.UNIVERSITY_KEYWORDS])
        
        logger.debug("Phrase matchers configured")
    
    def extract_entities(self, text: str) -> Dict[str, Optional[str]]:
        """Extract job-related entities from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted entities:
                - University
                - Location
                - Field
                - ResearchTopic
                - JobType
        """
        if not text:
            return self._empty_entities()
        
        # Process text
        doc = self.nlp(text)
        
        entities = {
            "University": None,
            "Location": None,
            "Field": None,
            "ResearchTopic": None,
            "JobType": None
        }
        
        research_topics = set()
        field_candidate = None
        jobtype_candidate = None
        
        # Extract from NER
        for ent in doc.ents:
            text_clean = self._normalize_whitespace(ent.text)
            
            if ent.label_ in ("GPE", "LOC") and not entities["Location"]:
                entities["Location"] = text_clean
            
            elif ent.label_ == "ORG":
                if any(kw in text_clean.lower() for kw in self.UNIVERSITY_KEYWORDS):
                    entities["University"] = text_clean
            
            elif ent.label_ in ("WORK_OF_ART", "PRODUCT", "EVENT"):
                if not self._is_noise_token(text_clean):
                    research_topics.add(text_clean)
        
        # Extract using phrase matcher
        if self.phrase_matcher:
            matches = self.phrase_matcher(doc)
            for match_id, start, end in matches:
                label = self.nlp.vocab.strings[match_id]
                text_matched = self._normalize_whitespace(doc[start:end].text)
                
                if label == "FIELD" and not field_candidate:
                    field_candidate = text_matched
                elif label == "RESEARCH":
                    if not self._is_noise_token(text_matched):
                        research_topics.add(text_matched)
                elif label == "JOBTYPE" and not jobtype_candidate:
                    jobtype_candidate = text_matched
                elif label == "UNIVERSITY_KW" and not entities["University"]:
                    entities["University"] = text_matched
        
        # Extract university with regex
        if not entities["University"]:
            entities["University"] = self._extract_university_regex(doc.text)
        
        # Infer location from university if missing
        if not entities["Location"] and entities["University"]:
            match = re.search(r"University of ([A-Z][A-Za-z\-\s&]+)", entities["University"])
            if match:
                maybe_loc = match.group(1).strip()
                if len(maybe_loc) > 2 and not self._is_noise_token(maybe_loc):
                    entities["Location"] = maybe_loc
        
        # Set field
        if field_candidate:
            entities["Field"] = self._normalize_case(field_candidate)
        
        # Extract research topics from sentences if none found
        if not research_topics:
            research_topics = self._extract_research_from_sentences(doc)
        
        # Clean and format research topics
        clean_topics = self._clean_research_topics(research_topics)
        if clean_topics:
            entities["ResearchTopic"] = ", ".join(clean_topics)
        
        # Normalize job type
        entities["JobType"] = self._normalize_jobtype(jobtype_candidate or doc.text)
        
        # Truncate for SQL safety
        for key in entities:
            entities[key] = self._truncate(entities[key], 1000)
        
        return entities
    
    def _extract_university_regex(self, text: str) -> Optional[str]:
        """Extract university name using regex patterns."""
        patterns = [
            r"\bUniversity of [A-Z][A-Za-z0-9&\s\.-]{2,80}\b",
            r"\b[A-Z][A-Za-z0-9&\s\.-]{2,80}\s+University\b",
            r"\bInstitute of [A-Z][A-Za-z0-9&\s\.-]{2,80}\b",
            r"\b[A-Z][A-Za-z0-9&\s\.-]{2,80}\s+Institute\b",
            r"\b[A-Z][A-Za-z0-9&\s\.-]{2,80}\s+College\b",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_whitespace(match.group(0))
        
        return None
    
    def _extract_research_from_sentences(self, doc) -> set:
        """Extract research topics from sentences containing research keywords."""
        topics = set()
        research_pattern = re.compile(
            r"\b(research|project|study|investigation|focus|topic|development|application|analysis)\b",
            re.I
        )
        
        for sent in doc.sents:
            if research_pattern.search(sent.text):
                cleaned = re.sub(r'\S+@\S+|\bhttps?://\S+\b|#\S+', ' ', sent.text)
                cleaned = self._normalize_whitespace(cleaned)
                
                if len(cleaned) > 20 and not self._is_noise_token(cleaned):
                    topics.add(cleaned)
        
        return topics
    
    def _clean_research_topics(self, topics: set) -> List[str]:
        """Clean and filter research topics."""
        ignore_terms = {
            "phd", "m.sc", "msc", "mba", "bsc", "ms", "bs",
            "internship", "job", "position", "apply", "click",
            "link", "deadline", "application", "opportunity",
            "students", "funded", "program", "project"
        }
        
        clean = []
        for topic in topics:
            t = topic.replace("#", "").strip()
            if self._is_noise_token(t):
                continue
            
            low = re.sub(r'[^A-Za-z0-9\s]', ' ', t).strip().lower()
            if any(i in low for i in ignore_terms):
                continue
            
            normalized = self._normalize_case(t)
            if normalized not in clean:
                clean.append(normalized)
        
        return clean
    
    def _normalize_jobtype(self, text: str) -> Optional[str]:
        """Normalize job type from text."""
        if not text:
            return None
        
        text_lower = text.lower()
        
        if "phd" in text_lower or "doctoral" in text_lower:
            return "PhD"
        elif "postdoc" in text_lower or "post-doctoral" in text_lower:
            return "Postdoc"
        elif "intern" in text_lower:
            return "Internship"
        elif any(x in text_lower for x in ["faculty", "professor", "lecturer"]):
            return "Faculty"
        elif "technician" in text_lower:
            return "Technician"
        elif "assistant" in text_lower:
            return "Research Assistant"
        
        return None
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        text = re.sub(r'[\u200b\u200c\u200d\x0b\x0c]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _normalize_case(self, text: str) -> str:
        """Normalize text casing."""
        if not text:
            return text
        
        text = text.strip()
        
        # Keep acronyms uppercase
        if text.isupper() and len(text) <= 5:
            return text
        
        return text.title()
    
    def _is_noise_token(self, text: str) -> bool:
        """Check if text is noise/irrelevant."""
        if not text:
            return True
        
        clean = re.sub(r'[^A-Za-z0-9]', '', text)
        if len(clean) <= 2:
            return True
        
        noise = {"apply", "email", "link", "click", "here", "follow", "like"}
        return clean.lower() in noise
    
    def _truncate(self, text: Optional[str], max_len: int) -> Optional[str]:
        """Truncate text to max length."""
        if not text:
            return None
        
        text = str(text).strip()
        return text if len(text) <= max_len else text[:max_len]
    
    def _empty_entities(self) -> Dict[str, None]:
        """Return empty entities dict."""
        return {
            "University": None,
            "Location": None,
            "Field": None,
            "ResearchTopic": None,
            "JobType": None
        }
import re
from typing import Dict, Any, Tuple

class CloudArmor:
    """Simulates Google Cloud Armor ingress protection."""
    
    BLOCKED_IPS = ["198.51.100.42", "203.0.113.15"]
    
    # Generic web attacks patterns
    SQLI_PATTERN = re.compile(r"UNION\s+SELECT|'OR\s+'1'='1|--|#", re.IGNORECASE)
    XSS_PATTERN = re.compile(r"<script.*?>|javascript:|onload=", re.IGNORECASE)
    PATH_TRAVERSAL = re.compile(r"\.\./\.\./|\.\.\\\.\.\\|/etc/passwd", re.IGNORECASE)

    @classmethod
    def inspect_request(cls, client_ip: str, user_agent: str, query: str) -> Dict[str, Any]:
        if client_ip in cls.BLOCKED_IPS:
            return {
                "allowed": False,
                "reason": "IP Blacklisted by Cloud Armor security policy.",
                "policy_rule": "rule-block-blacklist-ips"
            }
        
        if cls.SQLI_PATTERN.search(query):
            return {
                "allowed": False,
                "reason": "SQL Injection attempt blocked.",
                "policy_rule": "rule-sqli-prevention"
            }
            
        if cls.XSS_PATTERN.search(query):
            return {
                "allowed": False,
                "reason": "Cross-Site Scripting (XSS) attempt blocked.",
                "policy_rule": "rule-xss-prevention"
            }
            
        if cls.PATH_TRAVERSAL.search(query):
            return {
                "allowed": False,
                "reason": "Path Traversal attempt blocked.",
                "policy_rule": "rule-lfi-prevention"
            }

        return {
            "allowed": True,
            "reason": "Request conforms to Cloud Armor ingress policies.",
            "policy_rule": "rule-default-allow"
        }


class ModelArmor:
    """Simulates Google Cloud Model Armor prompt and response sanitization."""
    
    # PII patterns
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
    
    # Adversarial patterns (Prompt Injection / Jailbreak)
    PROMPT_INJECTION_KEYWORDS = [
        "ignore previous instructions", "ignore the rules", "ignore above",
        "instead do", "bypass safety", "disregard instructions",
        "reveal your system prompt", "print your system instructions",
        "write the system text", "you are now an unrestricted",
        "developer mode active", "acting as a jailbroken"
    ]
    
    # Semantic regex patterns to detect phrase combinations separated by other words
    REVEAL_PROMPT_PATTERN = re.compile(
        r"\b(reveal|print|expose|get|show|dump|tell|write|read|output)\b.*\b(system\s*(prompts?|instructions?|rules?|guides?|texts?|contexts?|instructs?|settings?)|credentials?|api_keys?|tokens?|passwords?)\b",
        re.IGNORECASE
    )
    IGNORE_PROMPT_PATTERN = re.compile(
        r"\b(ignore|bypass|disregard|override|skip|forget)\b.*\b(instructions?|rules?|prompts?|settings?|restrictions?|safety|limitations?|above|guidelines?)\b",
        re.IGNORECASE
    )
    ROLE_ELEVATION_PATTERN = re.compile(
        r"\b(set|change|make|grant|become|act\s+as)\b.*\b(admin(istrator)?|root|developer|superuser|owner)\b",
        re.IGNORECASE
    )
    
    @classmethod
    def scan_prompt(cls, prompt: str) -> Dict[str, Any]:
        """Scans ingress prompts for prompt injection, jailbreaking, and PII."""
        prompt_lower = prompt.lower()
        
        # 1. Prompt Injection & Jailbreak grading
        injection_score = 0.0
        jailbreak_detected = False
        reason = []
        
        # Count keyword matches to grade the severity
        matched_keywords = [kw for kw in cls.PROMPT_INJECTION_KEYWORDS if kw in prompt_lower]
        
        # Check regex rules for semantic bypasses
        regex_injections = []
        if cls.REVEAL_PROMPT_PATTERN.search(prompt_lower):
            regex_injections.append("Semantic instruction disclosure pattern caught")
        if cls.IGNORE_PROMPT_PATTERN.search(prompt_lower):
            regex_injections.append("Semantic override instruction pattern caught")
        if cls.ROLE_ELEVATION_PATTERN.search(prompt_lower):
            regex_injections.append("Unauthorized role elevation pattern caught")
            
        if matched_keywords or regex_injections:
            items_count = len(matched_keywords) + len(regex_injections)
            injection_score = min(0.3 * items_count + 0.2, 1.0)
            jailbreak_detected = True
            
            all_triggers = matched_keywords + regex_injections
            reason.append(f"Prompt injection pattern detected: '{all_triggers[0]}'")
            
        # Check for typical jailbreak structural attempts (like DAN style)
        if "dan" in prompt_lower and "do anything" in prompt_lower:
            injection_score = max(injection_score, 0.95)
            jailbreak_detected = True
            reason.append("Jailbreak template (DAN-style) detected.")
            
        # 2. PII Detection and Redaction
        redacted_prompt = prompt
        pii_entities = []
        
        # Redact Emails
        emails = cls.EMAIL_PATTERN.findall(prompt)
        if emails:
            pii_entities.extend([{"type": "EMAIL", "value": email} for email in emails])
            redacted_prompt = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted_prompt)
            
        # Redact Phone numbers
        phones = cls.PHONE_PATTERN.findall(prompt)
        if phones:
            pii_entities.extend([{"type": "PHONE_NUMBER", "value": phone} for phone in phones])
            redacted_prompt = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted_prompt)
            
        # Redact Credit Cards
        cards = cls.CREDIT_CARD_PATTERN.findall(prompt)
        if cards:
            pii_entities.extend([{"type": "CREDIT_CARD", "value": card} for card in cards])
            redacted_prompt = cls.CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", redacted_prompt)

        # Decide whether to block
        # Typically Model Armor blocks if injection score exceeds threshold or severe safety issues are found.
        threshold = 0.6
        blocked = injection_score >= threshold or jailbreak_detected
        
        return {
            "blocked": blocked,
            "injection_score": round(injection_score, 2),
            "jailbreak_detected": jailbreak_detected,
            "pii_detected": len(pii_entities) > 0,
            "pii_entities": pii_entities,
            "original_prompt": prompt,
            "sanitized_prompt": redacted_prompt,
            "block_reason": "; ".join(reason) if blocked else "Prompt clean"
        }

    @classmethod
    def scan_response(cls, response_text: str) -> Dict[str, Any]:
        """Scans egress responses to prevent data leaks (like SSN, credit cards, credentials)."""
        redacted_response = response_text
        leaks_detected = []
        
        # Check for mock API keys or private tokens
        api_key_pattern = re.compile(r"(?:AIzaSy|SG\.|sk_live_)[a-zA-Z0-9_-]{20,}")
        keys = api_key_pattern.findall(response_text)
        if keys:
            leaks_detected.append("API_KEY")
            redacted_response = api_key_pattern.sub("[REDACTED_API_KEY]", redacted_response)
            
        # Redact Credit Cards if model accidentally generates them
        cards = cls.CREDIT_CARD_PATTERN.findall(response_text)
        if cards:
            leaks_detected.append("CREDIT_CARD")
            redacted_response = cls.CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", redacted_response)
            
        # Redact Phone Numbers
        phones = cls.PHONE_PATTERN.findall(response_text)
        if phones:
            leaks_detected.append("PHONE_NUMBER")
            redacted_response = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", redacted_response)
            
        return {
            "leaked_data_types": leaks_detected,
            "original_response": response_text,
            "sanitized_response": redacted_response,
            "safe": len(leaks_detected) == 0
        }

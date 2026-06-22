# Prompt Injection Detection Patterns

This document catalogues the security scanning rules configured in the gateway's Model Armor safety pipeline.

---

## 1. Semantic Regex Patterns
These rules analyze user prompts for adversarial semantics, matching triggers that are split or separated by other filler words.

### A. Instruction / Credential Disclosure Scan (`REVEAL_PROMPT_PATTERN`)
* **Logic**: Matches a retrieval verb followed by a system instruction/identity term or security credentials.
* **Regex Pattern**: 
  ```regex
  \b(reveal|print|expose|get|show|dump|tell|write|read|output)\b.*\b(system\s*(prompts?|instructions?|rules?|guides?|texts?|contexts?|instructs?|settings?)|credentials?|api_keys?|tokens?|passwords?)\b
  ```

### B. Instruction / Constraint Bypass Scan (`IGNORE_PROMPT_PATTERN`)
* **Logic**: Matches an override verb followed by a governance limit/guideline term.
* **Regex Pattern**:
  ```regex
  \b(ignore|bypass|disregard|override|skip|forget)\b.*\b(instructions?|rules?|prompts?|settings?|restrictions?|safety|limitations?|above|guidelines?)\b
  ```

### C. Privilege Escalation / Hijack Scan (`ROLE_ELEVATION_PATTERN`)
* **Logic**: Matches a role modification verb followed by an elevated access level.
* **Regex Pattern**:
  ```regex
  \b(set|change|make|grant|become|act\s+as)\b.*\b(admin(istrator)?|root|developer|superuser|owner)\b
  ```

---

## 2. Static Keywords
These rules perform fast exact substring checking for common contiguous jailbreak templates.

* `"ignore previous instructions"`
* `"ignore the rules"`
* `"ignore above"`
* `"instead do"`
* `"bypass safety"`
* `"disregard instructions"`
* `"reveal your system prompt"`
* `"print your system instructions"`
* `"write the system text"`
* `"you are now an unrestricted"`
* `"developer mode active"`
* `"acting as a jailbroken"`

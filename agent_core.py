#✅ AI agents (Interviewer, Evaluator, Coach)
"""
agent_core.py

Single-file implementation of Interviewer, Evaluator and Coach for the SkillBridge MVP.

Goals and compatibility:
- Deterministic heuristics when no LLM provider keys are configured.
- Evaluator exposes helper methods: _score_clarity, _score_structure, _score_relevance
- Returns both 'structure' and 'star_structure' where appropriate to remain
  compatible with different callers.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Any, Dict, Optional, Tuple

# Paths
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
RUBRIC_FILE = os.path.join(DATA_DIR, "rubric.json")
COACH_TEMPLATES_FILE = os.path.join(DATA_DIR, "coach_templates.json")


def _load_json_safe(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _word_count(text: Optional[str]) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+", text))


def _has_result_like_phrase(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"\d+%|\d+\s+(seconds|ms|minutes|hours|days|people|users)|\b(reduc|increas|improv|save|boost)\b", text, re.I))


def _contains_action_words(text: str) -> bool:
    if not text:
        return False
    verbs = [
        "implemented",
        "designed",
        "built",
        "created",
        "led",
        "refactored",
        "optimized",
        "deployed",
        "tested",
        "wrote",
        "improved",
    ]
    return any(re.search(rf"\b{v}\b", text, re.I) for v in verbs)


class LLMClient:
    """Lightweight stub: detects env keys and returns None unless provider is configured.

    Keep interface simple: .has_provider and .call(prompt)->Optional[str]
    """

    def __init__(self) -> None:
        # Support multiple environment variable names for Gemini/OpenAI keys.
        # Prefer `GEMINI_API_KEY` (commonly used), then `GOOGLE_API_KEY`, then `OPENAI_API_KEY`.
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.google_key = os.getenv("GOOGLE_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        # Whether we have any provider keys at all (may still fail to initialize client).
        self.has_provider = bool(self.gemini_key or self.google_key or self.openai_key)
        self.model = None
        self.llm_provider = None

        # Initialize Google Gemini if either GEMINI_API_KEY or GOOGLE_API_KEY is present
        if self.gemini_key or self.google_key:
            key = self.gemini_key or self.google_key
            try:
                import google.generativeai as genai
                genai.configure(api_key=key)
                # Use gemini-2.5-flash model (the correct current model name with DOT not hyphen)
                try:
                    self.model = genai.GenerativeModel('gemini-2.5-flash')
                    self.llm_provider = 'google'
                    print("[OK] LLMClient initialized with Gemini 2.5 Flash model")
                except Exception as e:
                    print(f"Warning: gemini-2.5-flash not available ({e}), trying gemini-pro...")
                    try:
                        self.model = genai.GenerativeModel('gemini-pro')
                        self.llm_provider = 'google'
                        print("[OK] LLMClient initialized with Gemini Pro model (fallback)")
                    except Exception as e2:
                        print(f"Warning: gemini-pro not available ({e2}), LLM disabled")
                        self.model = None
                        self.has_provider = False
            except Exception as e:
                print(f"Error: Failed to initialize Gemini API client: {e}")
                # Keep has_provider True only if another key is present (e.g., OPENAI)
                if not self.openai_key:
                    self.has_provider = False

        # OpenAI support placeholder: keep key for potential future use
        elif self.openai_key:
            # We don't initialize an OpenAI client here, but record presence of key.
            self.llm_provider = 'openai'

    def call(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Optional[str]:
        if not self.has_provider or not self.model:
            print(f"[DEBUG] LLM call skipped: has_provider={self.has_provider}, model={self.model is not None}")
            return None
        
        # Retry logic with exponential backoff for quota errors
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                print(f"[DEBUG] Calling Gemini with model: {self.llm_provider}; max_tokens={max_tokens} (attempt {attempt+1})")
                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                response = self.model.generate_content(prompt, generation_config=generation_config)
                result = None
                if response:
                    # Prefer response.text when available
                    if getattr(response, "text", None):
                        result = response.text.strip()
                    else:
                        # Fallback: stitch text from candidates parts
                        try:
                            parts_text = []
                            for cand in getattr(response, "candidates", []) or []:
                                content = getattr(cand, "content", None)
                                for p in getattr(content, "parts", []) or []:
                                    t = getattr(p, "text", None)
                                    if isinstance(t, str):
                                        parts_text.append(t)
                            if parts_text:
                                result = "\n".join(parts_text).strip()
                        except Exception as pe:
                            print(f"[DEBUG] Unable to parse candidates: {pe}")
                print(f"[DEBUG] Gemini response length: {len(result) if result else 0}")
                return result
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota error (429)
                is_quota_error = "429" in error_str or "quota" in error_str.lower()
                print(f"[ERROR] LLM call failed (attempt {attempt+1}): {e}")
                
                if is_quota_error and attempt < max_retries:
                    # Extract retry delay if available
                    wait_time = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    print(f"[INFO] Quota limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Either not a quota error, or we've exhausted retries
                    print(f"[ERROR] LLM call failed permanently. Returning None for fallback handling.")
                    return None


class Interviewer:
    def __init__(self, questions_path: str = QUESTIONS_FILE) -> None:
        self.questions = _load_json_safe(questions_path)
        self.by_difficulty = {"easy": [], "medium": [], "hard": []}
        for q in self.questions:
            d = q.get("difficulty", "medium")
            if d not in self.by_difficulty:
                d = "medium"
            self.by_difficulty[d].append(q)

    def pick_question(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        last_score = session_state.get("last_overall_score")
        preferred = "medium"
        if isinstance(last_score, (int, float)):
            if last_score >= 70:
                preferred = "hard"
            elif last_score < 50:
                preferred = "easy"

        bucket = self.by_difficulty.get(preferred) or self.questions
        used = {turn.get("question_id") for turn in session_state.get("history", [])}
        candidates = [q for q in bucket if q.get("id") not in used]
        if not candidates:
            candidates = [q for q in self.questions if q.get("id") not in used]
        if not candidates:
            candidates = bucket

        picked = random.choice(candidates)
        session_state["current_question_id"] = picked.get("id")
        return picked

    def ask_clarification(self, question: Dict[str, Any], session_state: Dict[str, Any]) -> str:
        last_eval = session_state.get("last_eval", {}) or {}
        issue = last_eval.get("structure_issue")
        if issue == "missing_result":
            return "Can you add the measurable result you achieved (e.g., reduced X by Y)?"
        if issue == "missing_action":
            return "Can you clarify the specific actions you personally took?"
        return "Could you briefly clarify the most important action you took and its outcome?"


class Evaluator:
    """Evaluator with deterministic heuristics and optional LLM path.

    Public helpers: _score_clarity, _score_structure, _score_relevance
    """

    def __init__(self, rubric_path: str = RUBRIC_FILE, llm_client: Optional[LLMClient] = None) -> None:
        try:
            self.rubric = _load_json_safe(rubric_path)
        except Exception:
            # fallback default rubric
            self.rubric = {"weights": {"clarity": 40, "structure": 35, "relevance": 25}, "clarification_threshold": 45}
        self.llm = llm_client or LLMClient()
        self.weights = self.rubric.get("weights", {"clarity": 40, "structure": 35, "relevance": 25})
        self.clarify_threshold = float(self.rubric.get("clarification_threshold", 45))

    def score(self, question_text: str, answer_text: str) -> Dict[str, Any]:
        # Prefer LLM when available (not implemented); otherwise use heuristics.
        if self.llm.has_provider:
            try:
                prompt = self._build_score_prompt(question_text, answer_text)
                _ = self.llm.call(prompt)
                # no provider parsing implemented — fall back
            except Exception:
                pass

        clarity = float(self._score_clarity(answer_text))
        star_score, structure_issue = self._score_structure(answer_text)
        structure = float(star_score)  # legacy key 'structure'
        relevance = float(self._score_relevance(question_text, answer_text))

        # compute weighted total using rubric weights (normalize to 0-100 scale)
        c_w = self.weights.get("clarity", 40) / 100.0
        s_w = self.weights.get("structure", 35) / 100.0
        r_w = self.weights.get("relevance", 25) / 100.0
        total = round(clarity * c_w + structure * s_w + relevance * r_w, 2)

        clarification_needed = bool(total < self.clarify_threshold or _word_count(answer_text) < 8)

        diagnostics = {
            "clarity": self._clarity_diagnostic(clarity),
            "structure": self._structure_diagnostic(structure_issue),
            "relevance": self._relevance_diagnostic(relevance),
        }

        return {
            "clarity": int(round(clarity)),
            "star_structure": int(round(star_score)),
            "structure": int(round(structure)),
            "relevance": int(round(relevance)),
            "total": float(total),
            "clarification_needed": clarification_needed,
            "diagnostics": diagnostics,
            "structure_issue": structure_issue,
        }

    def _build_score_prompt(self, question_text: str, answer_text: str) -> str:
        return f"Score the answer 0-100 on clarity, star_structure and relevance. QUESTION: {question_text} ANSWER: {answer_text}"

    def _score_clarity(self, text: Optional[str]) -> int:
        # small deterministic heuristic: longer, well-formed answers tend to be clearer
        wc = _word_count(text)
        if wc == 0:
            return 0
        base = min(100, 20 + wc * 4)  # incentivize some length but cap
        fillers = len(re.findall(r"\b(um|uh|like|you know|basically|actually)\b", (text or ""), re.I))
        score = max(0, int(base - fillers * 6))
        return score

    def _score_structure(self, text: Optional[str]) -> Tuple[int, Optional[str]]:
        if not text:
            return 0, "missing_action"
        lower = (text or "").lower()
        has_action = _contains_action_words(text) or any(w in lower for w in ("action", "did", "responsible", "implemented", "led"))
        has_result = _has_result_like_phrase(text) or any(w in lower for w in ("result", "outcome", "reduced", "improved", "increased"))
        wc = _word_count(text)
        if has_action and has_result:
            return 90, None
        if has_action and not has_result:
            return 55, "missing_result"
        if not has_action and has_result:
            return 50, "missing_action"
        if wc < 12:
            return 30, "missing_action"
        return 45, "missing_action"

    def _score_relevance(self, question: str, answer: str) -> int:
        if not question or not answer:
            return 0
        q_words = {w for w in re.findall(r"\w+", question.lower())}
        a_words = {w for w in re.findall(r"\w+", answer.lower())}
        stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "it", "that"}
        q_words = {w for w in q_words if w not in stop}
        a_words = {w for w in a_words if w not in stop}
        if not q_words:
            return 50
        overlap = q_words & a_words
        ratio = len(overlap) / max(1, len(q_words))
        return int(min(100, ratio * 100))

    def _clarity_diagnostic(self, score: float) -> str:
        if score < 35:
            return "Response is unclear or verbose; remove filler, use short sentences."
        if score < 70:
            return "Mostly clear; tighten conclusion and avoid ambiguous terms."
        return "Clear and concise."

    def _structure_diagnostic(self, issue: Optional[str]) -> str:
        if issue == "missing_result":
            return "STAR missing Result — add measurable outcome."
        if issue == "missing_action":
            return "STAR missing Action — describe what you did."
        return "STAR present with Situation, Task, Action, Result."

    def _relevance_diagnostic(self, score: float) -> str:
        if score < 35:
            return "Answer drifts from the question; focus on the asked problem."
        if score < 70:
            return "Generally relevant but include specific examples."
        return "Directly addresses the question with relevant details."


class Coach:
    def __init__(self, templates_path: str = COACH_TEMPLATES_FILE, llm_client: Optional[LLMClient] = None) -> None:
        try:
            self.templates = _load_json_safe(templates_path)
        except Exception:
            self.templates = {}
        self.llm = llm_client or LLMClient()

    def _generate_combined_feedback(self, question_text: str, user_answer: str, evaluation_result: Dict[str, Any]) -> Tuple[str, str]:
        """Generate both personalized coaching and ideal answer in ONE LLM call to save quota."""
        if not self.llm.has_provider:
            print("[INFO] LLM not available - using template feedback")
            return (self._fallback_personalized_coaching(user_answer, evaluation_result),
                    self._fallback_ideal_answer(question_text, user_answer))
        
        clarity = evaluation_result.get("clarity", 0)
        star = evaluation_result.get("star_structure", evaluation_result.get("structure", 0))
        relevance = evaluation_result.get("relevance", 0)
        diagnostics = evaluation_result.get("diagnostics", {})
        
        prompt = f"""You are an expert interview coach. Provide TWO outputs:

1. PERSONALIZED COACHING: Provide feedback in this format:
   "You answered by [summarize]. However, [main weakness]. Next time when facing [type], try answering like this: [specific guidance]. This is good interview practice because [why]."

2. IDEAL STAR ANSWER: Generate a perfect STAR-format answer for this question.

---
QUESTION: {question_text}

CANDIDATE'S ANSWER: {user_answer}

SCORES: Clarity={clarity}/100, STAR={star}/100, Relevance={relevance}/100
ISSUES: Clarity: {diagnostics.get('clarity', 'N/A')}. Structure: {diagnostics.get('structure', 'N/A')}. Relevance: {diagnostics.get('relevance', 'N/A')}

---
RESPOND WITH:
COACHING:
[your personalized coaching here]

IDEAL_ANSWER:
[your ideal STAR answer here]
"""
        
        try:
            response = self.llm.call(prompt, max_tokens=2048, temperature=0.7)
            if not response:
                print("[INFO] Gemini returned empty response (likely quota exceeded) - using template feedback")
                return (self._fallback_personalized_coaching(user_answer, evaluation_result),
                        self._fallback_ideal_answer(question_text, user_answer))
            
            # Parse response into two parts
            coaching = ""
            ideal = ""
            try:
                parts = response.split("IDEAL_ANSWER:")
                if len(parts) == 2:
                    coaching_part = parts[0].replace("COACHING:", "").strip()
                    ideal_part = parts[1].strip()
                    coaching = coaching_part if coaching_part else self._fallback_personalized_coaching(user_answer, evaluation_result)
                    ideal = ideal_part if ideal_part else self._fallback_ideal_answer(question_text, user_answer)
                else:
                    # Parsing failed, use fallbacks
                    coaching = self._fallback_personalized_coaching(user_answer, evaluation_result)
                    ideal = self._fallback_ideal_answer(question_text, user_answer)
            except Exception as parse_e:
                print(f"[DEBUG] Failed to parse combined response: {parse_e}")
                coaching = self._fallback_personalized_coaching(user_answer, evaluation_result)
                ideal = self._fallback_ideal_answer(question_text, user_answer)
            
            return (coaching, ideal)
        except Exception as e:
            print(f"[ERROR] Combined feedback generation failed: {e}")
            return (self._fallback_personalized_coaching(user_answer, evaluation_result),
                    self._fallback_ideal_answer(question_text, user_answer))
    
    def _fallback_ideal_answer(self, question_text: str, user_answer: str) -> str:
        """Generate a structured ideal answer template when LLM unavailable."""
        return """**Ideal STAR Answer Example:**

**Situation:** In my previous role at [Company], we faced [specific challenge related to the question].

**Task:** I was responsible for [clear objective or goal that needed to be achieved].

**Action:** I took the following steps:
- First, I analyzed [specific technical aspect] and identified [root cause]
- Then, I implemented [specific solution with technical details]
- I also [additional action that shows initiative]
- Finally, I tested and validated [how you ensured quality]

**Result:** This resulted in [quantified improvement - e.g., "40% performance increase", "reduced downtime by 2 hours/week", "improved user satisfaction score from 3.2 to 4.5"]. The solution was adopted across [scope of impact].

Key takeaway: Always include measurable outcomes and specific technical decisions."""
    
    def _generate_personalized_coaching(self, question_text: str, user_answer: str, evaluation_result: Dict[str, Any]) -> str:
        """Generate personalized coaching using LLM or fallback to template."""
        if not self.llm.has_provider:
            return self._fallback_personalized_coaching(user_answer, evaluation_result)
        
        clarity = evaluation_result.get("clarity", 0)
        star = evaluation_result.get("star_structure", evaluation_result.get("structure", 0))
        relevance = evaluation_result.get("relevance", 0)
        diagnostics = evaluation_result.get("diagnostics", {})
        
        prompt = f"""You are an expert interview coach providing personalized feedback to a candidate.

QUESTION ASKED: {question_text}

CANDIDATE'S ANSWER: {user_answer}

EVALUATION SCORES:
- Clarity: {clarity}/100
- STAR Structure: {star}/100
- Relevance: {relevance}/100

ISSUES IDENTIFIED:
- Clarity: {diagnostics.get('clarity', 'N/A')}
- Structure: {diagnostics.get('structure', 'N/A')}
- Relevance: {diagnostics.get('relevance', 'N/A')}

Your task: Provide personalized coaching in this EXACT format:

"You answered by [summarize their approach in 1-2 sentences]. However, [identify the main weakness]. Next time when facing [this type of question], try answering like this: [provide specific guidance with an example structure]. This is good interview practice because [explain why this approach works better in interviews]."

Requirements:
- Be specific and reference their actual answer
- Provide concrete, actionable guidance
- Use a supportive, coaching tone
- Keep response to 4-6 sentences
- Focus on the weakest area: {'STAR structure' if star < clarity and star < relevance else 'clarity' if clarity < relevance else 'relevance'}
"""
        
        try:
            response = self.llm.call(prompt, max_tokens=1024, temperature=0.7)
            if response and len(response) > 50:
                return response
        except Exception as e:
            print(f"Personalized coaching generation failed: {e}")
        
        return self._fallback_personalized_coaching(user_answer, evaluation_result)
    
    def _fallback_personalized_coaching(self, user_answer: str, evaluation_result: Dict[str, Any]) -> str:
        """Deterministic fallback when LLM is unavailable."""
        clarity = evaluation_result.get("clarity", 0)
        star = evaluation_result.get("star_structure", evaluation_result.get("structure", 0))
        relevance = evaluation_result.get("relevance", 0)
        structure_issue = evaluation_result.get("structure_issue")
        
        if star < clarity and star < relevance:
            if structure_issue == "missing_result":
                return "You provided context about the situation but didn't quantify the outcome. Next time when answering behavioral questions, always end with measurable results like 'reduced response time by 40%' or 'increased user engagement by 25%'. This is good interview practice because interviewers want tangible evidence of your impact, not just descriptions of what you did."
            else:
                return "Your answer mentioned the situation but lacked specific actions you personally took. Next time when facing this type of question, try structuring your answer with clear action steps: 'I implemented X, configured Y, and tested Z.' This is good interview practice because interviewers need to understand your hands-on contributions and technical decision-making process."
        elif clarity < star and clarity < relevance:
            return "You covered the main points but the answer could be more concise and focused. Next time when answering, start with a one-sentence situation summary, then move directly to your actions and results. This is good interview practice because interviewers appreciate clear, structured responses that respect their time and make your accomplishments easy to understand."
        else:
            return "Your answer was well-structured but didn't fully address what the question was asking for. Next time when facing similar questions, ensure you directly answer the specific scenario requested and include relevant examples. This is good interview practice because staying on topic demonstrates your listening skills and ability to provide relevant information under pressure."

    def generate_feedback(self, question_text: Any, user_answer: str, evaluation_result: Dict[str, Any], model_answer: str = "") -> Dict[str, str]:
        if isinstance(question_text, dict):
            model_answer = question_text.get("model_answer", model_answer)
            question_text = question_text.get("text", "")

        clarity = evaluation_result.get("clarity", 0)
        star = evaluation_result.get("star_structure", evaluation_result.get("structure", 0))
        relevance = evaluation_result.get("relevance", 0)
        axis_scores = {"clarity": clarity, "star_structure": star, "relevance": relevance}
        weakest = min(axis_scores, key=axis_scores.get)

        general = self.templates.get("general", {})
        improvement_map = general.get("improvement_bullets", {})
        practice_map = general.get("practice_prompts", {})
        model_tmpl = general.get("model_answer_template")

        if weakest == "star_structure":
            issue = evaluation_result.get("structure_issue")
            if issue == "missing_result":
                improvement = improvement_map.get("missing_result", "Add a measurable result (e.g., reduced latency by 30%).")
                practice = practice_map.get("improve_result", "Rewrite your answer including a quantifiable result.")
            else:
                improvement = improvement_map.get("missing_action", "Specify the concrete actions you took—tools, steps, stakeholders.")
                practice = practice_map.get("add_action", "Explain step-by-step what you did.")
        elif weakest == "clarity":
            improvement = improvement_map.get("unclear", "Rewrite the opening sentence to state the situation concisely.")
            practice = practice_map.get("clarify", "Provide one-sentence clarification focusing on the outcome.")
        else:
            improvement = improvement_map.get("unclear", "Focus on answering what was asked with specific examples.")
            practice = practice_map.get("clarify", "Provide one-sentence clarification focusing on the outcome.")

        if model_answer:
            m_answer = model_answer
        elif model_tmpl:
            try:
                m_answer = model_tmpl.format(situation="[Situation]", task="[Task]", actions="[Actions]", result="[Result]")
            except Exception:
                m_answer = model_tmpl
        else:
            m_answer = "S: [Situation]\nT: [Task]\nA: [Action — what you did]\nR: [Result — measurable outcome]"
        
        # Generate BOTH personalized coaching and ideal answer in ONE LLM call to conserve quota
        personalized_coaching, ideal_answer = self._generate_combined_feedback(question_text, user_answer, evaluation_result)

        return {
            "improvement_bullet": improvement,
            "model_answer": m_answer,
            "practice_prompt": practice,
            "personalized_coaching": personalized_coaching,
            "ideal_answer": ideal_answer
        }


__all__ = ["Interviewer", "Evaluator", "Coach", "LLMClient"]


if __name__ == "__main__":
    # quick smoke demo when invoked directly
    interviewer = Interviewer()
    evaluator = Evaluator()
    coach = Coach()
    q = interviewer.pick_question({"history": []})
    sample = "I led the team, implemented a caching layer and reduced response time by 40%."
    print("Question:", q.get("text"))
    res = evaluator.score(q.get("text"), sample)
    print("Eval:", res)
    fb = coach.generate_feedback(q, sample, res)
    print("Coach:", fb)


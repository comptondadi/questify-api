# app/agent.py
import requests
import json
from ddgs import DDGS 
from groq import Groq
from .config import settings

# Initialize the Groq client here, it can be used by the agent class
groq_client = Groq(api_key=settings.groq_api_key)

class QuestAgent:
    """
    The Dungeon Master for Questify. This agent uses an LLM
    to provide contextual feedback and side quests to the user.
    """
    def __init__(self):
        # --- Local Ollama Configuration ---
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_model = "llama3"
        
        # --- Cloud Groq Configuration ---
        self.groq_model = "llama3-8b-8192"

    # =========================================================================
    #                    CORE LLM & TOOLING METHODS
    # =========================================================================

    def _run_ollama_and_parse_json(self, prompt: str) -> dict | None:
        """Sends a prompt to a LOCAL Ollama instance."""
        try:
            payload = {"model": self.ollama_model, "prompt": prompt, "stream": False, "format": "json"}
            response = requests.post(self.ollama_url, json=payload, timeout=180)
            response.raise_for_status()
            json_string = response.json().get("response")
            return json.loads(json_string) if json_string else None
        except requests.exceptions.RequestException as e:
            print(f"[AGENT ERROR] Could not communicate with Ollama: {e}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[AGENT ERROR] Could not parse JSON from Ollama response: {e}")
            return None

    def _run_groq_and_parse_json(self, prompt: str) -> dict | None:
        """Sends a prompt to the CLOUD-BASED Groq API."""
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model,
                response_format={"type": "json_object"},
            )
            response_content = chat_completion.choices[0].message.content
            print(f"--- RAW LLM RESPONSE ---\n{response_content}\n--- END RAW RESPONSE ---")
            return json.loads(response_content) if response_content else None
        except json.JSONDecodeError as e:
            print(f"!!!!!!!! AGENT JSON PARSE ERROR !!!!!!!!")
            print(f"Error: {e}")
            # This will show us exactly what Groq sent back that wasn't valid JSON.
            print(f"RAW UNPARSABLE RESPONSE: {response_content}") 
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return None
        except Exception as e:
            print(f"[AGENT ERROR] An unexpected error occurred: {e}")
            return None
    # --- THIS IS THE "TWO-PASS" FIX FOR WEB SEARCH ---
    def _search_web(self, query: str, num_results: int = 3) -> tuple[str, list]:
        """
        Performs a web search and returns a formatted string for the LLM prompt
        AND the raw list of result objects for programmatic use.
        """
        print(f"[AGENT ACTION] Performing web search for: '{query}'")
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=num_results))
            if not raw_results:
                return "No relevant information found.", []
            
            # Create a simplified string for the LLM prompt (without URLs)
            formatted_string = "\n\n".join(
                [f"Title: {res['title']}\nSnippet: {res['body']}" for res in raw_results]
            )
            return formatted_string, raw_results
        except Exception as e:
            print(f"[AGENT ERROR] Web search failed: {e}")
            return "Web search failed.", []

    # =========================================================================
    #                       MAIN AGENT LOGIC METHODS
    # =========================================================================

    def get_completion_insight(self, quest_title: str, quest_category: str, user_level: int, recent_history: str, discipline_summary: dict, use_groq: bool = False) -> dict:
        """The main 'DM Loop' for quest completion."""
        print(f"[AGENT] Generating insight for quest: '{quest_title}' (Category: {quest_category})")

        llm_runner = self._run_groq_and_parse_json if use_groq else self._run_ollama_and_parse_json
        
        summary_str = (
            f"User Performance: {discipline_summary.get('completions_today', 0)} completions today, "
            f"{discipline_summary.get('completions_this_week', 0)} this week. "
            f"Focusing on {discipline_summary.get('favorite_category', 'N/A')}."
        )

        reasoning_prompt = f"""
A user at Level {user_level} completed "{quest_title}" (Category: {quest_category}). Context: {summary_str}. History: {recent_history}.
Generate a specific, relevant web search query to help them improve.
Respond with JSON: {{"search_query": "string"}}
"""
        search_json = llm_runner(reasoning_prompt)
        
        if not search_json or "search_query" not in search_json:
            return {"dialogue": f"You have conquered '{quest_title}'! Well done, Traveler."}

        search_query = search_json["search_query"]
        search_results_str, raw_search_results = self._search_web(search_query)

        output_prompt = f"""
You are the Chronicler, a Dungeon Master for Questify. A user (Lvl {user_level}) completed "{quest_title}".
Their context: {summary_str} and {recent_history}.
Your web search for "{search_query}" found:
---
{search_results_str}
---
Craft a response and a new "Side Quest". Your response MUST be a JSON object with "dialogue" and "side_quest" keys.
- "dialogue": Your narrative commentary.
- "side_quest": An object with 'title', 'description', 'category', 'xp_value' (20-75). DO NOT include a 'resource_link'.
"""
        final_insight = llm_runner(output_prompt)

        if not final_insight:
            return {"dialogue": f"Your efforts on '{quest_title}' have been noted in the chronicles!"}

        # --- "TWO-PASS" FIX: Programmatically add the real link ---
        if raw_search_results and "side_quest" in final_insight:
            first_real_link = raw_search_results[0].get('href')
            if first_real_link:
                final_insight["side_quest"]["resource_link"] = first_real_link
        
        return final_insight

    def get_reengagement_insight(self, user_level: int, days_missed: int, discipline_summary: dict, use_groq: bool = False) -> dict:
        """Generates a 'Redemption Quest' for an inactive user."""
        print(f"[AGENT] Generating re-engagement insight for user (Lvl {user_level}, missed {days_missed} days).")
        
        llm_runner = self._run_groq_and_parse_json if use_groq else self._run_ollama_and_parse_json
        
        prompt = f"""...""" # The prompt for this can be similarly structured
        reengagement_insight = llm_runner(prompt)

        if not reengagement_insight: # Fallback logic
            return {
                "dialogue": "Welcome back, Traveler. The path awaits.",
                "redemption_quest": {"title": "Re-ignite the Flame", "description": "Complete any quest.", "category": "GENERAL", "xp_value": 50}
            }
        return reengagement_insight
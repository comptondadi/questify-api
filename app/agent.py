# app/agent.py
import requests
import json
from ddgs import DDGS
from .config import settings

class QuestAgent:
    """
    The Dungeon Master for Questify. This agent uses an Ollama instance
    (either local or tunneled via ngrok) to provide contextual feedback.
    """
    def __init__(self):
        # Reads the host (e.g., http://localhost:11434 or your ngrok URL) from settings
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3" # The model you are running in Ollama

    def _run_llm_and_parse_json(self, prompt: str) -> dict | None:
        """Sends a prompt to the configured Ollama instance and robustly parses the JSON."""
        response_content = None
        try:
            print(f"[AGENT] Sending prompt to Ollama at {self.ollama_url}...")
            payload = {"model": self.model, "prompt": prompt, "stream": False, "format": "json"}
            headers = {
              "ngrok-skip-browser-warning": "true",
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            }
            response = requests.post(self.ollama_url, json=payload, headers=headers, timeout=180)
            response.raise_for_status()
            response_content = response.json().get("response")
            
            print(f"--- RAW OLLAMA RESPONSE ---\n{response_content}\n--- END RAW RESPONSE ---")
            
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_string = response_content[json_start:json_end]
                return json.loads(json_string)
            else:
                raise json.JSONDecodeError("No JSON object found in Ollama response.", response_content, 0)

        except json.JSONDecodeError as e:
            print(f"!!!!!!!! AGENT JSON PARSE ERROR (Ollama) !!!!!!!!\n{e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[AGENT ERROR] Could not communicate with Ollama: {e}")
            return None

    def _search_web(self, query: str, num_results: int = 3) -> tuple[str, list]:
        """Performs a web search and returns a formatted string and raw results."""
        print(f"[AGENT ACTION] Performing web search for: '{query}'")
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=num_results))
            if not raw_results:
                return "No relevant information found.", []
            
            formatted_string = "\n\n".join([f"Title: {res['title']}\nSnippet: {res['body']}" for res in raw_results])
            return formatted_string, raw_results
        except Exception as e:
            print(f"[AGENT ERROR] Web search failed: {e}")
            return "Web search failed.", []

    def get_completion_insight(self, quest_title: str, quest_category: str, user_level: int, recent_history: str, discipline_summary: dict) -> dict:
        """The main 'DM Loop' for quest completion, using the single Ollama runner."""
        print(f"[AGENT] Generating insight for quest: '{quest_title}'")
        
        summary_str = f"User Performance: {discipline_summary.get('completions_today', 0)} completions today, {discipline_summary.get('completions_this_week', 0)} this week. Focusing on {discipline_summary.get('favorite_category', 'N/A')}."

        reasoning_prompt = f"""
A user at Level {user_level} completed "{quest_title}" (Category: {quest_category}). Context: {summary_str}. History: {recent_history}.
Generate a specific, relevant web search query to help them improve.
Respond with JSON: {{"search_query": "string"}}
"""
        search_json = self._run_llm_and_parse_json(reasoning_prompt)
        
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
- "side_quest": An object with 'title', 'description', 'category', 'xp_value' (integer between 20-75). DO NOT include a 'resource_link'.
"""
        final_insight = self._run_llm_and_parse_json(output_prompt)

        if not final_insight:
            return {"dialogue": f"Your efforts on '{quest_title}' have been noted in the chronicles!"}

        if raw_search_results and "side_quest" in final_insight:
            first_real_link = raw_search_results[0].get('href')
            if first_real_link:
                final_insight["side_quest"]["resource_link"] = first_real_link
        
        return final_insight

    def get_reengagement_insight(self, user_level: int, days_missed: int, discipline_summary: dict) -> dict:
        """Generates a 'Redemption Quest' for an inactive user, using the single Ollama runner."""
        print(f"[AGENT] Generating re-engagement insight for user who missed {days_missed} days.")
        
        summary_str = f"User's Performance (before login): {discipline_summary.get('completions_this_week', 0)} completions this week. Focusing on {discipline_summary.get('favorite_category', 'N/A')}."

        prompt = f"""
You are the Chronicler, a Dungeon Master for Questify. A user (Lvl {user_level}) has returned after being inactive for {days_missed} days. Their past performance: {summary_str}.
Craft a welcoming but firm message to re-engage them. Propose a simple, high-value "Redemption Quest".
Your response MUST be a JSON object with "dialogue" and "redemption_quest" keys.
"redemption_quest" should be an object with 'title', 'description', 'category' ('REDEMPTION'), and 'xp_value' (50-100).
"""
        reengagement_insight = self._run_llm_and_parse_json(prompt)

        if not reengagement_insight: # Fallback logic
            return {
                "dialogue": "Welcome back, Traveler. The path awaits.",
                "redemption_quest": {"title": "Re-ignite the Flame", "description": "Complete any quest.", "category": "GENERAL", "xp_value": 50}
            }
        return reengagement_insight
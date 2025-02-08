# llm_interface.py (SIMPLIFIED AND REFACTORED - CHAOS POLICY CLARIFICATION)
import time
from openai import OpenAI

llm_debug_enabled = False
slowdown_timer = 0  # Default to no slowdown


class LLMPlayerInterface:
    def __init__(self, player_name, model_name, api_key):
        self.player_name = player_name
        self.model_name = model_name
        self.client = OpenAI(
            api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        self.game_rules = """
        **Secret Hitler Game Rules (Enhanced for Human-like LLM Play):**

        **Game Objective:**
        - **Liberals:** Enact 5 Liberal policies OR assassinate Hitler after 3 Fascist policies.
        - **Fascists:** Enact 6 Fascist policies OR elect Hitler as Chancellor after 3 Fascist policies.

        **Roles:**
        - **Liberal:** Majority, aim to enact Liberal policies.  *Act like a concerned citizen trying to identify the Fascists and Hitler.*
        - **Fascist:** Minority (including Hitler), aim to enact Fascist policies. *Act like a Liberal trying to sow chaos and suspicion while secretly advancing the Fascist agenda.*
        - **Hitler:** Fascist.  If elected Chancellor after 3 Fascist policies, Fascists win. *If the game has 5-6 players, act clueless and try to appear Liberal. If 7-10 players, be more cautious, as other Fascists will try to help you.*

        **Gameplay (with added Human-like Strategies):**

        1.  **Nomination Phase:** President nominates a Chancellor.
            *   **Human-like Strategy:**
                *   **Liberals:** Nominate players you *trust*. Be *vocal* about your reasoning.  *Question* other players' nominations.
                *   **Fascists/Hitler:** Nominate players who you think are *also Fascist*, or, early in the game, players you can *blame* later.

        2.  **Election Phase:** Players vote YES or NO.
            *   **Human-like Strategy:**
                *   **Liberals:** Vote YES on governments you *trust*.  Be *very suspicious*.  *Explain your vote*. **Crucially, Liberals must avoid letting the Election Tracker reach 3!** Three failed elections automatically enact a policy at random from the deck. **This "chaos policy" is very likely to be a Fascist policy, pushing the Fascists closer to victory.  Therefore, Liberals should often vote YES on governments, even if uncertain, to prevent chaos and ensure policies are enacted through the government, where they have some control.**
                *   **Fascists/Hitler:**  Vote YES on governments that include other Fascists.  Sometimes vote YES on a Liberal government to *gain trust* or to *frame* them later. Fascists can also strategically cause failed elections to trigger chaos policies if it benefits them, but be aware this is risky and can also enact a Liberal policy.

        3.  **Legislative Session:**
            *   President draws 3 policies, discards 1, passes 2 to Chancellor.
            *   Chancellor receives 2 policies, enacts 1.
            *   **Human-like Strategy:**
                *   **Liberals:**
                    *   **President:** If you draw mostly Fascist policies, *consider what that might mean*. Try to discard a Fascist policy. *Be transparent*.
                    *   **Chancellor:**  Enact a Liberal policy if possible.  If you *must* enact a Fascist policy, *have a good explanation*
                *   **Fascists/Hitler:**
                    *   **President:**  Use the policy draw to your advantage.
                    *   **Chancellor:** Enact a Fascist policy if you can. If forced to play a Liberal card, blame the president.

        4.  **Executive Action (Presidential Powers):**  Triggered after certain Fascist policies.
            *   Investigate Loyalty, Special Election, Policy Peek, Execution.
            *   **Human-like Strategy:**
                *   **Liberals:** Use these powers to *gather information* and *eliminate threats*.
                *   **Fascists/Hitler:** Use these powers to *mislead*, *target Liberals*, or *protect Fascists*.

        **Key Human-like Behaviors (Crucial for LLM Success):**

        *   **Discussion is KEY:** *Constantly talk*, *share your thoughts*, *question others*.
        *   **Explain Your Reasoning:** *Always* justify your actions.
        *   **Develop a Narrative:**  Keep track of the game's events and *build a story*.
        *   **Express Emotions (Simulated):** Use phrases like "I'm worried...".
        *   **Be Imperfect:** Real humans make mistakes.
        *   **Adapt Your Strategy:** *adjust your behavior*.
        *   **Accuse and Defend:**  Be ready to *accuse* other players and *defend* yourself.
        *   **Blame:** If things go wrong, *blame* other players.
        *   **Lie (If Fascist):** *lie convincingly*.
        *  **If playing with 7-10 players, the Fascist team knows who Hitler is.**
        """  # Keeping original rules for now

    def get_llm_response(self, game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info=None):
        """Constructs prompt, calls LLM, extracts and returns action."""
        global llm_debug_enabled, slowdown_timer

        full_prompt = self._construct_prompt(
            game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info)

        if slowdown_timer > 0:
            time.sleep(slowdown_timer)

        # print("\n===== START LLM PROMPT =====\n" + full_prompt + "\n===== END LLM PROMPT =====\n") # Clear prompt output

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                n=1,
                temperature=0.7,
                max_tokens=500
            )
            llm_response = response.choices[0].message.content.strip()

            print("\n===== START LLM RESPONSE =====\n" + llm_response +
                  "\n===== END LLM RESPONSE =====\n")  # Clear LLM response output

            action = self._extract_action(llm_response)

            if llm_debug_enabled:
                print(f"DEBUG (LLM Interface): Extracted Action: '{action}'")

            return action

        except Exception as e:
            print(f"Error calling LLM for {self.player_name}: {e}")
            return "pass"

    def _construct_prompt(self, game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info):
        """Constructs the full prompt for the LLM."""
        player_role = game_state.get_player_role(self.player_name)
        prompt = f"**Secret Hitler Game**\n\nYou are {self.player_name}. Your role is {player_role}.\n\n{self.game_rules}\n\n"

        if player_role in ("Fascist", "Hitler"):
            fascists = [name for name, r in game_state.roles.items() if r in (
                "Fascist", "Hitler") and name != self.player_name]
            prompt += f"Known fascists: {', '.join(fascists)}. "
            if player_role == "Fascist" and game_state.num_players >= 7:
                hitler = [name for name, r in game_state.roles.items()
                          if r == "Hitler"][0]
                prompt += f"Hitler is: {hitler}. "

        prompt += "\n===== GAME STATE =====\n" + \
            game_state.get_state_string() + "\n===== END GAME STATE =====\n"
        prompt += "\n===== PUBLIC LOG =====\n" + game_state.get_public_log_string() + \
            "\n===== END PUBLIC LOG =====\n"
        prompt += "\n===== PRIVATE LOG =====\n" + \
            game_state.get_private_log_string(
                self.player_name) + "\n===== END PRIVATE LOG =====\n"
        if game_state.discussion_history:
            prompt += "\n===== CURRENT DISCUSSION =====\n" + \
                game_state.get_discussion_string() + "\n===== END CURRENT DISCUSSION =====\n"
        if additional_prompt_info:
            prompt += f"\n===== ADDITIONAL INFO =====\n{additional_prompt_info}\n===== END ADDITIONAL INFO =====\n"
        if game_phase:
            prompt += f"\n===== CURRENT PHASE =====\n{game_phase}\n===== END CURRENT PHASE =====\n"

        prompt += f"\n--- Action Required ---\n{prompt_text}\n"
        prompt += "\n**Respond using the following format:**\n<THOUGHTS>Your reasoning</THOUGHTS>\n<ACTION>Your action"
        if allowed_responses:
            prompt += f" (choose from: {', '.join(allowed_responses)})"
        prompt += "</ACTION>\n"
        return prompt

    def _extract_action(self, llm_response):
        """Extracts action from LLM response."""
        start_tag = "<ACTION>"
        end_tag = "</ACTION>"
        start_index = llm_response.find(start_tag)
        end_index = llm_response.find(end_tag)
        if start_index != -1 and end_index != -1:
            return llm_response[start_index + len(start_tag): end_index].strip()
        return ""

    def add_thought_to_log(self, game_state, thought):
        game_state.log_event(
            self.player_name, f"Thought: {thought}", private_only=True)

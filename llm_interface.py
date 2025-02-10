import time
from openai import OpenAI
import logging
import os
import json
import random


class GameLogger:
    def __init__(self, log_to_file_enabled):
        self.log_to_file_enabled = log_to_file_enabled
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        if self.log_to_file_enabled:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)

            game_log_filepath = os.path.join(log_dir, "game.log")
            public_log_filepath = os.path.join(log_dir, "public.log")

            game_formatter = logging.Formatter(
                '%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            game_file_handler = logging.FileHandler(
                game_log_filepath, mode='w')
            game_file_handler.setFormatter(game_formatter)
            self.logger.addHandler(game_file_handler)
            self.game_file_handler = game_file_handler

            public_logger = logging.getLogger('public')
            public_logger.setLevel(logging.INFO)
            public_formatter = logging.Formatter('%(message)s')
            public_file_handler = logging.FileHandler(
                public_log_filepath, mode='w')
            public_file_handler.setFormatter(public_formatter)
            public_logger.addHandler(public_file_handler)
            self.public_log_file_handler = public_file_handler
            self.public_logger = public_logger

            self.player_loggers = {}
            self.player_file_handlers = {}

    def setup_logging(self, player_names):
        if not self.log_to_file_enabled:
            return
        if self.log_to_file_enabled and self.public_log_file_handler:
            self.public_log_file_handler.stream.truncate(0)
            self.public_log_file_handler.stream.seek(0)

        for player_name in player_names:
            player_log_filepath = os.path.join("logs", f"{player_name}.log")
            player_file_handler = logging.FileHandler(
                player_log_filepath, mode='w')
            formatter = logging.Formatter('%(message)s')
            player_file_handler.setFormatter(formatter)
            player_logger = logging.getLogger(player_name)
            player_logger.addHandler(player_file_handler)
            player_logger.setLevel(logging.INFO)
            self.player_loggers[player_name] = player_logger
            self.player_file_handlers[player_name] = player_file_handler

    def log_public_event(self, event):
        if self.log_to_file_enabled and self.public_logger:
            self.public_logger.info(event)
            self.public_log_file_handler.flush()

    def close_log_files(self):
        if self.game_file_handler:
            self.game_file_handler.close()
        if self.public_log_file_handler:
            self.public_log_file_handler.close()
        for handler in self.player_file_handlers.values():
            handler.close()

        handlers = self.logger.handlers[:]
        for handler in handlers:
            self.logger.removeHandler(handler)
        for player_logger in self.player_loggers.values():
            handlers = player_logger.handlers[:]
            for handler in handlers:
                player_logger.removeHandler(handler)

    def log_to_debug_file(self, player_name, message):
        if self.log_to_file_enabled:
            self.logger.debug(message)
            if self.game_file_handler:
                self.game_file_handler.flush()
            if player_name:
                player_logger = self.player_loggers.get(player_name)
                if player_logger:
                    player_logger.info(message)
                    player_file_handler = self.player_file_handlers.get(
                        player_name)
                    if player_file_handler:
                        player_file_handler.flush()


class LLMPlayerInterface:
    def __init__(self, player_name, model_name, api_key, game_logger, llm_debug_enabled=False, slowdown_timer=0):
        self.player_name = player_name
        self.model_name = model_name
        self.client = OpenAI(
            api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        self.game_rules = """
        **Secret Hitler Game Rules (Enhanced for Human-like LLM Play with Strategic Discussion):**

        **Game Objective:**
        - **Liberals:** Enact 5 Liberal policies OR assassinate Hitler after 3 Fascist policies.
        - **Fascists:** Enact 6 Fascist policies OR elect Hitler as Chancellor after 3 Fascist policies.

        **Roles:**
        - **Liberal:** Majority, aim to enact Liberal policies and identify/eliminate Fascists. *Act like a concerned citizen, be observant, ask questions, share your reasoning, and try to build trust with other Liberals.*
        - **Fascist:** Minority (including Hitler), aim to enact Fascist policies and deceive Liberals. *Act like a Liberal, sow confusion, deflect suspicion, strategically lie, and coordinate with other Fascists in discussions to advance the Fascist agenda.*
        - **Hitler:** Fascist.  If elected Chancellor after 3 Fascist policies, Fascists win. *If the game has 5-6 players, act clueless and try to appear Liberal. If 7-10 players, be more cautious, as other Fascists will try to help you. In discussions, carefully reveal information to Fascists while deceiving Liberals.*

        **Gameplay (with enhanced Discussion and Human-like Strategies):**

        1.  **Nomination Phase:** President nominates a Chancellor.
            *   **Human-like Strategy:**
                *   **Liberals:** Nominate players you *trust*. Be *vocal* about your reasoning.  *Question* other players' nominations during discussion.
                *   **Fascists/Hitler:** Nominate players who you think are *also Fascist*, or, early in the game, players you can *blame* later. Use discussion to gauge reactions to nominations.

        2.  **Election Phase:** Players vote YES or NO.
            *   **Human-like Strategy:**
                *   **Liberals:** Vote YES on governments you *trust*.  Be *very suspicious*.  *Explain your vote in discussions*. **Crucially, Liberals must avoid letting the Election Tracker reach 3!** Three failed elections automatically enact a policy at random from the deck. **This "chaos policy" is very likely to be a Fascist policy. Use discussion to persuade others to vote correctly.**
                *   **Fascists/Hitler:**  Vote YES on governments that include other Fascists.  Sometimes vote YES on a Liberal government to *gain trust* or to *frame* them later. Strategically cause failed elections via NO votes if beneficial, but be aware of chaos policy risk. **Use discussion to coordinate votes and mislead Liberals.**

        3.  **Legislative Session:**
            *   President draws 3 policies, discards 1, passes 2 to Chancellor.
            *   Chancellor receives 2 policies, enacts 1.
            *   **Human-like Strategy:**
                *   **Liberals:**
                    *   **President:** If you draw mostly Fascist policies, *discuss this*. Be transparent in discussion.
                    *   **Chancellor:**  Enact a Liberal policy if possible and explain why in discussion. If you *must* enact a Fascist policy, *have a very good explanation ready for discussion*.
                *   **Fascists/Hitler:**
                    *   **President:**  Use policy draw to your advantage, and be ready to lie in discussion about what you drew.
                    *   **Chancellor:** Enact a Fascist policy if you can. If forced to play a Liberal card, blame the president convincingly in discussion.

        4.  **Executive Action (Presidential Powers):**  Triggered after certain Fascist policies.
            *   Investigate Loyalty, Special Election, Policy Peek, Execution.
            *   **Human-like Strategy:**
                *   **Liberals:** Use these powers to *gather information* and *eliminate threats*. *Discuss your intentions and findings*.
                *   **Fascists/Hitler:** Use these powers to *mislead*, *target Liberals*, or *protect Fascists*. Use discussion to justify your actions and sow misinformation.

        **Discussion is Paramount:**

        *   **Engage Actively:** *Talk in every discussion phase*. Share your thoughts, observations, suspicions, and plans.
        *   **Strategic Communication:** Use discussion to achieve your objectives: Liberals to identify Fascists, Fascists to deceive and coordinate.
        *   **Information Gathering:** Ask questions, probe for inconsistencies, and pay attention to how others speak and vote.
        *   **Form Coalitions (Cautiously):**  Attempt to identify and build alliances with players you believe are on your team, using discussion to test their loyalty.
        *   **Deception and Misdirection (If Fascist):**  Use discussion to lie convincingly, blame others, create false narratives, and protect your fellow Fascists and Hitler.
        *   **Silence is a Choice:** You are not obligated to speak in every turn, but prolonged silence might be suspicious, especially for Liberals who need to be proactive. Choose silence strategically.

        **Response Format:**

        Respond with a JSON object in the following format. You MUST ALWAYS include your private thoughts and action, and OPTIONALLY include a public statement to say to the other players.

        ```json
        {
          "thoughts": "Your internal reasoning...",
          "say": "What you choose to say publicly (optional, can be empty string)",
          "action": "Your action from the list of allowed actions below"
        }
        ```

        Example of a response:

        ```json
        {
          "thoughts": "I am still unsure about Player2...",
          "say": "Player2, can you explain why you voted yes...",
          "action": "pass"
        }
        ```
        """
        self.game_logger = game_logger
        self.llm_debug_enabled = llm_debug_enabled
        self.slowdown_timer = slowdown_timer

    def get_llm_response(self, game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info=None):
        return self._llm_call_with_retry(game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info)

    def _llm_call_with_retry(self, game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info, max_retries=3, initial_delay=2):
        retry_delay = initial_delay

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                full_prompt = self._construct_prompt(
                    game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info)

                self.game_logger.log_to_debug_file(
                    self.player_name, f"\n=== NEW REQUEST ===\nPhase: {game_phase}\n")

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": full_prompt}],
                    n=1,
                    temperature=0.7,
                    max_tokens=500
                )
                llm_response = response.choices[0].message.content.strip()

                self.game_logger.log_to_debug_file(
                    self.player_name, f"\n--- LLM RESPONSE ---\n{llm_response}\n--- END RESPONSE ---")

                action = self._extract_action(
                    llm_response, allowed_responses)
                elapsed_time = time.time() - start_time
                remaining_time = max(0, self.slowdown_timer - elapsed_time)

                if remaining_time > 0:
                    time.sleep(remaining_time)

                return llm_response, action

            except Exception as e:
                is_retryable_error = False
                error_message = str(e)

                if "rate limit" in error_message.lower() or "timeout" in error_message.lower() or "APIError" in error_message:
                    is_retryable_error = True

                error_log_msg = f"Error calling LLM for {self.player_name} (attempt {attempt + 1}/{max_retries}): {e}"
                print(f"ERROR: {error_log_msg}")
                self.game_logger.log_to_debug_file(
                    self.player_name, error_log_msg)

                if attempt < max_retries - 1 and is_retryable_error:
                    jitter = random.uniform(-0.5, 0.5)
                    delay = max(0, retry_delay + jitter)
                    print(
                        f"Retryable error detected. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    retry_delay *= 2
                else:
                    print(
                        f"Max retries reached for {self.player_name}. Choosing default action.")
                    self.game_logger.log_to_debug_file(
                        self.player_name, f"LLM failed after {max_retries} attempts. Choosing default action from allowed responses.")
                    if allowed_responses:
                        default_action = allowed_responses[0]
                        self.game_logger.log_to_debug_file(
                            self.player_name, f"Default action chosen: {default_action}. Allowed actions were: {allowed_responses}")
                        default_response_msg = f"LLM failed after {max_retries} attempts. Default action '{default_action}' chosen."
                        return default_response_msg, default_action
                    else:
                        default_response_msg = f"LLM failed after {max_retries} attempts and no allowed responses to choose from. Defaulting to 'pass' action."
                        self.game_logger.log_to_debug_file(
                            self.player_name, f"LLM failed after {max_retries} attempts and no allowed responses to choose from. Defaulting to 'pass' action.")
                        return default_response_msg, "pass"

    def _construct_prompt(self, game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info):
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
        prompt += "\n**Respond with a JSON object in the following format (do not include ```json or ```):**\n"
        prompt += "```\n"
        prompt += "{\n"
        prompt += '  "thoughts": "Your internal reasoning",\n'
        prompt += '  "say": "What you choose to say publicly (optional, can be empty string)",\n'
        prompt += '  "action": "Your action from the list of allowed actions below"\n'
        prompt += "}\n"
        prompt += "```\n"
        if allowed_responses:
            prompt += "\n**Allowed Actions:**\n"
            for action in allowed_responses:
                prompt += f"- \"{action}\"\n"
            prompt += "\n**Choose ONE action from the 'Allowed Actions' list for the \"action\" field in your JSON response.  Do NOT include any other actions. Ensure your response is valid JSON and do NOT include ```json or ```.**\n"
        else:
            prompt += "\n**For discussion turns where no direct action is required, you can set the \"action\" field to \"pass\" in your JSON response.**\n"

        return prompt

    def _extract_json_field(self, llm_response, field_name):
        llm_response = llm_response.strip()
        if llm_response.startswith("```json"):
            llm_response = llm_response[len("```json"):].strip()
        if llm_response.endswith("```"):
            llm_response = llm_response[:-len("```")].strip()

        try:
            response_json = json.loads(llm_response)
            return response_json.get(field_name, None)
        except json.JSONDecodeError:
            self.game_logger.log_to_debug_file(
                self.player_name, f"WARNING: Invalid JSON response from LLM. Response: '{llm_response}'")
            return None

    def _extract_action(self, llm_response, allowed_responses):
        action_text = self._extract_json_field(llm_response, "action")
        if action_text and (not allowed_responses or action_text in allowed_responses):
            return action_text
        else:
            self.game_logger.log_to_debug_file(
                self.player_name, f"WARNING: Invalid or missing 'action' in JSON response or action not in allowed responses. Defaulting to 'pass'. Response: '{llm_response}', Allowed Actions: {allowed_responses}")
            return "pass"

    def extract_thought(self, llm_response):
        return self._extract_json_field(llm_response, "thoughts")

    def extract_public_statement(self, llm_response):
        return self._extract_json_field(llm_response, "say")

    def add_thought_to_log(self, game_state, thought):
        game_state.log_event(
            self.player_name, f"Thought: {thought}", private_only=True)

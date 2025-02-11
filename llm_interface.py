import time
from openai import OpenAI
import logging
import os
import json
import random
from prompt_strings import PromptStrings
from llm_clients import GeminiClient, OpenRouterClient


class GameLogger:
    def __init__(self, log_to_file_enabled):
        self.log_to_file_enabled = log_to_file_enabled
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.game_file_handler = None
        self.public_log_file_handler = None
        self.player_file_handlers = {}
        self.player_loggers = {}
        self.public_logger = None

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

    # Added full_prompt and raw_llm_response arguments
    def log_to_debug_file(self, player_name, message, full_prompt=None, raw_llm_response=None):
        if self.log_to_file_enabled:
            self.logger.debug(message)
            if full_prompt:  # Log full prompt if provided
                self.logger.debug(
                    f"\n--- FULL PROMPT ---\n{full_prompt}\n--- END PROMPT ---")
            if raw_llm_response:  # Log raw LLM response if provided
                self.logger.debug(
                    f"\n--- RAW LLM RESPONSE ---\n{raw_llm_response}\n--- END RAW RESPONSE ---")
            if self.game_file_handler:
                self.game_file_handler.flush()
            if player_name:
                player_logger = self.player_loggers.get(player_name)
                if player_logger:
                    player_logger.info(message)
                    # Log raw LLM response to player log as well (INFO level)
                    if raw_llm_response:
                        player_logger.info(
                            f"\n--- RAW LLM RESPONSE ---\n{raw_llm_response}\n--- END RAW RESPONSE ---")
                    player_file_handler = self.player_file_handlers.get(
                        player_name)
                    if player_file_handler:
                        player_file_handler.flush()


class LLMPlayerInterface:
    def __init__(self, player_name, model_name, api_key, game_logger, llm_debug_enabled=False, slowdown_timer=0, provider_name="gemini"):
        self.player_name = player_name
        self.model_name = model_name
        self.game_rules = PromptStrings.get_game_rules()
        self.game_logger = game_logger
        self.llm_debug_enabled = llm_debug_enabled
        self.slowdown_timer = slowdown_timer
        self.provider_name = provider_name

        if provider_name == "gemini":
            self.llm_client = GeminiClient(api_key=api_key)
        elif provider_name == "openrouter":
            self.llm_client = OpenRouterClient(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    def get_llm_response(
            self,
            game_state,
            prompt_text,
            allowed_responses,
            game_phase,
            additional_prompt_info=None):
        return self._llm_call_with_retry(
            game_state,
            prompt_text,
            allowed_responses,
            game_phase,
            additional_prompt_info
        )

    def _llm_call_with_retry(
            self,
            game_state,
            prompt_text,
            allowed_responses,
            game_phase,
            additional_prompt_info,
            max_retries=3,
            initial_delay=2):
        retry_delay = initial_delay

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                full_prompt = self._construct_prompt(
                    game_state, prompt_text, allowed_responses, game_phase, additional_prompt_info)

                self.game_logger.log_to_debug_file(
                    self.player_name,
                    f"\n=== NEW REQUEST ===\n"
                    f"Provider: {self.provider_name}, Model: {self.model_name}\n"
                    f"Phase: {game_phase}\n"
                )

                response = self.llm_client.chat_completion(
                    model_name=self.model_name,
                    messages=[{"role": "user", "content": full_prompt}],
                    n=1,
                    temperature=0.7,
                    # max_tokens=500
                )
                llm_response = response.choices[0].message.content.strip()

                if not llm_response:  # Check if llm_response is empty or just whitespace
                    error_log_msg = (
                        f"WARNING: LLM returned an empty response for {self.player_name} "
                        f"(attempt {attempt + 1}/{max_retries}). "
                        f"Provider: {self.provider_name}, Model: {self.model_name}"
                    )
                    print(f"WARNING: {error_log_msg}")
                    self.game_logger.log_to_debug_file(
                        self.player_name, error_log_msg)

                    if attempt < max_retries - 1:  # Retry if possible
                        jitter = random.uniform(-0.5, 0.5)
                        delay = max(0, retry_delay + jitter)
                        print(
                            f"Empty response detected. Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        retry_delay *= 2
                        continue  # Go to the next retry attempt
                    else:  # Max retries reached for empty response
                        print(
                            f"Max retries reached for {self.player_name} after empty responses. Choosing default action.")
                        self.game_logger.log_to_debug_file(
                            self.player_name,
                            f"LLM failed after {max_retries} attempts due to empty responses. "
                            f"Choosing default action from allowed responses.")
                        if allowed_responses:
                            default_action = allowed_responses[0]
                            default_response_msg = (
                                f"LLM failed after {max_retries} attempts. "
                                f"Default action '{default_action}' chosen."
                            )
                            return default_response_msg, default_action
                        else:
                            default_response_msg = f"LLM failed after {max_retries} attempts and no allowed responses to choose from. Defaulting to 'pass' action."
                            return default_response_msg, "pass"

                self.game_logger.log_to_debug_file(
                    self.player_name,
                    f"\n--- LLM RESPONSE ---\n"
                    f"{llm_response}\n"
                    f"--- END RESPONSE ---"
                )

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

                error_msg = error_message.lower()
                if ("rate limit" in error_msg or
                        "timeout" in error_msg or
                        "APIError" in error_message):
                    is_retryable_error = True

                error_log_msg = (
                    f"Error calling LLM for {self.player_name} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                    f"Provider: {self.provider_name}, Model: {self.model_name}, Error: {e}"
                )
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
                        self.player_name,
                        f"LLM failed after {max_retries} attempts. "
                        f"Choosing default action from allowed responses.")
                    if allowed_responses:
                        default_action = allowed_responses[0]
                        self.game_logger.log_to_debug_file(
                            self.player_name,
                            f"Default action chosen: {default_action}. "
                            f"Allowed actions were: {allowed_responses}"
                        )
                        default_response_msg = (
                            f"LLM failed after {max_retries} attempts. "
                            f"Default action '{default_action}' chosen."
                        )
                        return default_response_msg, default_action
                    else:
                        default_response_msg = f"LLM failed after {max_retries} attempts and no allowed responses to choose from. Defaulting to 'pass' action."
                        self.game_logger.log_to_debug_file(
                            self.player_name, f"LLM failed after {max_retries} attempts and no allowed responses to choose from. Defaulting to 'pass' action.")
                        return default_response_msg, "pass"

    def _construct_prompt(
            self,
            game_state,
            prompt_text,
            allowed_responses,
            game_phase,
            additional_prompt_info):
        player_role = game_state.get_player_role(self.player_name)
        prompt = PromptStrings.get_game_title_prefix() + \
            PromptStrings.get_you_are_prefix() + self.player_name + \
            PromptStrings.get_your_role_prefix() + str(player_role) + ".\n\n" + \
            PromptStrings.get_game_rules() + "\n\n"

        if player_role in ("Fascist", "Hitler"):
            fascists = [name for name, r in game_state.roles.items() if r in (
                "Fascist", "Hitler") and name != self.player_name]
            prompt += PromptStrings.get_known_fascists_prefix() + ', '.join(fascists) + ". "
            if player_role == "Fascist" and game_state.num_players >= 7:
                hitler = [name for name, r in game_state.roles.items()
                          if r == "Hitler"][0]
                prompt += PromptStrings.get_hitler_is_prefix() + hitler + ". "

        prompt += PromptStrings.get_game_state_section_prefix() + \
            game_state.get_state_string() + \
            PromptStrings.get_game_state_section_suffix()
        prompt += PromptStrings.get_private_log_section_prefix() + \
            game_state.get_private_log_string(self.player_name) + \
            PromptStrings.get_private_log_section_suffix()
        if game_state.discussion_history:
            prompt += PromptStrings.get_discussion_history_section_prefix() + \
                game_state.get_discussion_string() + \
                PromptStrings.get_discussion_history_section_suffix()
        if additional_prompt_info:
            prompt += PromptStrings.get_additional_info_section_prefix() + \
                additional_prompt_info + \
                PromptStrings.get_additional_info_section_suffix()
        if game_phase:
            prompt += PromptStrings.get_current_phase_section_prefix() + \
                game_phase + \
                PromptStrings.get_current_phase_section_suffix()

        prompt += PromptStrings.get_action_required_prefix() + prompt_text + "\n"
        prompt += PromptStrings.get_response_format_instructions_prefix()
        prompt += PromptStrings.get_json_block()

        if allowed_responses:
            prompt += PromptStrings.get_allowed_actions_prefix()
            for action in allowed_responses:
                prompt += PromptStrings.get_action_list_item_prefix() + action + \
                    PromptStrings.get_action_list_item_suffix()
            prompt += PromptStrings.get_allowed_actions_suffix()
        else:
            prompt += PromptStrings.get_no_action_required_instruction()

        return prompt

    def _extract_json_substring(self, text):
        start_index = text.find('{')
        end_index = text.rfind('}')  # rfind to get the *last* occurrence

        if start_index != -1 and end_index != -1 and start_index < end_index:
            json_substring = text[start_index:end_index + 1]
            return json_substring
        return None  # Or raise an exception if you prefer

    def _extract_json_field(self, llm_response, field_name):
        llm_response = llm_response.strip()  # Aggressively trim whitespace FIRST

        json_payload = None
        extracted_json_substring = None  # Initialize for logging

        try:
            # Attempt 1: Extract JSON-like substring using curly braces
            extracted_json_substring = self._extract_json_substring(
                llm_response)
            if extracted_json_substring:
                try:
                    json_payload = json.loads(extracted_json_substring)
                    self.game_logger.log_to_debug_file(
                        self.player_name, f"DEBUG: Successfully parsed JSON after curly brace extraction. Extracted JSON: '{extracted_json_substring}'")
                except json.JSONDecodeError as e_sub_parse:
                    self.game_logger.log_to_debug_file(
                        self.player_name, f"WARNING: JSONDecodeError after curly brace extraction: {e_sub_parse}. Extracted JSON: '{extracted_json_substring}', Original Response: '{llm_response}'")
                    json_payload = None  # Parsing failed even after extraction

            if not json_payload:  # If extraction failed or parsing of extracted JSON failed, try original response
                # Attempt 2: Parse original response as pure JSON (no extraction)
                try:
                    json_payload = json.loads(llm_response)
                    self.game_logger.log_to_debug_file(
                        self.player_name, f"DEBUG: Successfully parsed JSON directly (no extraction needed). Response: '{llm_response}'")
                except json.JSONDecodeError as e_pure_parse:
                    self.game_logger.log_to_debug_file(
                        self.player_name, f"WARNING: JSONDecodeError (pure JSON parse failed): {e_pure_parse}. Response: '{llm_response}'")
                    json_payload = None  # Pure JSON parsing failed

            if json_payload:  # If JSON parsing was successful (either way)
                return json_payload.get(field_name, None)
            else:  # If both parsing attempts failed
                self.game_logger.log_to_debug_file(
                    self.player_name, f"WARNING: Failed to parse JSON even after extraction attempts. Response: '{llm_response}'")
                return None

        except Exception as general_e:  # Catch any other unexpected errors during parsing
            self.game_logger.log_to_debug_file(
                self.player_name, f"WARNING: General error during JSON processing: {general_e}. Response: '{llm_response}'")
            return None

    def _extract_action(self, llm_response, allowed_responses):
        action_text = self._extract_json_field(llm_response, "action")
        if action_text and (not allowed_responses or action_text in allowed_responses):
            return action_text
        else:
            self.game_logger.log_to_debug_file(
                self.player_name,
                (f"WARNING: Invalid or missing 'action' in JSON response "
                 f"or action not in allowed responses. "
                 f"Defaulting to 'pass'. "
                 f"Response: '{llm_response}', "
                 f"Allowed Actions: {allowed_responses}")
            )
            return "pass"

    def extract_thought(self, llm_response):
        return self._extract_json_field(llm_response, "thoughts")

    def extract_public_statement(self, llm_response):
        return self._extract_json_field(llm_response, "say")

    def add_thought_to_log(self, game_state, thought):
        game_state.log_event(
            self.player_name, f"Thought: {thought}", private_only=True)

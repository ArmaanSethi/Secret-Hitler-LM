# secret_hitler_game.py (REFACTORED - Using Classes, No Globals)
import argparse
import os
import sys
import time

from secret_hitler_engine import GameState, is_valid_chancellor_nominee, LIBERAL, FASCIST, ALIVE, DEAD
from llm_interface import LLMPlayerInterface, GameLogger


class GameConfig:
    def __init__(self, args):
        self.num_players = args.num_players
        self.slowdown_timer = args.slowdown
        self.press_enter_mode = args.press_enter
        self.debug_llm_enabled = args.debug_llm
        self.log_to_file_enabled = args.log_to_file
        self.player_models = self._parse_player_models(args.player_models, args.num_players)

    def _parse_player_models(self, player_models_arg, num_players):
        player_models = {}
        if player_models_arg:
            for player_config in player_models_arg:
                name, model = player_config.split("=", 1)
                player_models[name] = model
        else:
            for i in range(num_players):
                player_models[f"Player{i+1}"] = "gemini-2.0-flash" # Default model
        return player_models


class GameRunner:
    def __init__(self, config):
        self.config = config
        self.logger = GameLogger(config.log_to_file_enabled)
        self.player_llm_configs = self._setup_llm_interfaces()
        self.game_state = None

    def _setup_llm_interfaces(self):
        player_llm_configs = {}
        default_api_key = os.environ.get("GEMINI_API_KEY")
        if not default_api_key:
            sys.exit("No API Key found.")

        for player_name, model_name in self.config.player_models.items():
            player_llm_configs[player_name] = LLMPlayerInterface(
                player_name, model_name, default_api_key, self.logger, self.config.debug_llm_enabled, self.config.slowdown_timer)
        return player_llm_configs

    def setup_game(self):
        player_names = list(self.player_llm_configs.keys())
        if len(player_names) != self.config.num_players:
            raise ValueError(
                f"Player config mismatch: {len(player_names)} vs {self.config.num_players}")
        self.game_state = GameState(player_names, self.logger) # Pass GameLogger to GameState

        self.game_state.log_event(None, "Roles assigned.")
        for player in player_names:
            role = self.game_state.get_player_role(player)
            private_info = {player: f"Your role is: {role}"}
            if role in (FASCIST, "Hitler"):
                fascists = [name for name, r in self.game_state.roles.items()
                            if r in (FASCIST, "Hitler")]
                private_info[player] += f"\nFascists: {', '.join(fascists)}"
                if role == FASCIST and self.config.num_players >= 7:
                    hitler = [name for name, r in self.game_state.roles.items()
                              if r == "Hitler"][0]
                    private_info[player] += f"\nHitler: {hitler}"
            self.game_state.log_event(None, "Roles assigned.",
                                 private_info=private_info)
        if self.config.log_to_file_enabled:
            self.logger.setup_logging(self.game_state.get_player_names()) # Use GameLogger to setup logging


    def display_state_terminal(self,  message: str | None = None, error_message: str | None = None, debug_message: str | None = None, current_player_name: str | None = None):
        """Displays the current game state in the terminal."""
        if error_message:
            print(f"ERROR: {error_message}")
        if debug_message and self.config.debug_llm_enabled:
            print(f"DEBUG: {debug_message}")
        if message:
            print(message)

        if self.game_state is None:
            return

        print("\n======== Game State ========")
        print(f"Liberal Policies: {self.game_state.lib_policies}")
        print(f"Fascist Policies: {self.game_state.fasc_policies}")
        print(f"Election Tracker: {self.game_state.election_tracker}")
        print(f"President: {self.game_state.gov['president'] or 'None'}")
        print(f"Chancellor: {self.game_state.gov['chancellor'] or 'None'}")
        print(f"Veto Power: {'Yes' if self.game_state.veto_power else 'No'}")

        print("\n===== PUBLIC LOG =====")
        for event in self.game_state.public_log:
            print(f"- {event}")
        if self.game_state.discussion_history:
            print("\n===== DISCUSSION =====")
            for msg in self.game_state.discussion_history:
                print(f"- {msg}")
        if current_player_name:
            print(f"\n=== {current_player_name}'s Private Log ===")
            for event in self.game_state.private_logs[current_player_name]:
                print(f"- {event}")

        print("\n===== END STATE =====")


    def get_player_input(self, prompt, allowed_responses, current_player, game_phase, llm_interface, additional_prompt_info=None):
        """Gets player input from LLM and handles terminal output."""

        llm_response_full, llm_response_action = llm_interface.get_llm_response(
            self.game_state, prompt, allowed_responses, game_phase, additional_prompt_info
        )

        self.game_state.log_event(current_player, f"Action: {llm_response_action}",
                             private_info={current_player: f"Full response:\n{llm_response_full}"})

        self.display_state_terminal(
            message=f"\n===== TURN: {current_player} ({self.game_state.get_player_role(current_player)}) - PHASE: {game_phase} =====", current_player_name=current_player)

        if self.config.slowdown_timer <= 0 and not self.config.press_enter_mode: # Timer or press enter
            pass # No automatic pause, rely on timer in LLM interface
        elif self.config.press_enter_mode:
             input("\nPress Enter to Continue...")
        elif self.config.slowdown_timer > 0:
            time.sleep(self.config.slowdown_timer) # Fallback timer here, but ideally handled in LLM interface

        return llm_response_action


    def election_phase(self):
        """Runs election phase."""
        president_name = self.game_state.get_president()
        llm_interface_president = self.player_llm_configs[president_name]

        valid_nominees = [name for name in self.game_state.get_player_names(
        ) if is_valid_chancellor_nominee(self.game_state, president_name, name)]

        while True:
            nominee_prompt = f"{president_name}, nominate Chancellor from: {', '.join(valid_nominees)}"
            nominee_name = self.get_player_input(
                nominee_prompt, valid_nominees, president_name, "Nomination", llm_interface_president)

            if nominee_name in valid_nominees:
                break
            self.display_state_terminal(
                error_message=f"Invalid nominee: {nominee_name}. Please choose from: {', '.join(valid_nominees)}")

        self.game_state.set_government(president_name, nominee_name)
        self.game_state.log_event(
            None, f"{president_name} nominated {nominee_name} Chancellor.")
        self.display_state_terminal(
            message=f"\n{president_name} nominated {nominee_name} Chancellor.")

        self.discussion_phase("Election")
        votes = self.voting_phase()
        yes_votes = list(votes.values()).count("YES")
        vote_results_msg = f"Vote Results: Yes={yes_votes}, No={len(votes) - yes_votes}"
        self.display_state_terminal(message=f"\n{vote_results_msg}")
        self.game_state.log_event(None, vote_results_msg)
        return yes_votes > len(votes) / 2


    def discussion_phase(self, phase_name):
        """Runs discussion phase."""
        self.display_state_terminal(
            message=f"\n--- {phase_name} Discussion ---")
        self.game_state.start_discussion(phase_name)

        players_passed = set()
        discussion_rounds = 0
        max_rounds = 3

        while discussion_rounds < max_rounds:
            current_speaker = self.game_state.get_current_discussion_speaker()
            if not current_speaker or current_speaker in players_passed:
                self.game_state.next_discussion_speaker()
                if not self.game_state.get_current_discussion_speaker():
                    break
                continue

            llm_interface = self.player_llm_configs[current_speaker]
            prompt = f"{current_speaker}, Discuss {phase_name}. (You can say 'pass')"
            message = self.get_player_input(prompt, [
                                       "pass"], current_speaker, f"{phase_name} Discussion", llm_interface)

            if message.lower() == "pass":
                self.game_state.log_event(current_speaker, "passed discussion turn.")
                players_passed.add(current_speaker)
                self.display_state_terminal(
                    message=f"{current_speaker} passes.")
            else:
                self.game_state.record_discussion_message(
                    current_speaker, message)

            self.game_state.next_discussion_speaker()
            if len(players_passed) < len([p for p in self.game_state.get_player_names() if self.game_state.player_status[p] == ALIVE]):
                self.display_state_terminal()

            if len(players_passed) == len([p for p in self.game_state.get_player_names() if self.game_state.player_status[p] == ALIVE]):
                self.display_state_terminal(
                    message="All players passed discussion.")
                break
            if self.game_state.get_current_discussion_speaker() == self.game_state.get_first_discussion_speaker():
                discussion_rounds += 1
        self.display_state_terminal(
            message=f"--- {phase_name} Discussion End ---")


    def voting_phase(self):
        """Runs voting phase."""
        self.display_state_terminal(message="\n--- Voting Phase ---")
        votes = {}
        for player in self.game_state.get_player_names():
            if self.game_state.player_status[player] == ALIVE:
                vote_prompt = f"{player}, vote YES/NO on government."
                llm_interface_voter = self.player_llm_configs[player]
                vote = self.get_player_input(vote_prompt, [
                                        "YES", "NO"], player, "Voting", llm_interface_voter).upper()
                votes[player] = vote
                self.game_state.log_event(player, f"Voted {vote}.", private_info={
                                     player: f"You voted {vote}"})
                self.display_state_terminal(message=f"{player} voted.")
        return votes


    def legislative_session(self):
        """Runs legislative session."""
        president_name = self.game_state.get_president()
        chancellor_name = self.game_state.gov["chancellor"]
        llm_interface_president = self.player_llm_configs[president_name]
        llm_interface_chancellor = self.player_llm_configs[chancellor_name]

        policies = self.game_state.draw_policies(3)
        if not policies:
            return None
        self.game_state.log_event(president_name, f"Drew policies: {policies}", private_info={
                             president_name: f"Drew policies: {policies}"})

        discard_prompt = f"{president_name}, discard one policy (1, 2, 3): {policies}"
        while True:
            discard_choice = self.get_player_input(discard_prompt, [str(i+1) for i in range(
                3)], president_name, "President Discard", llm_interface_president, additional_prompt_info=str(policies))
            try:
                discard_index = int(discard_choice) - 1
                if 0 <= discard_index < len(policies):
                    break
            except ValueError:
                self.display_state_terminal(
                    error_message=f"Invalid choice from President: {discard_choice}. Retrying...")
                continue

        discarded_policy = policies.pop(discard_index)
        self.game_state.discard_policy(discarded_policy)
        self.game_state.log_event(None, f"{president_name} discarded a policy.")
        self.display_state_terminal(
            message=f"\n{president_name} discarded a policy.")

        enact_prompt = f"{chancellor_name}, enact one policy (1, 2): {policies}"
        while True:
            enact_choice = self.get_player_input(enact_prompt, [str(i+1) for i in range(2)], chancellor_name,
                                            "Chancellor Enact", llm_interface_chancellor, additional_prompt_info=str(policies))
            try:
                enact_index = int(enact_choice) - 1
                if 0 <= enact_index < len(policies):
                    break
            except ValueError:
                self.display_state_terminal(
                    error_message=f"Invalid choice from Chancellor: {enact_choice}. Retrying...")
                continue

        enacted_policy = policies.pop(enact_index)
        self.game_state.enact_policy(enacted_policy)
        self.game_state.log_event(
            None, f"{chancellor_name} enacted a {enacted_policy} policy.")
        self.display_state_terminal(
            message=f"\n{chancellor_name} enacted a {enacted_policy} policy.")
        return enacted_policy


    def executive_action(self):
        """Runs executive action based on fascist policies enacted."""
        president_name = self.game_state.get_president()
        llm_interface_president = self.player_llm_configs[president_name]

        power_used = None
        if self.game_state.fasc_policies == 3 and self.config.num_players >= 5:
            power_used = "Investigate"
            action_func = self.game_state.investigate_player
            prompt_text = f"{president_name}, investigate player:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and name not in self.game_state.investigated and self.game_state.player_status[name] == ALIVE]
        elif self.game_state.fasc_policies == 4 and self.config.num_players >= 7:
            power_used = "Special Election"
            action_func = self.game_state.call_special_election
            prompt_text = f"{president_name}, choose next president:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and self.game_state.player_status[name] == ALIVE]
        elif self.game_state.fasc_policies == 5 and self.config.num_players >= 9:
            power_used = "Policy Peek"
            action_func = self.game_state.policy_peek
            prompt_text = f"{president_name} uses Policy Peek."
            allowed_targets = None
        elif self.game_state.fasc_policies >= 4 and (self.config.num_players == 5 or self.config.num_players == 6 or self.config.num_players >= 9):
            power_used = "Execution"
            action_func = self.game_state.kill_player
            prompt_text = f"{president_name}, execute player:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and self.game_state.player_status[name] == ALIVE]
        else:
            self.display_state_terminal(message="No executive action.")
            return

        self.display_state_terminal(
            message=f"\n--- Executive Action: {power_used} ---")

        if power_used == "Policy Peek":
            self.game_state.policy_peek(president_name)
            self.game_state.log_event(None, f"{president_name} used Policy Peek.")
            self.display_state_terminal(
                message=f"{president_name} used Policy Peek.")
        elif allowed_targets:
            target_player = self.get_player_input(prompt_text, allowed_targets, president_name,
                                             f"Executive Action: {power_used}", llm_interface_president)
            if action_func == self.game_state.investigate_player:
                membership = self.game_state.investigate_player(
                    president_name, target_player)
                investigate_result_msg = f"{president_name} investigated {target_player}. Result: {membership}"
                self.display_state_terminal(
                    message=f"\n{investigate_result_msg}")
                self.game_state.log_event(None, investigate_result_msg)
                self.display_state_terminal(
                    message=f"\n{president_name} investigated {target_player}. Result: {membership}")
            elif action_func == self.game_state.call_special_election:
                self.game_state.call_special_election(president_name, target_player)
                special_election_msg = f"{president_name} called special election for {target_player}."
                self.display_state_terminal(
                    message=f"\n{special_election_msg}")
                self.game_state.log_event(None, special_election_msg)
                self.display_state_terminal(
                    message=f"\n{president_name} called special election for {target_player}.")
            elif action_func == self.game_state.kill_player:
                self.game_state.kill_player(target_player)
                execution_msg = f"{president_name} executed {target_player}."
                self.display_state_terminal(message=f"\n{execution_msg}")
                self.game_state.log_event(None, execution_msg)
                self.display_state_terminal(
                    message=f"\n{president_name} executed {target_player}.")

        self.display_state_terminal(
            message=f"--- Executive Action: {power_used} Completed ---")


    def game_over_screen(self):
        """Displays game over screen."""
        self.display_state_terminal(message="\n======== GAME OVER ========")
        self.display_state_terminal(message=f"Winner: {self.game_state.winner}!")
        self.display_state_terminal(message="\n--- Roles ---")
        for name, role in self.game_state.roles.items():
            self.display_state_terminal(message=f"{name}: {role}")
        self.display_state_terminal(message="\n--- Public Log ---")
        for event in self.game_state.public_log:
            self.display_state_terminal(message=f"- {event}")
        if self.config.log_to_file_enabled:
            self.logger.close_log_files() # Use GameLogger to close files


    def run_game(self):
        """Plays Secret Hitler game with LLMs."""
        self.setup_game()

        while not self.game_state.game_over:
            president_name = self.game_state.get_president()
            gov_approved = self.election_phase()

            if gov_approved:
                self.game_state.election_tracker = 0
                if self.game_state.check_hitler_chancellor_win():
                    win_msg = "\nFascists win: Hitler Chancellor after 3 Fascist policies!"
                    self.display_state_terminal(message=win_msg)
                    self.game_state.log_event(None, win_msg)
                    self.game_state.game_over = True
                    self.game_state.winner = "Fascists"
                    break
                enacted_policy = self.legislative_session()
                if enacted_policy:
                    self.executive_action()
            else:
                self.game_state.reset_government()
                self.game_state.increment_election_tracker()
                if self.game_state.election_tracker >= 3:
                    chaos_msg = "\nElection tracker maxed! Chaos policy enacted."
                    self.display_state_terminal(message=chaos_msg)
                    self.game_state.log_event(None, chaos_msg)
                    self.game_state.enact_chaos_policy()
                    self.game_state.election_tracker = 0
                    if self.game_state.game_over:
                        break

            if not self.game_state.game_over:
                self.game_state.next_president()
                self.display_state_terminal(message="\n--- Next Round ---")

        self.game_over_screen()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Play Secret Hitler with LLM players.")
    parser.add_argument("num_players", type=int,
                        help="Number of players (5-10)")
    parser.add_argument("--slowdown", type=int, default=0,
                        help="Slowdown timer in seconds (0 for no slowdown)")
    parser.add_argument("--press_enter", action="store_true",
                        help="Press enter to continue instead of timer")
    parser.add_argument("--debug_llm", action="store_true",
                        help="Enable LLM debug output")
    parser.add_argument("--log_to_file", action="store_true",
                        help="Enable logging detailed output to files in 'logs/' directory")
    parser.add_argument("--player_models", nargs="+",
                        help="PlayerName=ModelName (e.g., PlayerName=ModelName Player2=gpt-4)")
    args = parser.parse_args()

    if not 5 <= args.num_players <= 10:
        sys.exit("Players must be 5-10")
    if args.slowdown < 0:
        sys.exit("Slowdown must be non-negative")

    game_config = GameConfig(args) # Create GameConfig instance
    game_runner = GameRunner(game_config) # Create GameRunner instance

    start_game_msg = "Running Secret Hitler LLM Game."
    if game_config.slowdown_timer > 0:
        start_game_msg += f" Slowdown timer: {game_config.slowdown_timer} seconds."
    elif game_config.press_enter_mode:
        start_game_msg += " Press Enter to continue after each turn."
    if game_config.debug_llm_enabled:
        start_game_msg += " LLM debug output enabled."
    if game_config.log_to_file_enabled:
        start_game_msg += " File logging enabled (logs/ directory)."
    game_runner.display_state_terminal(message=start_game_msg)

    game_runner.run_game() # Run the game using GameRunner
import argparse
import os
import sys
import time

from secret_hitler_engine import GameState, is_valid_chancellor_nominee, Role, PlayerStatus
from llm_interface import LLMPlayerInterface, GameLogger


NOMINATE_ACTION_PREFIX = "nominate "
DISCARD_ACTION_PREFIX = "discard "
ENACT_ACTION_PREFIX = "enact "
VOTE_YES = "YES"
VOTE_NO = "NO"
INVESTIGATE_ACTION = "investigate "
EXECUTE_ACTION = "execute "
PASS_ACTION = "pass"


class GameConfig:
    def __init__(self, config_args):
        self.num_players = config_args.num_players
        self.slowdown_timer = config_args.slowdown
        self.press_enter_mode = config_args.press_enter
        self.debug_llm_enabled = config_args.debug_llm
        self.log_to_file_enabled = config_args.log_to_file
        self.player_models = self._parse_player_models(
            config_args.player_models, config_args.num_players)

    def _parse_player_models(self, player_models_arg, num_players):
        player_models = {}
        if player_models_arg:
            for player_config in player_models_arg:
                name, model = player_config.split("=", 1)
                player_models[name] = model
        else:
            for i in range(num_players):
                player_models[f"Player{i+1}"] = "gemini-2.0-flash"
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
        self.game_state = GameState(player_names, self.logger)

        if self.config.log_to_file_enabled:
            self.logger.setup_logging(self.game_state.get_player_names())
            roles_log_entry = "--- ROLES ---"
            self.logger.log_public_event(roles_log_entry)
            for name, role in self.game_state.roles.items():
                role_msg = f"{name}: {role}"
                self.logger.log_public_event(role_msg)

        for player in player_names:
            role = self.game_state.get_player_role(player)
            private_info = {player: f"Your role is: {role}"}
            if role in (Role.FASCIST, Role.HITLER):
                fascists = [name for name, r in self.game_state.roles.items()
                            if r in (Role.FASCIST, Role.HITLER)]
                private_info[player] += f"\nFascists: {', '.join(fascists)}"
                if role == Role.FASCIST and self.config.num_players >= 7:
                    hitler = [name for name, r in self.game_state.roles.items()
                              if r == Role.HITLER][0]
                    private_info[player] += f"\nHitler: {hitler}"
            self.game_state.log_event(None, "Roles assigned.",
                                      private_info=private_info)

    def display_state_terminal(self,  message: str | None = None, error_message: str | None = None, debug_message: str | None = None, current_player_name: str | None = None):
        if error_message:
            print(f"ERROR: {error_message}")
        if debug_message and self.config.debug_llm_enabled:
            print(f"DEBUG: {debug_message}")
        if message:
            print(message)

        if self.game_state is None:
            return

        self._display_game_status()
        self._display_public_log()
        if self.game_state.discussion_history:
            self._display_discussion_log()
        if current_player_name:
            self._display_private_log(current_player_name, current_player_name)

        print("\n===== END STATE =====")

    def _display_game_status(self):
        print("\n======== Game State ========")
        print(f"Liberal Policies: {self.game_state.lib_policies}")
        print(f"Fascist Policies: {self.game_state.fasc_policies}")
        print(f"Election Tracker: {self.game_state.election_tracker}")
        print(f"President: {self.game_state.gov.president or 'None'}")
        print(f"Chancellor: {self.game_state.gov.chancellor or 'None'}")
        print(f"Veto Power: {'Yes' if self.game_state.veto_power else 'No'}")

    def _display_public_log(self):
        print("\n===== PUBLIC LOG =====")
        for event in self.game_state.public_log:
            print(f"- {event}")

    def _display_discussion_log(self):
        print("\n===== DISCUSSION =====")
        for msg in self.game_state.discussion_history:
            print(f"- {msg}")

    def _display_private_log(self, player_name, current_player_name):
        print(f"\n=== {player_name}'s Private Log ===")
        for event in self.game_state.private_logs[current_player_name]:
            print(f"- {event}")

    def get_player_input(self, prompt, allowed_responses, current_player, game_phase, llm_interface, additional_prompt_info=None):
        self.game_state.game_logger.log_to_debug_file(
            current_player, f"DEBUG: get_player_input CALLED - Phase: {game_phase}, Allowed Responses: {allowed_responses}, Player: {current_player}")
        llm_response_full, llm_response_action = llm_interface.get_llm_response(
            self.game_state, prompt, allowed_responses, game_phase, additional_prompt_info
        )

        thought = llm_interface.extract_thought(llm_response_full)
        if thought:
            llm_interface.add_thought_to_log(self.game_state, thought)

        public_statement = llm_interface.extract_public_statement(
            llm_response_full)

        if public_statement:
            log_message = f"{current_player} says: {public_statement}"
            self.game_state.record_discussion_message(
                current_player, public_statement)
        else:
            log_message = f"{current_player} remains silent."

        private_info_log = {
            current_player: f"Full response:\n{llm_response_full}"}
        self.game_state.log_event(
            current_player, log_message, private_info=private_info_log)

        self.display_state_terminal(
            message=f"\n===== TURN: {current_player} ({self.game_state.get_player_role(current_player)}) - PHASE: {game_phase} =====", current_player_name=current_player)

        if self.config.slowdown_timer <= 0 and not self.config.press_enter_mode:
            pass
        elif self.config.press_enter_mode:
            input("\nPress Enter to Continue...")
        elif self.config.slowdown_timer > 0:
            time.sleep(self.config.slowdown_timer)

        return llm_response_action

    def election_phase(self):
        president_name = self.game_state.get_president()
        llm_interface_president = self.player_llm_configs[president_name]

        nominee_name = self._nomination_phase(
            president_name, llm_interface_president)
        if not nominee_name:
            return False

        self.discussion_phase("Election")
        votes = self.voting_phase()
        election_successful = self._process_election_results(
            president_name, nominee_name, votes)
        return election_successful

    def _nomination_phase(self, president_name, llm_interface_president):
        valid_nominees = [name for name in self.game_state.get_player_names(
        ) if is_valid_chancellor_nominee(self.game_state, president_name, name)]
        allowed_nominees_actions = [
            f"{NOMINATE_ACTION_PREFIX}{nominee}" for nominee in valid_nominees] + [PASS_ACTION]

        while True:
            nominee_prompt = f"{president_name}, nominate Chancellor from: {', '.join(valid_nominees)}"
            nominee_action = self.get_player_input(
                nominee_prompt, allowed_nominees_actions, president_name, "Nomination", llm_interface_president)

            if nominee_action.startswith(NOMINATE_ACTION_PREFIX):
                nominee_name = nominee_action[len(NOMINATE_ACTION_PREFIX):]
                if nominee_name in valid_nominees:
                    self.game_state.set_government(
                        president_name, nominee_name)
                    self.display_state_terminal(
                        message=f"\n{president_name} nominated {nominee_name} Chancellor.")
                    return nominee_name
            elif nominee_action == PASS_ACTION:
                self.game_state.reset_government()
                self.display_state_terminal(
                    message=f"\nPresident {president_name} passed on nomination.")
                return None
            self.display_state_terminal(
                error_message=f"Invalid nominee action: {nominee_action}. Please choose from: {', '.join(allowed_nominees_actions)}")

    def _process_election_results(self, president_name, nominee_name, votes):
        yes_votes = list(votes.values()).count(VOTE_YES)
        vote_results_msg = f"Vote Results: Yes={yes_votes}, No={len(votes) - yes_votes}"
        self.display_state_terminal(message=f"\n{vote_results_msg}")
        election_result = "Government approved" if yes_votes > len(
            votes) / 2 else "Government failed"
        full_election_log_msg = f"{president_name} nominated {nominee_name} as Chancellor. {vote_results_msg}. Election outcome: {election_result}."
        self.game_state.log_event(None, full_election_log_msg)
        return yes_votes > len(votes) / 2

    def discussion_phase(self, phase_name):
        self.display_state_terminal(
            message=f"\n--- {phase_name} Discussion ---")
        self.game_state.start_discussion(phase_name)

        players_spoken_in_round = set()
        discussion_rounds = 0
        max_rounds = 10
        last_round_someone_spoke = True

        while discussion_rounds < max_rounds and last_round_someone_spoke:
            last_round_someone_spoke = False
            players_spoken_in_round = set()

            for _ in self.game_state.get_player_names():
                current_speaker = self.game_state.get_current_discussion_speaker()
                if not current_speaker or self.game_state.player_status[current_speaker] == PlayerStatus.DEAD:
                    self.game_state.next_discussion_speaker()
                    continue

                llm_interface = self.player_llm_configs[current_speaker]
                prompt = f"{current_speaker}, Discuss {phase_name}."
                public_statement = self.get_player_input(
                    prompt, [PASS_ACTION], current_speaker, f"{phase_name} Discussion", llm_interface)

                if public_statement != PASS_ACTION:
                    last_round_someone_spoke = True
                    players_spoken_in_round.add(current_speaker)
                    self.display_state_terminal(
                        message=f"{current_speaker} says: {public_statement}")
                else:
                    self.display_state_terminal(
                        message=f"{current_speaker} remains silent.")

                self.game_state.next_discussion_speaker()

            discussion_rounds += 1

            if not last_round_someone_spoke:
                self.display_state_terminal(
                    message="--- Discussion ends as no one spoke in the last round ---")
                break

        self.display_state_terminal(
            message=f"--- {phase_name} Discussion End ---")

    def voting_phase(self):
        self.display_state_terminal(message="\n--- Voting Phase ---")
        votes = {}
        vote_log_messages = []
        allowed_vote_actions = [VOTE_YES, VOTE_NO]

        player_names = self.game_state.get_player_names()

        for player in player_names:
            player_status_val = self.game_state.player_status[player]
            if player_status_val == PlayerStatus.ALIVE:
                vote_prompt = f"{player}, vote YES/NO on government."
                llm_interface_voter = self.player_llm_configs[player]
                vote = self.get_player_input(
                    vote_prompt, allowed_vote_actions, player, "Voting", llm_interface_voter).upper()
                votes[player] = vote
                vote_log_messages.append(f"{player} voted {vote}.")
                self.display_state_terminal(message=f"{player} voted.")
            else:
                self.game_state.game_logger.log_to_debug_file(
                    "Game", f"DEBUG: Voting Phase - Player {player} is NOT alive - Skipping vote.")
        self.game_state.log_event(None, " ".join(vote_log_messages))
        return votes

    def legislative_session(self):
        president_name = self.game_state.get_president()
        chancellor_name = self.game_state.gov.chancellor
        llm_interface_president = self.player_llm_configs[president_name]
        llm_interface_chancellor = self.player_llm_configs[chancellor_name]

        policies = self.game_state.draw_policies(3)
        if not policies:
            return None

        discarded_policy = self._president_discard_policy(
            president_name, llm_interface_president, policies)
        if not discarded_policy:
            return None

        enacted_policy = self._chancellor_enact_policy(
            chancellor_name, llm_interface_chancellor, policies)
        if not enacted_policy:
            return None

        legislative_log_msg = f"President {president_name} discarded a policy. Chancellor {chancellor_name} enacted a {enacted_policy} policy."
        self.game_state.log_event(None, legislative_log_msg, private_info={
            president_name: f"Drew policies: {policies + [discarded_policy]}.",
            chancellor_name: f"Received policies: {[enacted_policy, policies[0]]}"})
        self.display_state_terminal(
            message=f"\n{chancellor_name} enacted a {enacted_policy} policy.")
        return enacted_policy

    def _president_discard_policy(self, president_name, llm_interface_president, policies):
        policy_choices_president = [
            f"{DISCARD_ACTION_PREFIX}{i+1}" for i in range(3)]
        discard_prompt = f"{president_name}, discard one policy (1, 2, 3): {policies}"
        while True:
            discard_choice_action = self.get_player_input(
                discard_prompt, policy_choices_president, president_name, "President Discard", llm_interface_president, additional_prompt_info=str(policies))

            if discard_choice_action.startswith(DISCARD_ACTION_PREFIX):
                try:
                    discard_index = int(
                        discard_choice_action[len(DISCARD_ACTION_PREFIX):]) - 1
                    if 0 <= discard_index < len(policies):
                        discarded_policy = policies.pop(discard_index)
                        self.game_state.discard_policy(discarded_policy)
                        self.display_state_terminal(
                            message=f"\n{president_name} discarded a policy.")
                        return discarded_policy
                except ValueError:
                    pass
            self.display_state_terminal(
                error_message=f"Invalid choice from President: {discard_choice_action}. Please choose from: {', '.join(policy_choices_president)}")

    def _chancellor_enact_policy(self, chancellor_name, llm_interface_chancellor, policies):
        policy_choices_chancellor = [
            f"{ENACT_ACTION_PREFIX}{i+1}" for i in range(2)]
        enact_prompt = f"{chancellor_name}, enact one policy (1, 2): {policies}"
        while True:
            enact_choice_action = self.get_player_input(enact_prompt, policy_choices_chancellor, chancellor_name,
                                                        "Chancellor Enact", llm_interface_chancellor, additional_prompt_info=str(policies))
            if enact_choice_action.startswith(ENACT_ACTION_PREFIX):
                try:
                    enact_index = int(
                        enact_choice_action[len(ENACT_ACTION_PREFIX):]) - 1
                    if 0 <= enact_index < len(policies):
                        enacted_policy = policies.pop(enact_index)
                        return enacted_policy
                except ValueError:
                    pass
            self.display_state_terminal(
                error_message=f"Invalid choice from Chancellor: {enact_choice_action}. Please choose from: {', '.join(policy_choices_chancellor)}")

    def executive_action(self):
        president_name = self.game_state.get_president()
        llm_interface_president = self.player_llm_configs[president_name]
        power_used = None
        log_message = None
        allowed_targets = None

        if self.game_state.fasc_policies == 3 and self.config.num_players >= 5:
            power_used = "Investigate"
            action_func = self.game_state.investigate_player
            prompt_text = f"{president_name}, investigate player:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and name not in self.game_state.investigated and self.game_state.player_status[name] == PlayerStatus.ALIVE]
        elif self.game_state.fasc_policies == 4 and self.config.num_players >= 7:
            power_used = "Special Election"
            action_func = self.game_state.call_special_election
            prompt_text = f"{president_name}, choose next president:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and self.game_state.player_status[name] == PlayerStatus.ALIVE]
        elif self.game_state.fasc_policies == 5 and self.config.num_players >= 9:
            power_used = "Policy Peek"
            action_func = self.game_state.policy_peek
            prompt_text = f"{president_name} uses Policy Peek."
            allowed_targets = ["continue"]
        elif self.game_state.fasc_policies >= 4 and (self.config.num_players == 5 or self.config.num_players == 6 or self.config.num_players >= 9):
            power_used = "Execution"
            action_func = self.game_state.kill_player
            prompt_text = f"{president_name}, execute player:"
            allowed_targets = [name for name in self.game_state.get_player_names(
            ) if name != president_name and self.game_state.player_status[name] == PlayerStatus.ALIVE]
        else:
            self.display_state_terminal(message="No executive action.")
            return

        self.display_state_terminal(
            message=f"\n--- Executive Action: {power_used} ---")

        if power_used == "Policy Peek":
            policies_peeked = self.game_state.policy_peek()
            log_message = f"{president_name} used Policy Peek and saw: {policies_peeked}."
            self.display_state_terminal(
                message=f"{president_name} used Policy Peek.")
            self.get_player_input(prompt_text, allowed_targets, president_name,
                                  f"Executive Action: {power_used}", llm_interface_president)

        elif allowed_targets:
            target_player_action = self.get_player_input(prompt_text, allowed_targets, president_name,
                                                         f"Executive Action: {power_used}", llm_interface_president)
            target_player = target_player_action

            if action_func == self.game_state.investigate_player:
                membership = self.game_state.investigate_player(
                    president_name, target_player)
                log_message = f"{president_name} investigated {target_player}. Result: {membership} membership."
                self.display_state_terminal(
                    message=f"\n{log_message}")
                self.display_state_terminal(
                    message=f"\n{president_name} investigated {target_player}. Result: {membership}")
            elif action_func == self.game_state.call_special_election:
                self.game_state.call_special_election(
                    president_name, target_player)
                log_message = f"{president_name} called special election for {target_player}."
                self.display_state_terminal(
                    message=f"\n{log_message}")
                self.display_state_terminal(
                    message=f"\n{president_name} called special election for {target_player}.")
            elif action_func == self.game_state.kill_player:
                kill_successful = self.game_state.kill_player(target_player)
                if kill_successful:
                    log_message = f"{president_name} executed {target_player}."
                else:
                    log_message = f"{president_name} attempted to execute {target_player} but failed (already dead)."

                self.display_state_terminal(message=f"\n{log_message}")
                self.display_state_terminal(
                    message=f"\n{log_message}")
        if log_message:
            self.game_state.log_event(None, log_message)

        self.display_state_terminal(
            message=f"--- Executive Action: {power_used} Completed ---")

    def game_over_screen(self):
        game_over_msg = "\n======== GAME OVER ========"
        self.display_state_terminal(message=game_over_msg)
        self.game_state.log_event(None, game_over_msg)

        winner_msg = f"Winner: {self.game_state.winner}!"
        self.display_state_terminal(message=winner_msg)
        self.game_state.log_event(None, winner_msg)

        roles_header = "\n--- Roles ---"
        self.display_state_terminal(message=roles_header)
        self.game_state.log_event(None, roles_header)
        for name, role in self.game_state.roles.items():
            role_msg = f"{name}: {role}"
            self.display_state_terminal(message=role_msg)
            self.game_state.log_event(None, role_msg)

        log_header = "\n--- Public Log ---"
        self.display_state_terminal(message=log_header)
        self.game_state.log_event(None, log_header)
        for event in self.game_state.public_log:
            self.display_state_terminal(message=f"- {event}")

        self.game_state.log_event(None, "--- GAME SUMMARY ---")
        self.game_state.log_event(None, f"Winner: {self.game_state.winner}")
        self.game_state.log_event(
            None, f"Liberal Policies Enacted: {self.game_state.lib_policies}")
        self.game_state.log_event(
            None, f"Fascist Policies Enacted: {self.game_state.fasc_policies}")
        self.game_state.log_event(
            None, f"Number of failed elections: {self.game_state.failed_elections}")
        self.game_state.log_event(
            None, f"Hitler was: {self.game_state.get_player_names_by_role(Role.HITLER)[0]}")
        self.game_state.log_event(
            None, f"Fascists were: {', '.join(self.game_state.get_player_names_by_role(Role.FASCIST))}")
        self.game_state.log_event(
            None, f"Liberals were: {', '.join(self.game_state.get_player_names_by_role(Role.LIBERAL))}")

        if self.config.log_to_file_enabled:
            self.logger.close_log_files()

    def run_game(self):
        self.setup_game()

        while not self.game_state.game_over:
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

    game_config = GameConfig(args)
    game_runner = GameRunner(game_config)

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

    game_runner.run_game()

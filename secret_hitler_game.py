# secret_hitler_game.py (SIMPLIFIED AND REFACTORED - VARIABLE NAMES CORRECTED)
import argparse
import os
import sys
import time

from secret_hitler_engine import GameState, is_valid_chancellor_nominee, LIBERAL, FASCIST, ALIVE, DEAD
from llm_interface import LLMPlayerInterface, llm_debug_enabled, slowdown_timer


def display_state_terminal(game_state: GameState, current_player_name: str | None = None):
    """Displays the current game state in the terminal."""
    print("\n======== Game State ========")
    # Corrected: lib_policies
    print(f"Liberal Policies: {game_state.lib_policies}")
    # Corrected: fasc_policies
    print(f"Fascist Policies: {game_state.fasc_policies}")
    print(f"Election Tracker: {game_state.election_tracker}")
    # Corrected: gov
    print(f"President: {game_state.gov['president'] or 'None'}")
    # Corrected: gov
    print(f"Chancellor: {game_state.gov['chancellor'] or 'None'}")
    # Corrected: veto_power
    print(f"Veto Power: {'Yes' if game_state.veto_power else 'No'}")

    print("\n===== PUBLIC LOG =====")
    for event in game_state.public_log:  # Corrected: public_log
        print(f"- {event}")
    if game_state.discussion_history:
        print("\n===== DISCUSSION =====")
        for message in game_state.discussion_history:
            print(f"- {message}")
    if current_player_name:
        print(f"\n=== {current_player_name}'s Private Log ===")
        # Corrected: private_logs
        for event in game_state.private_logs[current_player_name]:
            print(f"- {event}")

    print("\n===== END STATE =====")


def get_player_input(prompt, allowed_responses, game_state, current_player, game_phase, llm_interface, additional_prompt_info=None):
    """Gets player input from LLM and handles terminal output."""
    global slowdown_timer

    print(
        f"\n===== TURN: {current_player} ({game_state.get_player_role(current_player)}) - PHASE: {game_phase} =====")
    display_state_terminal(game_state, current_player)

    llm_response_action = llm_interface.get_llm_response(
        game_state, prompt, allowed_responses, game_phase, additional_prompt_info
    )

    if slowdown_timer <= 0:
        # Wait for user input if no timer
        input("\nPress Enter to Continue...")
    return llm_response_action


def setup(num_players, player_llm_configs):
    """Sets up the game."""
    player_names = list(player_llm_configs.keys())
    if len(player_names) != num_players:
        raise ValueError(
            f"Player config mismatch: {len(player_names)} vs {num_players}")
    game_state = GameState(player_names)

    print("\nRoles assigned.")
    for player in player_names:
        role = game_state.get_player_role(player)
        private_info = {player: f"Your role is: {role}"}
        if role in (FASCIST, "Hitler"):
            fascists = [name for name, r in game_state.roles.items()
                        if r in (FASCIST, "Hitler")]
            private_info[player] += f"\nFascists: {', '.join(fascists)}"
            if role == FASCIST and num_players >= 7:
                hitler = [name for name, r in game_state.roles.items()
                          if r == "Hitler"][0]
                private_info[player] += f"\nHitler: {hitler}"
        game_state.log_event(None, "Roles assigned.",
                             private_info=private_info)
    return game_state, player_llm_configs


def election_phase(game_state, llm_interfaces):
    """Runs election phase."""
    president_name = game_state.get_president()
    llm_interface_president = llm_interfaces[president_name]

    valid_nominees = [name for name in game_state.get_player_names(
    ) if is_valid_chancellor_nominee(game_state, president_name, name)]
    nominee_prompt = f"{president_name}, nominate Chancellor from: {', '.join(valid_nominees)}"
    nominee_name = get_player_input(
        nominee_prompt, valid_nominees, game_state, president_name, "Nomination", llm_interface_president)

    game_state.set_government(president_name, nominee_name)
    print(f"\n{president_name} nominated {nominee_name} Chancellor.")

    discussion_phase(game_state, "Election", llm_interfaces)
    votes = voting_phase(game_state, llm_interfaces)
    yes_votes = list(votes.values()).count("YES")
    print(f"\nVote Results: Yes={yes_votes}, No={len(votes) - yes_votes}")
    game_state.log_event(
        None, f"Vote Results: Yes={yes_votes}, No={len(votes) - yes_votes}")
    return yes_votes > len(votes) / 2


def discussion_phase(game_state, phase_name, llm_interfaces):
    """Runs discussion phase."""
    print(f"\n--- {phase_name} Discussion ---")
    game_state.start_discussion(phase_name)

    players_passed = set()
    discussion_rounds = 0
    max_rounds = 3

    while discussion_rounds < max_rounds:
        current_speaker = game_state.get_current_discussion_speaker()
        if not current_speaker or current_speaker in players_passed:
            game_state.next_discussion_speaker()
            if not game_state.get_current_discussion_speaker():  # All passed or no speakers left
                break
            continue

        llm_interface = llm_interfaces[current_speaker]
        prompt = f"{current_speaker}, Discuss {phase_name}. (You can say 'pass')"
        message = get_player_input(prompt, [
                                   "pass"], game_state, current_speaker, f"{phase_name} Discussion", llm_interface)

        if message.lower() == "pass":
            print(f"{current_speaker} passes.")
            players_passed.add(current_speaker)
            # Added log event for pass
            game_state.log_event(current_speaker, "passed discussion turn.")
        else:
            game_state.record_discussion_message(
                current_speaker, message)  # Record message FIRST

        # Move to next speaker AFTER recording message
        game_state.next_discussion_speaker()
        # Only display state if not all passed
        if len(players_passed) < len([p for p in game_state.get_player_names() if game_state.player_status[p] == ALIVE]):
            # Display updated state HERE, after message recorded
            display_state_terminal(game_state)

        if len(players_passed) == len([p for p in game_state.get_player_names() if game_state.player_status[p] == ALIVE]):
            print("All players passed discussion.")
            break
        if game_state.get_current_discussion_speaker() == game_state.get_first_discussion_speaker():  # All players had a turn
            discussion_rounds += 1
    print(f"--- {phase_name} Discussion End ---")


def voting_phase(game_state, llm_interfaces):
    """Runs voting phase."""
    print("\n--- Voting Phase ---")
    votes = {}
    for player in game_state.get_player_names():  # Corrected: get_player_names()
        if game_state.player_status[player] == ALIVE:
            vote_prompt = f"{player}, vote YES/NO on government."
            llm_interface_voter = llm_interfaces[player]
            vote = get_player_input(vote_prompt, [
                                    "YES", "NO"], game_state, player, "Voting", llm_interface_voter).upper()
            votes[player] = vote
            game_state.log_event(player, f"Voted {vote}.", private_info={
                                 player: f"You voted {vote}"})
            print(f"{player} voted.")
    return votes


def legislative_session(game_state, llm_interfaces):
    """Runs legislative session."""
    president_name = game_state.get_president()
    chancellor_name = game_state.gov["chancellor"]
    llm_interface_president = llm_interfaces[president_name]
    llm_interface_chancellor = llm_interfaces[chancellor_name]

    policies = game_state.draw_policies(3)
    if not policies:
        return None
    game_state.log_event(president_name, f"Drew policies: {policies}", private_info={
                         president_name: f"Drew policies: {policies}"})

    # President's turn
    discard_prompt = f"{president_name}, discard one policy (1, 2, 3): {policies}"
    while True:
        discard_choice = get_player_input(discard_prompt, [str(i+1) for i in range(
            3)], game_state, president_name, "President Discard", llm_interface_president, additional_prompt_info=str(policies))
        try:
            discard_index = int(discard_choice) - 1
            if 0 <= discard_index < len(policies):
                break
        except ValueError:
            print(f"Invalid choice from President: {discard_choice}. Retrying...")
            continue

    discarded_policy = policies.pop(discard_index)
    game_state.discard_policy(discarded_policy)
    print(f"\n{president_name} discarded a policy.")

    # Chancellor's turn
    enact_prompt = f"{chancellor_name}, enact one policy (1, 2): {policies}"
    while True:
        enact_choice = get_player_input(enact_prompt, [str(i+1) for i in range(2)], game_state, chancellor_name,
                                      "Chancellor Enact", llm_interface_chancellor, additional_prompt_info=str(policies))
        try:
            enact_index = int(enact_choice) - 1
            if 0 <= enact_index < len(policies):
                break
        except ValueError:
            print(f"Invalid choice from Chancellor: {enact_choice}. Retrying...")
            continue

    enacted_policy = policies.pop(enact_index)
    game_state.enact_policy(enacted_policy)
    print(f"\n{chancellor_name} enacted a {enacted_policy} policy.")
    return enacted_policy


def executive_action(game_state, llm_interfaces):
    """Runs executive action based on fascist policies enacted."""
    president_name = game_state.get_president()
    llm_interface_president = llm_interfaces[president_name]

    power_used = None
    if game_state.fasc_policies == 3 and game_state.num_players >= 5:  # Corrected: fasc_policies
        power_used = "Investigate"
        action_func = game_state.investigate_player
        prompt_text = f"{president_name}, investigate player:"
        allowed_targets = [name for name in game_state.get_player_names(
            # Corrected: investigated
        ) if name != president_name and name not in game_state.investigated and game_state.player_status[name] == ALIVE]
    elif game_state.fasc_policies == 4 and game_state.num_players >= 7:  # Corrected: fasc_policies
        power_used = "Special Election"
        action_func = game_state.call_special_election
        prompt_text = f"{president_name}, choose next president:"
        allowed_targets = [name for name in game_state.get_player_names(
        ) if name != president_name and game_state.player_status[name] == ALIVE]
    elif game_state.fasc_policies == 5 and game_state.num_players >= 9:  # Corrected: fasc_policies
        power_used = "Policy Peek"
        action_func = game_state.policy_peek
        prompt_text = f"{president_name} uses Policy Peek."
        allowed_targets = None
    # Corrected: fasc_policies
    elif game_state.fasc_policies >= 4 and (game_state.num_players == 5 or game_state.num_players == 6 or game_state.num_players >= 9):
        power_used = "Execution"
        action_func = game_state.kill_player
        prompt_text = f"{president_name}, execute player:"
        allowed_targets = [name for name in game_state.get_player_names(
        ) if name != president_name and game_state.player_status[name] == ALIVE]
    else:
        print("No executive action.")
        return

    print(f"\n--- Executive Action: {power_used} ---")

    if power_used == "Policy Peek":
        # Directly call policy peek as no player input needed
        game_state.policy_peek(president_name)
        print(f"{president_name} used Policy Peek.")
    elif allowed_targets:
        target_player = get_player_input(prompt_text, allowed_targets, game_state,
                                         president_name, f"Executive Action: {power_used}", llm_interface_president)
        if action_func == game_state.investigate_player:
            membership = game_state.investigate_player(
                president_name, target_player)
            print(
                f"\n{president_name} investigated {target_player}. Result: {membership}")
        elif action_func == game_state.call_special_election:
            game_state.call_special_election(president_name, target_player)
            print(
                f"\n{president_name} called special election for {target_player}.")
        elif action_func == game_state.kill_player:
            game_state.kill_player(target_player)
            print(f"\n{president_name} executed {target_player}.")

    print(f"--- Executive Action: {power_used} Completed ---")


def game_over_screen(game_state):
    """Displays game over screen."""
    print("\n======== GAME OVER ========")
    print(f"Winner: {game_state.winner}!")
    print("\n--- Roles ---")
    for name, role in game_state.roles.items():
        print(f"{name}: {role}")
    print("\n--- Public Log ---")
    for event in game_state.public_log:  # Corrected: public_log
        print(f"- {event}")


def play_game(num_players, player_llm_configs, use_slowdown_timer):
    """Plays Secret Hitler game with LLMs."""
    global slowdown_timer
    slowdown_timer = use_slowdown_timer

    game_state, llm_interfaces = setup(num_players, player_llm_configs)

    while not game_state.game_over:
        president_name = game_state.get_president()
        gov_approved = election_phase(game_state, llm_interfaces)

        if gov_approved:
            game_state.election_tracker = 0
            if game_state.check_hitler_chancellor_win():
                print("\nFascists win: Hitler Chancellor after 3 Fascist policies!")
                game_state.game_over = True
                game_state.winner = "Fascists"
                break
            enacted_policy = legislative_session(game_state, llm_interfaces)
            if enacted_policy:
                executive_action(game_state, llm_interfaces)
        else:
            game_state.reset_government()
            game_state.increment_election_tracker()
            if game_state.election_tracker >= 3:
                print("\nElection tracker maxed! Chaos policy enacted.")
                game_state.enact_chaos_policy()
                game_state.election_tracker = 0
                if game_state.game_over:
                    break  # Check game over after chaos policy

        if not game_state.game_over:
            game_state.next_president()
            print("\n--- Next Round ---")

    game_over_screen(game_state)


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
    parser.add_argument("--player_models", nargs="+",
                        help="PlayerName=ModelName (e.g., Player1=gemini-2.0-flash Player2=gpt-4)")
    args = parser.parse_args()

    if not 5 <= args.num_players <= 10:
        sys.exit("Players must be 5-10")
    if args.slowdown < 0:
        sys.exit("Slowdown must be non-negative")

    llm_debug_enabled = args.debug_llm
    # Timer takes precedence unless press_enter
    use_slowdown_timer = args.slowdown if not args.press_enter else 0

    player_models = {}
    if args.player_models:
        for player_config in args.player_models:
            name, model = player_config.split("=", 1)
            player_models[name] = model
    else:  # Default models if not specified
        for i in range(args.num_players):
            player_models[f"Player{i+1}"] = "gemini-2.0-flash"

    player_llm_configs = {}
    default_api_key = os.environ.get("GEMINI_API_KEY")
    if not default_api_key:
        sys.exit("No API Key found.")

    for player_name, model_name in player_models.items():
        player_llm_configs[player_name] = LLMPlayerInterface(
            player_name, model_name, default_api_key)

    print("Running Secret Hitler LLM Game.")
    if use_slowdown_timer > 0:
        print(f"Slowdown timer: {use_slowdown_timer} seconds.")
    elif args.press_enter:
        print("Press Enter to continue after each turn.")
    if llm_debug_enabled:
        print("LLM debug output enabled.")

    play_game(args.num_players, player_llm_configs, use_slowdown_timer)

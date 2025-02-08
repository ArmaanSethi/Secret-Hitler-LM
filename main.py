"""Main script to run the text-based Secret Hitler game."""

from secret_hitler_engine import (
    GameState,
    is_valid_chancellor_nominee,
    get_player_role,
    get_player_names,
    kill_player,
    reveal_hitler,
    investigate_player,
    call_special_election,
    policy_peek,
    LIBERAL,
    FASCIST,
    ALIVE,
    DEAD,
)


def display_game_state(game_state: GameState, current_player_name: str | None = None):
    """Displays the current game state to the console.

    Args:
        game_state: The current game state object.
        current_player_name: Optional name of the current player.
    """
    print("\n================ Game State ================")
    print(f"Liberal Policies Enacted: {game_state.liberal_policies_enacted}")
    print(f"Fascist Policies Enacted: {game_state.fascist_policies_enacted}")
    print(f"Election Tracker: {game_state.election_tracker}")
    print(f"Consecutive Failed Elections: {game_state.consecutive_failed_elections}")
    print(f"President: {game_state.government['president'] if game_state.government['president'] else 'None'}")
    print(f"Chancellor: {game_state.government['chancellor'] if game_state.government['chancellor'] else 'None'}")
    if game_state.previous_governments:
        print("Previous Governments:")
        for pres, chan in game_state.previous_governments:
            print(f"  President: {pres}, Chancellor: {chan}")
    else:
        print("No previous governments yet.")
    print(f"Current President: {game_state.get_president()}")
    print("Player Status:")
    for name, status in game_state.player_status.items():
        print(f"  {name}: {status}")
    print(f"Veto Power Available: {'Yes' if game_state.veto_power_available else 'No'}")
    print(f"Investigated Players: {', '.join(game_state.investigated_players)}")

    print("\n--- Public Game Log ---")
    print("\n=== PUBLIC GAME LOG START ===")
    for event in game_state.public_game_log:
        print(f"- {event}")
    print("=== PUBLIC GAME LOG END ===")

    if current_player_name:
        print(f"\n=== {current_player_name}'s PRIVATE GAME LOG START ===")
        for event in game_state.private_game_logs[current_player_name]:
            print(f"- {event}")
        print(f"=== {current_player_name}'s PRIVATE GAME LOG END ===")

    if game_state.discussion_history:
        print("\n--- Current Discussion ---")
        for message in game_state.discussion_history:
            print(f"  {message}")

    print("==========================================")
    if current_player_name:
        print(f"It's your turn, {current_player_name}!")


def get_player_input(prompt: str, allowed_responses: list[str] | None = None, input_type: str = "text",
                     game_state: GameState | None = None, current_player: str | None = None, game_phase: str | None = None) -> str:
    """Gets validated player input from the console.

    Args:
        prompt: The prompt to display to the player.
        allowed_responses: Optional list of valid input options (case-insensitive).
        input_type: 'text' or 'int'.  If 'int', the *first* allowed response
            is returned as an integer (index 0).
        game_state: Optional game state to display.
        current_player: Optional current player name for display.
        game_phase: The current phase of the game (e.g., "Nomination", "Election").

    Returns:
        The validated player input (string or int, based on input_type).
    """
    while True:
        if game_state:
            clear_and_display_state(game_state, current_player)

        if game_phase:
            print(f"\n--- Current Phase: {game_phase} ---")

        user_input = input(prompt).strip()

        if input_type == "int":
            try:
                int(user_input)
                if allowed_responses:
                    if 1 <= int(user_input) <= len(allowed_responses):
                        return allowed_responses[int(user_input) - 1]
                    else:
                        print(f"Invalid input.  Please enter a number between 1 and {len(allowed_responses)}.")
                        continue
                else:
                    return user_input
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

        if allowed_responses and {r.upper() for r in allowed_responses} == {"YES", "NO"}:
            if user_input.upper() in ["YES", "Y"]:
                return "YES"
            elif user_input.upper() in ["NO", "N"]:
                return "NO"
            else:
                print("Invalid input. Please enter Yes or No.")
                continue

        if allowed_responses is None or user_input.upper() in [r.upper() for r in allowed_responses]:
            return user_input
        else:
            print(f"Invalid input. Please choose from: {', '.join(allowed_responses)}")


def clear_and_display_state(game_state: GameState, current_player_name: str | None):
    """Clears screen and displays game state."""
    print("\n" * 50)
    display_game_state(game_state, current_player_name)



def play_discussion_phase(game_state: GameState, phase_name: str):
    """Plays a discussion phase, allowing players to exchange messages.

    Args:
        game_state: The current game state object.
        phase_name: The name of the discussion phase (e.g., "Nomination").
    """
    print(f"\n--- {phase_name} Discussion Phase ---")
    game_state.start_discussion(phase_name)

    while True:
        current_speaker = game_state.get_current_discussion_speaker()
        if not current_speaker:
            print("No players alive to continue discussion.")
            break

        message = get_player_input(
            f"{current_speaker}, say something (or type 'pass' to skip turn): ",
            game_state=game_state,
            current_player=current_speaker,
            game_phase=phase_name
        )

        # Record the turn progression whether the player speaks or passes
        if message.lower() == "pass":
            game_state.discussion_turn_order_index += 1
            game_state.discussion_turn_counts[current_speaker] += 1
        else:
            game_state.record_discussion_message(current_speaker, message)

        if game_state.can_end_discussion(by_president=(current_speaker == game_state.get_president())) and current_speaker == game_state.get_president():
            end_discussion_input = get_player_input(
                f"\nPresident {game_state.get_president()}, as the president, you can review the discussion and decide to end it.\nDiscussion summary:\n{game_state.get_discussion_summary()}\nDo you want to end the discussion and call for vote? (YES/NO): ",
                allowed_responses=["YES", "NO"],
                game_state=game_state,
                current_player=current_speaker,
                game_phase=phase_name
            ).upper()
            if end_discussion_input == "YES":
                print("The president has ended the discussion.")
                break
        else:
            get_player_input(
                "Press Enter to pass turn to the next player in discussion...",
                game_state=game_state,
                current_player=current_speaker
            )

        if all(game_state.discussion_turn_counts.get(name, 0) >= game_state.max_discussion_turns_per_player
               for name in game_state.player_names if game_state.player_status[name] == ALIVE):
            print("Maximum discussion turns reached.")
            break
        if game_state.game_over:
            break



def setup_game() -> GameState:
    """Sets up the game: gets player names, initializes GameState, and assigns roles.

    Returns:
        The initialized GameState object.
    """
    player_names = []
    num_players = 0
    while num_players < 5 or num_players > 10:
        num_players = int(get_player_input("Enter the number of players (5-10): ", input_type="int"))
        if not (5 <= num_players <= 10):
            print("Invalid number of players. Must be between 5 and 10.")
    for i in range(num_players):
        name = get_player_input(f"Enter name for Player {i + 1}: ")
        player_names.append(name)

    game_state = GameState(player_names)

    print("\nRoles have been assigned.")
    for player in player_names:
        get_player_input(
            f"{player}, press Enter to see YOUR ROLE **PRIVATELY** (without showing others)...",
            current_player=player
        )
        role = get_player_role(game_state, player)

        private_info = {player: f"Your role is: {role}"}
        if role in (FASCIST, "Hitler"):
            fascists = [name for name, r in game_state.roles.items() if r in (FASCIST, "Hitler")]
            private_info[player] += f"\nThe Fascists are: {', '.join(fascists)}"
            if role == FASCIST and game_state.num_players >= 7:
                hitler = [name for name, r in game_state.roles.items() if r == "Hitler"][0]
                private_info[player] += f"\nHitler is: {hitler}"

        game_state.log_event(None, "Roles have been assigned.", private_info=private_info)
        print(f"Your role is: {role}")

        if role in (FASCIST, "Hitler"):
            print(f"The Fascists are: {', '.join(fascists)}")
            if role == FASCIST and game_state.num_players >= 7:
                print(f"Hitler is: {[name for name, r in game_state.roles.items() if r == 'Hitler'][0]}")

        get_player_input("Press Enter to continue...", current_player=player)
        print("\n" * 50)

    return game_state


def run_election_phase(game_state: GameState) -> bool:
    """Runs the election phase: nomination, discussion, and voting.

    Args:
        game_state: The current GameState object.

    Returns:
        True if the government is approved, False otherwise.
    """
    president_name = game_state.get_president()

    while True:
        nominee_name = get_player_input(
            f"{president_name}, nominate a Chancellor: ",
            game_state=game_state,
            current_player=president_name,
            game_phase="Nomination"
        )
        if nominee_name not in get_player_names(game_state):
            get_player_input("Invalid nominee name.  Must be an existing player.", game_state=game_state, current_player=president_name)
        elif not is_valid_chancellor_nominee(game_state, president_name, nominee_name):
            get_player_input("Invalid nomination.  Check for term limits or other restrictions.", game_state=game_state, current_player=president_name)
        else:
            break

    game_state.set_government(president_name, nominee_name)
    get_player_input(
        f"{president_name} has nominated {nominee_name} as Chancellor. Press enter to continue.",
        game_state=game_state,
        current_player=president_name,
    )

    print("\n--- Election Phase ---")
    play_discussion_phase(game_state, "Election")

    votes = {}
    for player in get_player_names(game_state):
        if game_state.player_status[player] == ALIVE:
            vote = get_player_input(
                f"{player}, vote YES or NO on the government "
                f"({president_name} as President, {nominee_name} as Chancellor): ",
                allowed_responses=["YES", "NO"],
                game_state=game_state,
                current_player=player,
                game_phase="Election"
            ).upper()
            votes[player] = vote
            private_info = {player: f"You voted {vote}"}
            game_state.log_event(player, "Cast vote for government", private_info=private_info)
            print("\n" * 50)

    yes_votes = list(votes.values()).count("YES")
    no_votes = list(votes.values()).count("NO")
    game_state.log_event(None, f"Vote Results - Yes: {yes_votes}, No: {no_votes}")
    for player, vote in votes.items():
        game_state.log_event(None, f"{player} voted {vote}")

    clear_and_display_state(game_state, None)
    print("\n--- Vote Results ---")
    for player, vote in votes.items():
        print(f"{player} voted {vote}")

    return yes_votes > no_votes


def run_legislative_session(game_state: GameState) -> str | None:
    """Runs the legislative session: policy drawing, discarding, and enactment.

    Args:
        game_state: The current GameState object.

    Returns:
        The enacted policy (LIBERAL or FASCIST), or None if vetoed.
    """
    president_name = game_state.get_president()
    chancellor_name = game_state.government["chancellor"]

    print("\n--- Legislative Session ---")
    policy_cards = game_state.draw_policies(3)
    private_info_pres = {president_name: f"Drew policies: {policy_cards}"}
    game_state.log_event(president_name, "Drew 3 policies.", private_info=private_info_pres)

    discard_choice = get_player_input(
        f"{president_name}, you drew policies:\n" +
        "\n".join(f"{i + 1}. {policy}" for i, policy in enumerate(policy_cards)) +
        "\nDiscard one policy (enter 1, 2, or 3): ",
        allowed_responses=[str(i + 1) for i in range(len(policy_cards))],
        input_type="int",
        game_state=game_state,
        current_player=president_name,
        game_phase="Legislative Session"
    )
    discard_index = int(discard_choice) - 1
    discarded_policy = policy_cards.pop(discard_index)
    game_state.discard_policy(discarded_policy)
    private_info_pres_discard = {
        president_name: f"Discarded policy at index {discard_index + 1} (which was: {discarded_policy}). "
                        f"Remaining policies passed to Chancellor: {policy_cards}"
    }
    game_state.log_event(
        president_name,
        f"Discarded a policy. Passed 2 to Chancellor.",
        private_info=private_info_pres_discard,
    )

    get_player_input(
        f"{president_name} discarded a policy. Passing remaining policies to {chancellor_name} (Chancellor).\nPress Enter...",
        game_state=game_state,
        current_player=chancellor_name
    )

    private_info_chan = {chancellor_name: f"Received policies: {policy_cards}"}
    game_state.log_event(chancellor_name, "Received 2 policies.", private_info=private_info_chan)

    if game_state.veto_power_available:
        veto_option = get_player_input(
            f"{chancellor_name}, you received policies: {policy_cards}\nDo you want to VETO? (YES/NO): ",
            allowed_responses=["YES", "NO"],
            game_state=game_state,
            current_player=chancellor_name,
            game_phase="Legislative Session"
        ).upper()

        if veto_option == "YES":
            veto_president_confirm = get_player_input(
                f"{president_name}, Chancellor wants to VETO. Confirm VETO? (YES/NO): ",
                allowed_responses=["YES", "NO"],
                game_state=game_state,
                current_player=president_name,
                game_phase="Legislative Session"
            ).upper()
            if veto_president_confirm == "YES":
                print("Government VETOED!")
                game_state.log_event(None, "Government vetoed.")
                game_state.reset_government()
                game_state.increment_election_tracker()
                return None

            else:
                print("President rejected VETO. Chancellor must enact policy.")

    enact_choice = get_player_input(
        f"{chancellor_name}, you received policies:\n" +
        "\n".join(f"{i+1}. {policy}" for i, policy in enumerate(policy_cards)) +
        "\nChoose a policy to enact (enter 1 or 2): ",
        allowed_responses=[str(i+1) for i in range(len(policy_cards))],
        input_type="int",
        game_state=game_state,
        current_player=chancellor_name,
        game_phase="Legislative Session"
    )

    enact_index = int(enact_choice) - 1
    enacted_policy = policy_cards[enact_index]
    game_state.enact_policy(enacted_policy)
    game_state.discard_policy(policy_cards[1 - enact_index])
    return enacted_policy



def run_executive_action(game_state: GameState):
    """Runs the executive action phase (presidential powers).

    Args:
        game_state: The current GameState object.
    """
    president_name = game_state.get_president()

    if game_state.fascist_policies_enacted == 3 and game_state.num_players >= 5:
        while True:
            target_player = get_player_input(
                f"{president_name}, investigate loyalty of which player?: ",
                game_state=game_state,
                current_player=president_name,
                game_phase="Presidential Power: Investigate Loyalty"
            )
            if target_player not in get_player_names(game_state):
                print("Invalid player name.")
                continue

            membership = investigate_player(game_state, president_name, target_player)
            if membership:
                private_info = {president_name: f"Investigated {target_player}.  Membership: {membership}"}
                game_state.log_event(president_name, f"Investigated loyalty of {target_player}.", private_info=private_info)
                get_player_input(
                    f"{target_player}'s Membership Card is revealed to **YOU PRIVATELY** as: {membership}\nPress Enter to continue...",
                    game_state=game_state,
                    current_player=president_name
                )
                break
            else:
                print("Invalid investigation target (already investigated, dead, or self).")

    elif game_state.fascist_policies_enacted == 4 and game_state.num_players >= 7:
        # Special Election
        while True:
            target_president = get_player_input(
                f"{president_name}, choose the next President (Special Election): ",
                game_state=game_state,
                current_player=president_name,
                game_phase="Presidential Power: Special Election"
            )
            if target_president not in get_player_names(game_state):
                print("Invalid player name.")
                continue

            if call_special_election(game_state, president_name, target_president):
                get_player_input(
                    f"Next President will be {target_president} after your term.\nPress Enter to continue...",
                    game_state=game_state,
                    current_player=president_name
                )
                break
            else:
                print("Invalid special election target (self or dead).")

    elif game_state.fascist_policies_enacted == 5 and game_state.num_players >= 9:
        peeked_policies = policy_peek(game_state, president_name)
        if peeked_policies:
            private_info_peek = {president_name: f"Peeked at top 3 policies: {peeked_policies}"}
            game_state.log_event(president_name, "Used Policy Peek power.", private_info=private_info_peek)
            get_player_input(
                f"{president_name}, you peek at the top 3 policies **PRIVATELY**:\n" +
                "\n".join(f"{i + 1}. {policy}" for i, policy in enumerate(peeked_policies)) +
                "\nPress Enter to continue...",
                game_state=game_state,
                current_player=president_name
            )
        else:
            print("Policy peek failed (no policies in deck).")

    elif game_state.fascist_policies_enacted >= 4 and game_state.num_players >= 5:
        if game_state.fascist_policies_enacted >= 6 or game_state.num_players >= 7:
            while True:
                target_player_execute = get_player_input(
                    f"{president_name}, execute which player?: ",
                    game_state=game_state,
                    current_player=president_name,
                    game_phase="Presidential Power: Execution"
                )
                if target_player_execute not in get_player_names(game_state):
                    print("Invalid player name.")
                    continue
                if kill_player(game_state, target_player_execute):
                    game_state.log_event(president_name, f"Executed player {target_player_execute}.")
                    break
                else:
                    print("Execution failed (player already dead).")


def display_game_over(game_state: GameState):
    """Displays the game over screen and results."""
    clear_and_display_state(game_state, None)
    print("\n================ Game Over! ================")
    print(f"Winner: {game_state.winner}!")
    print("\n--- Roles ---")
    for name, role in game_state.roles.items():
        print(f"{name}: {role}")
    print("\n--- Game Log ---")
    for event in game_state.public_game_log:
        print(f"- {event}")

    print("\n--- Private Game Logs ---")
    for player_name in game_state.player_names:
        print(f"\n** {player_name}'s Private Log **")
        for event in game_state.private_game_logs[player_name]:
            print(f"- {event}")



def display_turn_summary(game_state: GameState):
    """Displays a turn summary."""
    president_name = game_state.get_president()
    print("\n===== Turn Summary =====")
    print(f"Current President: {president_name} ({game_state.roles[president_name]})")
    print(f"Liberal Policies: {game_state.liberal_policies_enacted}, Fascist Policies: {game_state.fascist_policies_enacted}")
    print(f"Election Tracker: {game_state.election_tracker}")
    print("=========================")



def play_secret_hitler():
    """Plays a game of Secret Hitler."""
    game_state = setup_game()

    while not game_state.game_over:
        display_turn_summary(game_state)
        president_name = game_state.get_president()

        # Election Phase
        government_approved = run_election_phase(game_state)

        if government_approved:
            game_state.election_tracker = 0
            game_state.consecutive_failed_elections = 0

            if (game_state.government["chancellor"]
                and game_state.fascist_policies_enacted >= 3
                and game_state.roles[game_state.government["chancellor"]] == "Hitler"
                and not game_state.hitler_revealed):
                print("\nHitler elected as Chancellor after 3 Fascist policies!")
                reveal_hitler(game_state)
                game_state.check_game_end_conditions()
                if game_state.game_over:
                    break

            # Legislative Session
            enacted_policy = run_legislative_session(game_state)
            if enacted_policy is None:
                continue

            run_executive_action(game_state)

        else:
            get_player_input("Government failed!", game_state=game_state)
            game_state.reset_government()
            game_state.increment_election_tracker()

        if not game_state.game_over:
            if game_state.special_election_president:
                game_state.current_president_index = game_state.player_names.index(game_state.special_election_president)
                game_state.special_election_president = None
                get_player_input(
                    f"\nSpecial Election! {game_state.get_president()} is the new President.",
                    game_state=game_state
                )
            else:
                game_state.next_president()

            get_player_input("\nPress Enter to start the next round...", game_state=game_state)
            print("\n" * 50)

    display_game_over(game_state)


if __name__ == "__main__":
    play_secret_hitler()

# main.py
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
)


def display_game_state(game_state, current_player_name=None):
    """Displays the current game state to the console.

    Args:
        game_state: The current game state object.
        current_player_name: Optional name of the current player for display.
    """
    print("\n================ Game State ================")
    print(f"Liberal Policies Enacted: {game_state.liberal_policies_enacted}")
    print(f"Fascist Policies Enacted: {game_state.fascist_policies_enacted}")
    print(f"Election Tracker: {game_state.election_tracker}")
    print(
        f"Consecutive Failed Elections: {game_state.consecutive_failed_elections}")
    print(
        f"President: {game_state.government['president'] if game_state.government['president'] else 'None'}"
    )
    print(
        f"Chancellor: {game_state.government['chancellor'] if game_state.government['chancellor'] else 'None'}"
    )
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
    print(
        f"Veto Power Available: {'Yes' if game_state.veto_power_available else 'No'}")
    print(
        f"Investigated Players: {', '.join(game_state.investigated_players)}")

    print("\n--- Public Game Log ---")
    for event in game_state.public_game_log:
        print(f"- {event}")
    if game_state.discussion_history:
        print("\n--- Current Discussion ---")
        for message in game_state.discussion_history:
            print(f"  {message}")

    print("==========================================")
    if current_player_name:
        print(f"It's your turn, {current_player_name}!")


def get_player_input(prompt, valid_options=None, input_type="text"):
    """Gets validated player input from the console.

    Args:
        prompt: The prompt to display to the player.
        valid_options: Optional list of valid input options.
        input_type: Optional type of input ('text' or 'int').

    Returns:
        The validated player input (string or int).
    """
    while True:
        user_input = input(prompt).strip()
        if input_type == "int":
            try:
                user_input = int(user_input)
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

        # Handle yes/no inputs more flexibly
        if valid_options and set(valid_options) == {"YES", "NO"}:
            if user_input.upper() in ["YES", "Y"]:
                return "YES"
            elif user_input.upper() in ["NO", "N"]:
                return "NO"
            else:
                print("Invalid input. Please enter Yes or No.")
                continue

        if valid_options is None or (
            valid_options
            and str(user_input) in [str(opt) for opt in valid_options]
        ) or (not valid_options and input_type == "text"):
            return user_input
        else:
            print(
                f"Invalid input. Please choose from: {', '.join(map(str, valid_options))}")


def play_discussion_phase(game_state, phase_name):
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

        print(f"\nIt's {current_speaker}'s turn to speak in the discussion.")
        message = get_player_input(
            f"{current_speaker}, say something (or type 'pass' to skip turn): "
        )

        # Record the turn progression whether the player speaks or passes
        if message.lower() == "pass":
            game_state.discussion_turn_order_index += 1
            game_state.discussion_turn_counts[current_speaker] += 1
        else:
            game_state.record_discussion_message(current_speaker, message)

        if game_state.can_end_discussion(
            by_president=(game_state.get_current_discussion_speaker()
                          == game_state.get_president())
        ):
            end_discussion_input = get_player_input(
                f"\n{game_state.get_president()}, discussion summary:\n{game_state.get_discussion_summary()}\nEnd discussion and call for vote? (YES/NO): ",
                valid_options=["YES", "NO"]
            ).upper()
            if end_discussion_input == "YES":
                print("Discussion ended.")
                break
        else:
            input("Press Enter to pass turn to the next player in discussion...")

        # Check max turns reached
        if all(
            game_state.discussion_turn_counts.get(name, 0)
            >= game_state.max_discussion_turns_per_player
            for name in game_state.player_names
            if game_state.player_status[name] == "alive"
        ):
            print("Maximum discussion turns reached.")
            break
        # Check if game ended during discussion
        if game_state.game_over:
            # End discussion if game is over
            break


def play_secret_hitler():
    """Plays a game of Secret Hitler in text-based mode."""
    player_names = []
    num_players = 0
    while num_players < 5 or num_players > 10:
        num_players = int(
            get_player_input(
                "Enter the number of players (5-10): ", input_type="int")
        )
        if not (5 <= num_players <= 10):
            print("Invalid number of players. Must be between 5 and 10.")
    for i in range(num_players):
        name = get_player_input(f"Enter name for Player {i+1}: ")
        player_names.append(name)

    game_state = GameState(player_names)

    print("\nRoles have been assigned.")
    for player in player_names:
        input(
            f"{player}, press Enter to see YOUR ROLE **PRIVATELY** (without showing others)..."
        )
        role = get_player_role(game_state, player)
        print(f"Your role is: {role}")
        if role == "Fascist" or role == "Hitler":
            fascists = [
                name for name, r in game_state.roles.items() if r in ("Fascist", "Hitler")
            ]
            # Fascists know each other
            print(f"The Fascists are: {', '.join(fascists)}")
            if role == "Fascist" and game_state.num_players >= 7:
                # Fascists know Hitler from 7+ players
                print(
                    f"Hitler is: {[name for name, r in game_state.roles.items() if r == 'Hitler'][0]}"
                )
        input("Press Enter to continue...")
        # Clear screen
        print("\n" * 50)

    while not game_state.game_over:
        display_game_state(game_state, game_state.get_president())

        # Nomination Phase
        president_name = game_state.get_president()
        print(f"\n--- Nomination Phase ---")
        # Discussion before nomination
        play_discussion_phase(game_state, "Nomination")

        while True:
            nominee_name = get_player_input(
                f"{president_name}, nominate a Chancellor: "
            )
            if nominee_name not in get_player_names(game_state):
                print("Invalid nominee name.")
            elif game_state.player_status[nominee_name] == "dead":
                print("Cannot nominate a dead player.")
            elif not is_valid_chancellor_nominee(
                game_state, president_name, nominee_name
            ):
                print(
                    "Invalid nominee. Cannot nominate yourself or the previous Chancellor (and President in 7+ player games if applicable)."
                )

            else:
                break

        game_state.set_government(president_name, nominee_name)
        print(f"{president_name} has nominated {nominee_name} as Chancellor.")

        # Election Phase
        print("\n--- Election Phase ---")
        # Discussion before voting
        play_discussion_phase(game_state, "Election")

        votes = {}
        for player in get_player_names(game_state):
            # Only living players vote
            if game_state.player_status[player] == "alive":
                vote = get_player_input(
                    f"{player}, vote YES or NO on the government ({president_name} as President, {nominee_name} as Chancellor): ",
                    valid_options=["YES", "NO"],
                ).upper()
                votes[player] = vote

        # Majority yes votes
        government_approved = (
            list(votes.values()).count("YES") > list(
                votes.values()).count("NO")
        )

        print("\n--- Vote Results ---")
        for player, vote in votes.items():
            print(f"{player} voted {vote}")

        if government_approved:
            print("Government approved!")
            # Reset election tracker
            game_state.election_tracker = 0
            # Reset consecutive failed elections
            game_state.consecutive_failed_elections = 0

            # Legislative Session - President draws, President discards, Chancellor enacts
            print("\n--- Legislative Session ---")
            policy_cards = game_state.draw_policies(3)
            # Private information for President about drawn policies
            private_info_pres = {
                president_name: f"Drew policies: {policy_cards}"}
            game_state.log_event(
                president_name, f"Drew 3 policies.", private_info=private_info_pres
            )

            print(
                f"{president_name}, you drew policies: {policy_cards} **LOOK AT THESE PRIVATELY**")
            while True:
                discard1 = get_player_input(
                    f"{president_name}, discard one policy (enter 1, 2, or 3): ",
                    valid_options=[1, 2, 3],
                    input_type="int",
                )
                # Ensure discard1 is int before indexing
                if 1 <= int(discard1) <= 3:
                    discard_index = int(discard1) - 1
                    discarded_policy_pres = policy_cards.pop(discard_index)
                    game_state.discard_policy(discarded_policy_pres)
                    # Private information for President about discarded policy
                    private_info_pres_discard = {
                        president_name: f"Discarded policy at index {discard_index+1} (which was: {discarded_policy_pres}). Remaining policies passed to Chancellor: {policy_cards}"
                    }
                    game_state.log_event(
                        president_name,
                        f"Discarded a policy. Passed 2 to Chancellor.",
                        private_info=private_info_pres_discard,
                    )
                    break
                else:
                    print("Invalid choice.")

            print(
                f"{president_name} discarded a policy. Remaining policies: {policy_cards} **PASS THESE TO CHANCELLOR PRIVATELY (SYMBOLICALLY)**"
            )
            input(
                f"Pass the remaining policies to {nominee_name} (Chancellor). Press Enter..."
            )

            # Private information for Chancellor about received policies
            private_info_chan = {
                nominee_name: f"Received policies: {policy_cards}"}
            game_state.log_event(
                nominee_name, f"Received 2 policies.", private_info=private_info_chan
            )
            print(
                f"\n{nominee_name}, you received policies: {policy_cards} **LOOK AT THESE PRIVATELY**")
            # Initialize outside if/else blocks
            policy_to_enact = None

            # Veto power check
            if game_state.veto_power_available:
                veto_option = get_player_input(
                    f"{nominee_name}, do you want to VETO? (YES/NO): ",
                    valid_options=["YES", "NO"],
                ).upper()
                if veto_option == "YES":
                    # Double check with President for veto confirmation
                    if game_state.veto_power_available:
                        veto_president_confirm = get_player_input(
                            f"{president_name}, Chancellor wants to VETO. Confirm VETO? (YES/NO): ",
                            valid_options=["YES", "NO"],
                        ).upper()
                        if veto_president_confirm == "YES":
                            print("Government VETOED!")
                            game_state.log_event(None, "Government vetoed.")
                            # Reset government on veto
                            game_state.reset_government()
                            # Election tracker +1
                            game_state.increment_election_tracker()
                            # Skip to next president nomination
                            game_state.next_president()
                            continue
                        else:
                            # Fall through to policy enactment if veto rejected
                            print(
                                "President rejected VETO. Chancellor must enact policy.")
                    else:
                        # Fall through to policy enactment
                        print(
                            "Veto power not available (anymore - should not happen). Enacting policy."
                        )

            # Enact policy if no veto or veto failed
            if (
                not game_state.veto_power_available
                or veto_option.upper() != "YES"
                or veto_president_confirm.upper() != "YES"
            ):
                while True:
                    enact_policy_choice = get_player_input(
                        f"{nominee_name}, enact Liberal or Fascist policy? (1 for Liberal, 2 for Fascist): ",
                        valid_options=[1, 2],
                        input_type="int",
                    )
                    if enact_policy_choice == 1:
                        policy_to_enact = "Liberal"
                        if "Liberal" in policy_cards:
                            policy_cards.remove("Liberal")
                            game_state.discard_policy(policy_cards[0])
                            break
                        else:
                            print(
                                "Invalid choice. No Liberal policy available in hand.")
                    elif enact_policy_choice == 2:
                        policy_to_enact = "Fascist"
                        if "Fascist" in policy_cards:
                            policy_cards.remove("Fascist")
                            break
                        else:
                            print(
                                "Invalid choice. No Fascist policy available in hand.")
                    else:
                        print("Invalid choice.")

                enacted_policy = policy_to_enact
                game_state.enact_policy(enacted_policy)
                # Reset government after policy enactment
                game_state.reset_government()

            # Executive Actions (Presidential Powers) - After Fascist Policies
            if game_state.fascist_policies_enacted == 3 and game_state.num_players >= 5:
                print("\nPresidential Power: Investigate Loyalty")
                target_player = get_player_input(
                    f"{president_name}, investigate loyalty of which player?: "
                )
                if target_player in get_player_names(game_state):
                    # Added checks for valid investigation target
                    if (
                        target_player not in game_state.investigated_players
                        and game_state.player_status[target_player] == "alive"
                        and target_player != president_name
                    ):
                        # Use engine function to investigate player
                        membership = investigate_player(
                            game_state, president_name, target_player
                        )
                        # Ensure investigation was successful
                        if membership:
                            # Private information for President about investigation result
                            private_info_investigate = {
                                president_name: f"Investigated {target_player}. Membership Card: {membership}"
                            }
                            game_state.log_event(
                                president_name,
                                f"Investigated loyalty of {target_player}.",
                                private_info=private_info_investigate,
                            )
                            # Clarification of membership card reveal
                            print(
                                f"{target_player}'s Membership Card is revealed to **YOU PRIVATELY** as: {membership} (Note: In Secret Hitler all membership cards are Fascist)"
                            )
                            input("Press Enter to continue...")
                        else:
                            # Feedback for invalid investigation target
                            print(
                                "Invalid investigation target (already investigated, dead, or self). No action taken."
                            )
                    else:
                        # More descriptive message for invalid target
                        print(
                            "Invalid investigation target (already investigated, dead, or self). No action taken."
                        )
                else:
                    print("Invalid player name.")

            elif game_state.fascist_policies_enacted == 4 and game_state.num_players >= 7:
                print("\nPresidential Power: Special Election")
                target_president = get_player_input(
                    f"{president_name}, choose the next President (Special Election): "
                )
                if target_president in get_player_names(game_state):
                    # Fixed variable name from target_player_execute to target_president
                    if (
                        target_president != president_name
                        and game_state.player_status[target_president] == "alive"
                    ):
                        # Use engine function to call special election
                        if call_special_election(
                            game_state, president_name, target_president
                        ):
                            print(
                                f"Next President will be {target_president} after your term.")
                            input("Press Enter to continue...")
                        else:
                            print(
                                "Special Election call failed (invalid target). No action taken."
                            )
                    else:
                        print(
                            "Invalid special election target (self or dead). No action taken."
                        )
                else:
                    print("Invalid player name.")

            elif game_state.fascist_policies_enacted == 5 and game_state.num_players >= 9:
                print("\nPresidential Power: Policy Peek")
                # Use engine function for policy peek
                peeked_policies = policy_peek(
                    game_state, president_name
                )
                # Ensure peek was successful
                if peeked_policies:
                    # Private information for President about peeked policies
                    private_info_peek = {
                        president_name: f"Peeked at top 3 policies: {peeked_policies}"
                    }
                    game_state.log_event(
                        president_name, "Used Policy Peek power.", private_info=private_info_peek
                    )
                    print(
                        f"{president_name}, you peek at the top 3 policies **PRIVATELY**: {peeked_policies}"
                    )
                    input("Press Enter to continue...")
                else:
                    # Feedback for failed policy peek
                    print(
                        "Policy peek failed (no policies in deck to peek at). No action taken."
                    )

            elif game_state.fascist_policies_enacted >= 4 and game_state.num_players >= 5:
                # Execute power at 6 policies for 5-6 players, else from 4
                if (
                    game_state.fascist_policies_enacted >= 6
                    or game_state.num_players >= 7
                ):
                    print("\nPresidential Power: Execution")
                    target_player_execute = get_player_input(
                        f"{president_name}, execute which player?: "
                    )
                    if target_player_execute in get_player_names(game_state):
                        # Use engine's kill_player function for execution
                        if kill_player(
                            game_state, target_player_execute
                        ):
                            game_state.log_event(
                                president_name, f"Executed player {target_player_execute}."
                            )
                        else:
                            # Feedback for failed execution
                            print(
                                "Execution failed (player already dead). No action taken."
                            )
                    else:
                        print("Invalid player name.")

            # Check if Hitler was elected Chancellor after 3 Fascist policies
            if (
                game_state.government["chancellor"]
                and game_state.fascist_policies_enacted >= 3
                and game_state.roles[game_state.government["chancellor"]] == "Hitler"
                and not game_state.hitler_revealed
            ):
                print("\nHitler elected as Chancellor after 3 Fascist policies!")
                reveal_hitler(game_state)
                # Check game end conditions after Hitler reveal
                game_state.check_game_end_conditions()

        else:
            # Government not approved
            print("Government failed!")
            # Reset government on failed vote
            game_state.reset_government()
            # Election tracker +1
            game_state.increment_election_tracker()

        if not game_state.game_over:
            # Special election president becomes the next president
            if game_state.special_election_president:
                # Set president index to special election president
                game_state.current_president_index = game_state.player_names.index(
                    game_state.special_election_president
                )
                # Reset special election president
                game_state.special_election_president = None
                print(
                    f"\nSpecial Election! {game_state.get_president()} is the new President.")
            else:
                # Move to next president in rotation
                game_state.next_president()

            # Clear screen for next round
            input("\nPress Enter to start the next round...")
            print("\n" * 50)

    # Game Over sequence
    display_game_state(game_state)
    print("\n================ Game Over! ================")
    print(f"Winner: {game_state.winner}!")
    print("\n--- Roles ---")
    for name, role in game_state.roles.items():
        print(f"{name}: {role}")
    print("\n--- Game Log ---")
    for event in game_state.public_game_log:
        print(f"- {event}")

    # Display private logs at the end of the game
    print("\n--- Private Game Logs ---")
    for player_name in game_state.player_names:
        print(f"\n** {player_name}'s Private Log **")
        for event in game_state.private_game_logs[player_name]:
            print(f"- {event}")


if __name__ == "__main__":
    play_secret_hitler()

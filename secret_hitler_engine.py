# secret_hitler_engine.py
"""Engine for the Secret Hitler game, managing game state and logic."""

import random


class GameState:
    """Represents the state of a Secret Hitler game."""

    def __init__(self, player_names, use_ai_players=False):
        """Initializes the game state.

        Args:
            player_names: A list of player names (strings).
            use_ai_players: A boolean flag indicating if AI players are used.
        """
        self.player_names = player_names
        self.num_players = len(player_names)
        # Flag to indicate if AI players are used (currently unused)
        self.use_ai_players = use_ai_players
        # Assign roles to players
        self.roles = self.assign_roles()
        # Create the policy deck
        self.policy_deck = self.create_policy_deck()
        # Initialize the policy discard pile
        self.policy_discard_pile = []
        # Track number of enacted liberal policies
        self.liberal_policies_enacted = 0
        # Track number of enacted fascist policies
        self.fascist_policies_enacted = 0
        # Initialize the election tracker
        self.election_tracker = 0
        # Initialize the government (President and Chancellor)
        self.government = {"president": None, "chancellor": None}
        # List of previous governments (President, Chancellor tuples)
        self.previous_governments = []
        # Order of presidents in the game
        self.president_order = player_names[:]
        # Index of the current president in president_order
        self.current_president_index = 0
        # Track term-limited chancellor (ineligible for next chancellorship)
        self.term_limited_chancellor = None
        # Track term-limited president (ineligible for next chancellorship in 7+ player games)
        self.term_limited_president = None
        # Flag to indicate if Hitler's identity has been revealed
        self.hitler_revealed = False
        # Flag to indicate if the game is over
        self.game_over = False
        # Stores the winner of the game ("Liberals" or "Fascists")
        self.winner = None
        # Dictionary to track player status ('alive' or 'dead')
        self.player_status = {name: "alive" for name in player_names}
        # Assign party membership cards (all 'Fascist' in this version)
        self.player_membership_cards = self.assign_party_membership()
        # Set to track players who have been investigated
        self.investigated_players = set()
        # Name of the president chosen by special election (for next round)
        self.special_election_president = None
        # Flag to indicate if veto power is available (after 5 fascist policies)
        self.veto_power_available = False
        # Counter for consecutive failed elections
        self.consecutive_failed_elections = 0
        # List to store public game log events
        self.public_game_log = []
        # Dictionary to store private game logs for each player
        self.private_game_logs = {name: [] for name in player_names}
        # Track the current game phase (e.g., "Nomination", "Election") for discussions
        self.current_phase = "Nomination"
        # List to store discussion messages in the current phase
        self.discussion_history = []
        # Index to track whose turn it is in discussion
        self.discussion_turn_order_index = 0
        # Maximum discussion turns per player before discussion can be ended
        self.max_discussion_turns_per_player = 2
        # Dictionary to track discussion turns per player
        self.discussion_turn_counts = {
            name: 0 for name in player_names if name in self.player_names
        }

    def assign_roles(self):
        """Assigns roles to players based on the number of players.

        Roles are distributed according to the Secret Hitler game rules.

        Returns:
            A dictionary mapping player names to their roles.
        """
        roles_distribution = {
            5: 1 * ["Fascist"] + ["Hitler"] + 3 * ["Liberal"],
            6: 1 * ["Fascist"] + ["Hitler"] + 4 * ["Liberal"],
            7: 2 * ["Fascist"] + ["Hitler"] + 4 * ["Liberal"],
            8: 2 * ["Fascist"] + ["Hitler"] + 5 * ["Liberal"],
            9: 3 * ["Fascist"] + ["Hitler"] + 5 * ["Liberal"],
            10: 3 * ["Fascist"] + ["Hitler"] + 6 * ["Liberal"],
        }
        # Create a copy to avoid modifying the original distribution
        roles = roles_distribution[self.num_players][:]
        random.shuffle(roles)
        return dict(zip(self.player_names, roles))

    def assign_party_membership(self):
        """Assigns party membership cards (all 'Fascist' in this version).

        In the Secret Hitler game, all membership cards are visually 'Fascist'.
        Only the secret role cards differentiate between Liberals, Fascists, and Hitler.

        Returns:
            A dictionary mapping player names to 'Fascist' membership.
        """
        return {name: "Fascist" for name in self.player_names}

    def create_policy_deck(self):
        """Creates the policy deck with 6 Liberal and 11 Fascist policies.

        Returns:
            A list representing the shuffled policy deck.
        """
        # Correct policy card counts: 6 Liberal, 11 Fascist
        deck = ["Liberal"] * 6 + ["Fascist"] * 11
        random.shuffle(deck)
        return deck

    def draw_policies(self, num):
        """Draws a specified number of policies from the deck.

        Reshuffles the discard pile into the deck if the deck runs out.

        Args:
            num: The number of policies to draw.

        Returns:
            A list of drawn policy cards (strings).
        """
        drawn_policies = []
        for _ in range(num):
            if not self.policy_deck:
                # Reshuffle discard pile if deck is empty
                self.policy_deck = self.policy_discard_pile[:]
                self.policy_discard_pile = []
                random.shuffle(self.policy_deck)
                # Log reshuffle event
                self.log_event(None, "Policy deck reshuffled.")
            if self.policy_deck:
                # Make sure deck isn't empty after reshuffle
                drawn_policies.append(self.policy_deck.pop())
            else:
                # Handle case where deck is empty after reshuffle
                break
        return drawn_policies

    def discard_policy(self, policy):
        """Discards a policy card to the discard pile.

        Args:
            policy: The policy card ('Liberal' or 'Fascist') to discard.
        """
        self.policy_discard_pile.append(policy)
        # Log policy discard event (private to president)
        self.log_event(None, f"Policy discarded.", private_info={
                       self.get_president(): f"You discarded a {policy} policy."})

    def enact_policy(self, policy):
        """Enacts a policy and updates the game state.

        Checks for game end conditions after enacting a policy.

        Args:
            policy: The policy card to enact ('Liberal' or 'Fascist').
        """
        if policy == "Liberal":
            self.liberal_policies_enacted += 1
            # Log liberal policy enacted
            self.log_event(
                None,
                f"Liberal policy enacted. Liberal policies: {self.liberal_policies_enacted}",
                # Example of chancellor private log
                private_info={
                    self.government['chancellor']: "You enacted a Liberal policy."}
            )
        elif policy == "Fascist":
            self.fascist_policies_enacted += 1
            # Log fascist policy enacted
            self.log_event(
                None,
                f"Fascist policy enacted. Fascist policies: {self.fascist_policies_enacted}",
                # Example of chancellor private log
                private_info={
                    self.government['chancellor']: "You enacted a Fascist policy."}
            )
            # Veto power becomes available after 5 fascist policies
            if self.fascist_policies_enacted >= 5:
                self.veto_power_available = True
        self.check_game_end_conditions()

    def check_game_end_conditions(self):
        """Checks if any game end conditions are met and sets game_over and winner."""
        # Liberals win if 5 liberal policies are enacted
        if self.liberal_policies_enacted >= 5:
            self.game_over = True
            self.winner = "Liberals"
            self.log_event(
                None, "Liberals win by enacting 5 Liberal policies.")
        # Fascists win if 6 fascist policies are enacted
        if self.fascist_policies_enacted >= 6:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(
                None, "Fascists win by enacting 6 Fascist policies.")
        # Fascists win if Hitler is elected Chancellor after 3 fascist policies
        if (
            self.fascist_policies_enacted >= 3
            and self.government["chancellor"]
            and self.roles[self.government["chancellor"]] == "Hitler"
        ):
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(
                None,
                "Fascists win by electing Hitler as Chancellor after 3 Fascist policies.",
            )
        # Fascists win if 3 consecutive governments fail (chaos win)
        if self.consecutive_failed_elections >= 3:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win due to 3 failed elections.")

    def get_president(self):
        """Returns the name of the current president.

        Returns:
            The name of the current president (string).
        """
        return self.president_order[self.current_president_index % self.num_players]

    def next_president(self):
        """Moves to the next president in the president order."""
        self.current_president_index += 1
        # Reset special election president after presidency changes
        self.special_election_president = None

    def set_government(self, president_name, chancellor_name):
        """Sets the president and chancellor for the current government.

        Args:
            president_name: Name of the president.
            chancellor_name: Name of the chancellor.
        """
        self.government["president"] = president_name
        self.government["chancellor"] = chancellor_name
        # Log government nomination event
        self.log_event(
            None,
            f"Government nominated: President {president_name}, Chancellor {chancellor_name}",
        )

    def reset_government(self):
        """Resets the government, increments failed election counter, and checks for chaos policy."""
        if self.government["president"] and self.government["chancellor"]:
            self.previous_governments.append(
                (self.government["president"], self.government["chancellor"])
            )
            # Set term limits for previous president and chancellor
            self.term_limited_president = self.government["president"]
            self.term_limited_chancellor = self.government["chancellor"]
        self.government = {"president": None, "chancellor": None}
        # Increment consecutive failed elections counter
        self.consecutive_failed_elections += 1
        # Check if chaos policy should be enacted due to failed elections
        if self.consecutive_failed_elections >= 3:
            self.enact_chaos_policy()
            # Reset failed election counter after chaos policy
            self.consecutive_failed_elections = 0

    def enact_chaos_policy(self):
        """Enacts policy from top of deck due to 3 failed elections (chaos policy)."""
        self.log_event(None, "Three failed elections! Chaos policy enacted.")
        # Draw one policy from top of deck
        top_policy = self.draw_policies(1)[0]
        self.enact_policy(top_policy)
        # Reset election tracker after chaos policy enacted
        self.election_tracker = 0
        # Term limits are forgotten after chaos policy
        self.term_limited_chancellor = None
        # Term limits are forgotten after chaos policy
        self.term_limited_president = None
        # Log chaos policy type
        self.log_event(None, f"Chaos policy enacted was {top_policy}.")

    def increment_election_tracker(self):
        """Increments the election tracker.

        If tracker reaches 3, enacts top policy and resets tracker.
        """
        # Only increment if chaos policy not already enacted
        if self.consecutive_failed_elections < 3:
            self.election_tracker += 1
            # If tracker reaches 3, enact top policy and reset
            if self.election_tracker >= 3:  # Changed from > to >= to enact at 3
                # Draw one policy from top of deck
                top_policy = self.draw_policies(1)[0]
                self.enact_policy(top_policy)
                # Reset election tracker after policy enacted
                self.election_tracker = 0
                # Log election tracker maxed event
                self.log_event(
                    None, f"Election Tracker reached 3! Top policy enacted.")
            else:
                # Log election tracker increment event
                self.log_event(
                    None,
                    f"Government failed. Election tracker is now {self.election_tracker}.",
                )
            self.check_game_end_conditions()

    def log_event(self, player_name, event_description, private_info=None):
        """Logs an event to public and private logs.

        Args:
            player_name: Name of the player initiating the event (or None for system events).
            event_description: Public description of the event.
            private_info: Optional dictionary of player names to private information.
                          Keys should be player names, values are private messages.
        """
        # Basic round counter for log entry prefix
        log_entry = (
            f"Round {len(self.public_game_log) + 1 if not self.game_over else 'End'} - "
        )
        if player_name:
            log_entry += f"{player_name}: "
        log_entry += event_description
        self.public_game_log.append(log_entry)

        # Add to private logs if private_info is provided
        for name in self.player_names:
            # Start with the public log entry
            private_log_entry = log_entry
            if private_info and name in private_info:
                # Append private information if it exists for this player
                private_log_entry += f" (Private: {private_info[name]})"
            self.private_game_logs[name].append(private_log_entry)

    def get_game_state_for_player(self, player_name):
        """Returns a simplified game state view for a specific player.

        Used to provide AI players with necessary game information without revealing
        hidden roles to other players.

        Args:
            player_name: The name of the player requesting the game state.

        Returns:
            A dictionary representing the game state visible to the player.
        """
        visible_state = {
            "player_names": self.player_names,
            "num_players": self.num_players,
            "liberal_policies": self.liberal_policies_enacted,
            "fascist_policies": self.fascist_policies_enacted,
            "election_tracker": self.election_tracker,
            "government": self.government,
            "previous_governments": self.previous_governments,
            "current_president": self.get_president(),
            "player_status": self.player_status,
            "game_over": self.game_over,
            "winner": self.winner,
            "public_log": self.public_game_log,
            "discussion_history": self.discussion_history,
            "current_phase": self.current_phase,
            "veto_power_available": self.veto_power_available,
            # Convert set to list for JSON serializability if needed
            "investigated_players": list(self.investigated_players),
        }
        # Reveal fascist player list and hitler name to fascists and hitler
        if (
            self.roles[player_name] == "Fascist"
            or self.roles[player_name] == "Hitler"
        ):
            visible_state["fascist_players"] = [
                name
                for name, role in self.roles.items()
                if role in ("Fascist", "Hitler")
            ]
            if self.fascist_policies_enacted >= 3:
                visible_state["hitler_name"] = [
                    name for name, role in self.roles.items() if role == "Hitler"
                ][0]
        # Add player's own role to their visible state
        visible_state["my_role"] = self.roles[player_name]
        return visible_state

    def get_full_game_state(self):
        """Returns the full game state for debugging or replay purposes.

        Includes all hidden information like roles and policy deck.

        Returns:
            A dictionary representing the complete game state.
        """
        full_state = {
            "player_names": self.player_names,
            "num_players": self.num_players,
            "roles": self.roles,
            # Just show deck size for brevity, can show full deck for deeper debug
            "policy_deck": len(self.policy_deck),
            "policy_discard_pile": len(self.policy_discard_pile),
            "liberal_policies": self.liberal_policies_enacted,
            "fascist_policies": self.fascist_policies_enacted,
            "election_tracker": self.election_tracker,
            "government": self.government,
            "previous_governments": self.previous_governments,
            "president_order": self.president_order,
            "current_president_index": self.current_president_index,
            "term_limited_chancellor": self.term_limited_chancellor,
            "term_limited_president": self.term_limited_president,
            "hitler_revealed": self.hitler_revealed,
            "game_over": self.game_over,
            "winner": self.winner,
            "player_status": self.player_status,
            "public_game_log": self.public_game_log,
            "private_game_logs": self.private_game_logs,
            "discussion_history": self.discussion_history,
            "current_phase": self.current_phase,
            "veto_power_available": self.veto_power_available,
            "investigated_players": list(self.investigated_players),
            "special_election_president": self.special_election_president,
            "consecutive_failed_elections": self.consecutive_failed_elections,
        }
        return full_state

    def start_discussion(self, phase):
        """Starts a discussion phase for a given game phase.

        Resets discussion history and turn tracking for the new phase.

        Args:
            phase: The name of the discussion phase (e.g., "Nomination").
        """
        self.current_phase = phase
        # Clear discussion history for new phase
        self.discussion_history = []
        self.discussion_turn_order_index = 0
        # Reset turn counts for new discussion phase
        self.discussion_turn_counts = {
            name: 0
            for name in self.player_names
            if name in self.player_names and self.player_status[name] == "alive"
        }

    def get_current_discussion_speaker(self):
        """Gets the name of the player whose turn it is to speak in discussion.

        Determines the speaker based on president order and discussion turn index.

        Returns:
            The name of the current speaker (string) or None if no alive players.
        """
        # Get only alive players for discussion turn order
        alive_players = [
            player for player in self.player_names if self.player_status[player] == "alive"
        ]
        # No alive players left to speak
        if not alive_players:
            return None

        current_president_alive_index = -1
        for i, player in enumerate(alive_players):
            if player == self.get_president():
                current_president_alive_index = i
                break

        # President is dead, find index of next alive player as starting point
        if current_president_alive_index == -1:
            # Default to first alive player if president is dead
            current_president_alive_index = 0

        speaker_index_relative_to_president = self.discussion_turn_order_index
        speaker_index_in_alive_players = (
            current_president_alive_index + speaker_index_relative_to_president
        ) % len(alive_players)

        return alive_players[speaker_index_in_alive_players]

    def record_discussion_message(self, player_name, message_text):
        """Records a discussion message, updates history, and logs the event."""
        message = f"{player_name}: {message_text}"
        self.discussion_history.append(message)
        # Log publicly and to all private logs
        self.log_event(None, f"Discussion: {message}")
        self.discussion_turn_order_index += 1
        self.discussion_turn_counts[player_name] += 1

    def can_end_discussion(self, by_president=False):
        """Checks if the discussion phase can be ended.

        Discussion can be ended by the president or after all alive players have spoken.

        Args:
            by_president: True if the president is trying to end discussion.

        Returns:
            True if discussion can be ended, False otherwise.
        """
        # Need at least one message in discussion to end it
        if not self.discussion_history:
            return False
        # President can end discussion at any point after at least one message
        if by_president:
            return True
        # Check if all alive players have had at least one turn to speak
        alive_players = [
            name for name in self.player_names if self.player_status[name] == "alive"
        ]
        # Use get with default 0 to handle players who haven't spoken yet
        all_alive_players_spoke_once = all(
            self.discussion_turn_counts.get(player, 0) >= 1 for player in alive_players
        )
        # Only require all alive players to speak if more than one alive player
        if all_alive_players_spoke_once and len(alive_players) > 1:
            return True

        # Check if max turns reached by all alive players (optional condition)
        max_turns_reached = all(
            self.discussion_turn_counts.get(player, 0)
            >= self.max_discussion_turns_per_player
            for player in self.player_names
            if self.player_status[player] == "alive"
        )
        if max_turns_reached:
            return True
        return False

    def get_discussion_summary(self):
        """Returns a summary of the discussion history as a single string.

        Returns:
            A string containing all discussion messages, each on a new line.
        """
        return "\n".join(self.discussion_history)


def is_valid_chancellor_nominee(game_state, president_name, nominee_name):
    """Checks if a player is a valid chancellor nominee.

    A player cannot be nominated if they are the president, dead,
    the term-limited chancellor, or the term-limited president (in 7+ player games).

    Args:
        game_state: The current game state object.
        president_name: Name of the current president.
        nominee_name: Name of the proposed chancellor nominee.

    Returns:
        True if the nominee is valid, False otherwise.
    """
    # President cannot nominate themselves as chancellor
    if nominee_name == president_name:
        return False
    # Cannot nominate a dead player as chancellor
    if game_state.player_status[nominee_name] == "dead":
        return False
    # Cannot nominate the term-limited chancellor
    if nominee_name == game_state.term_limited_chancellor:
        return False
    # In 7+ player games, cannot nominate the term-limited president as chancellor
    if (
        game_state.num_players >= 7 and nominee_name == game_state.term_limited_president
    ):
        return False
    return True


def get_player_role(game_state, player_name):
    """Returns the secret role of a player.

    Args:
        game_state: The current game state object.
        player_name: Name of the player.

    Returns:
        The role of the player (string).
    """
    return game_state.roles[player_name]


def get_player_names(game_state):
    """Returns a list of all player names in the game.

    Args:
        game_state: The current game state object.

    Returns:
        A list of player names (strings).
    """
    return game_state.player_names


def kill_player(game_state, player_name):
    """Kills a player, removing them from the game.

    Checks if the killed player is Hitler, and updates game state accordingly.

    Args:
        game_state: The current game state object.
        player_name: Name of the player to kill.

    Returns:
        True if the player was successfully killed, False if player was already dead.
    """
    # Prevent killing a player who is already dead
    if game_state.player_status[player_name] == "dead":
        return False
    game_state.player_status[player_name] = "dead"
    # Log player execution event
    game_state.log_event(None, f"{player_name} has been executed.")
    if game_state.roles[player_name] == "Hitler":
        game_state.game_over = True
        game_state.winner = "Liberals"
        # Log hitler execution win event
        game_state.log_event(None, "Liberals win! Hitler has been executed.")
        # Double check game end conditions after killing player
        game_state.check_game_end_conditions()
    return True


def reveal_hitler(game_state):
    """Reveals Hitler's identity to all players.

    Sets the hitler_revealed flag and logs the event.

    Args:
        game_state: The current game state object.
    """
    game_state.hitler_revealed = True
    # Log hitler reveal event
    game_state.log_event(None, "Hitler's identity is now revealed.")


def investigate_player(game_state, president_name, target_player_name):
    """Investigates a player's party membership.

    Only usable once per player per game.

    Args:
        game_state: The current game state object.
        president_name: Name of the president using the power.
        target_player_name: Name of the player to investigate.

    Returns:
        The membership card of the investigated player ('Fascist' in this version),
        or None if the investigation is invalid (player already investigated, dead, etc.).
    """
    # Cannot investigate a player who has already been investigated
    if target_player_name in game_state.investigated_players:
        return None
    # Cannot investigate a dead player
    if game_state.player_status[target_player_name] == "dead":
        return None
    # President cannot investigate themselves
    if president_name == target_player_name:
        return None

    # Mark player as investigated
    game_state.investigated_players.add(target_player_name)
    # Return membership card of the investigated player
    return game_state.player_membership_cards[target_player_name]


def call_special_election(game_state, president_name, target_player_name):
    """Calls a special election, setting the next president.

    Args:
        game_state: The current game state object.
        president_name: Name of the president using the power.
        target_player_name: Name of the player to be the next president.

    Returns:
        True if special election was successful, False if target is invalid.
    """
    # Cannot choose a dead player for special election
    if game_state.player_status[target_player_name] == "dead":
        return False
    # President cannot choose themselves for special election
    if president_name == target_player_name:
        return False

    # Set the special election president for the next round
    game_state.special_election_president = target_player_name
    # Log special election call event
    game_state.log_event(
        president_name, f"Called special election. {target_player_name} will be next president."
    )
    return True


def policy_peek(game_state, president_name):
    """Allows the president to peek at the top 3 policies in the deck.

    Args:
        game_state: The current game state object.
        president_name: Name of the president using the power.

    Returns:
        A list of the top 3 policy cards (strings), or an empty list if deck is empty.
    """
    top_policies = game_state.draw_policies(3)
    # Handle case where deck is empty and no policies can be peeked
    if not top_policies:
        return []
    # Put the peeked policies back on top of the deck in the same order
    game_state.policy_deck = top_policies + game_state.policy_deck
    # Return the list of peeked policies
    return top_policies


def enact_top_policy_chaos(game_state):
    """Enacts the top policy from the deck due to chaos (election tracker).

    Args:
        game_state: The current game state object.

    Returns:
        The enacted policy card (string), or None if no policy was enacted.
    """
    top_policy = game_state.draw_policies(1)
    # Only enact if there's a policy to draw from the deck
    if top_policy:
        game_state.enact_policy(top_policy[0])
        # Return the enacted policy card
        return top_policy[0]
    return None

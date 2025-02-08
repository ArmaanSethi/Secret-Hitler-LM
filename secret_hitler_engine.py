# secret_hitler_engine.py
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
        # Flag for AI players
        self.use_ai_players = use_ai_players
        self.roles = self.assign_roles()
        self.policy_deck = self.create_policy_deck()
        self.policy_discard_pile = []
        self.liberal_policies_enacted = 0
        self.fascist_policies_enacted = 0
        self.election_tracker = 0
        self.government = {"president": None, "chancellor": None}
        # List of tuples (President, Chancellor)
        self.previous_governments = []
        # Initial president order
        self.president_order = player_names[:]
        self.current_president_index = 0
        # Track term-limited chancellor
        self.term_limited_chancellor = None
        # Track term-limited president
        self.term_limited_president = None
        self.hitler_revealed = False
        self.game_over = False
        self.winner = None
        # 'alive' or 'dead'
        self.player_status = {name: "alive" for name in player_names}
        # For investigation power
        self.player_membership_cards = self.assign_party_membership()
        # Track players who have been investigated.
        self.investigated_players = set()
        # Track president chosen by special election.
        self.special_election_president = None
        # Veto becomes available after 5 fascist policies
        self.veto_power_available = False
        # Counter for consecutive failed elections
        self.consecutive_failed_elections = 0
        # Game log visible to all
        self.public_game_log = []
        # Private log for each player
        self.private_game_logs = {name: [] for name in player_names}
        # Track game phase for discussion triggers
        self.current_phase = "Nomination"
        # Store discussion messages in the current phase
        self.discussion_history = []
        # Track whose turn it is in discussion
        self.discussion_turn_order_index = 0
        # Limit discussion turns per player
        self.max_discussion_turns_per_player = 2
        # Track turns per player
        self.discussion_turn_counts = {
            name: 0 for name in player_names if name in self.player_names
        }

    def assign_roles(self):
        """Assigns roles to players based on the number of players."""
        roles_distribution = {
            5: ["Liberal"] * 3 + ["Fascist"] * 1 + ["Hitler"],
            # 1 Fascist + Hitler
            6: ["Liberal"] * 4 + ["Fascist"] * 1 + ["Hitler"],
            # 1 Fascist + Hitler
            7: ["Liberal"] * 4 + ["Fascist"] * 2 + ["Hitler"],
            # 2 Fascists + Hitler
            8: ["Liberal"] * 5 + ["Fascist"] * 2 + ["Hitler"],
            # 2 Fascists + Hitler
            9: ["Liberal"] * 5 + ["Fascist"] * 3 + ["Hitler"],
            # 3 Fascists + Hitler
            10: ["Liberal"] * 6 + ["Fascist"] * 3 + ["Hitler"],
            # 3 Fascists + Hitler
        }
        # Create a copy
        roles = roles_distribution[self.num_players][:]
        random.shuffle(roles)
        return dict(zip(self.player_names, roles))

    def assign_party_membership(self):
        """Assigns party membership cards (all 'Fascist' in this version)."""
        # In game all membership cards are fascist. Only roles differ
        return {name: "Fascist" for name in self.player_names}

    def create_policy_deck(self):
        """Creates the policy deck with 6 Liberal and 11 Fascist policies."""
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
                # Reshuffle if deck is empty
                self.policy_deck = self.policy_discard_pile[:]
                self.policy_discard_pile = []
                random.shuffle(self.policy_deck)
                # System event
                self.log_event(None, "Policy deck reshuffled.")
            if self.policy_deck:
                # Make sure deck isn't empty after reshuffle
                drawn_policies.append(self.policy_deck.pop())
            else:
                # Handle case where deck is empty after reshuffle
                break
        return drawn_policies

    def discard_policy(self, policy):
        """Discards a policy card."""
        self.policy_discard_pile.append(policy)
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
            self.log_event(
                None,
                f"Liberal policy enacted. Liberal policies: {self.liberal_policies_enacted}",
                private_info={
                    self.government['chancellor']: "You enacted a Liberal policy."}
            )
        elif policy == "Fascist":
            self.fascist_policies_enacted += 1
            self.log_event(
                None,
                f"Fascist policy enacted. Fascist policies: {self.fascist_policies_enacted}",
                private_info={
                    self.government['chancellor']: "You enacted a Fascist policy."}
            )
            # Veto power after 5 fascist policies
            if self.fascist_policies_enacted >= 5:
                self.veto_power_available = True
        self.check_game_end_conditions()

    def check_game_end_conditions(self):
        """Checks if any game end conditions are met."""
        # Liberals win with 5 liberal policies
        if self.liberal_policies_enacted >= 5:
            self.game_over = True
            self.winner = "Liberals"
            self.log_event(
                None, "Liberals win by enacting 5 Liberal policies.")
        if self.fascist_policies_enacted >= 6:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(
                None, "Fascists win by enacting 6 Fascist policies.")
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
        # Fascists win after 3 failed elections
        if self.consecutive_failed_elections >= 3:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win due to 3 failed elections.")

    def get_president(self):
        """Returns the name of the current president."""
        return self.president_order[self.current_president_index % self.num_players]

    def next_president(self):
        """Moves to the next president in the president order."""
        self.current_president_index += 1
        # Reset special election president
        self.special_election_president = None

    def set_government(self, president_name, chancellor_name):
        """Sets the president and chancellor for the current government.

        Args:
            president_name: Name of the president.
            chancellor_name: Name of the chancellor.
        """
        self.government["president"] = president_name
        self.government["chancellor"] = chancellor_name
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
            # Set term limits
            self.term_limited_president = self.government["president"]
            self.term_limited_chancellor = self.government["chancellor"]
        self.government = {"president": None, "chancellor": None}
        # Increment failed election count
        self.consecutive_failed_elections += 1
        # Check for chaos policy
        if self.consecutive_failed_elections >= 3:
            self.enact_chaos_policy()
            # Reset counter after chaos
            self.consecutive_failed_elections = 0

    def enact_chaos_policy(self):
        """Enacts policy from top of deck due to 3 failed elections (chaos policy)."""
        self.log_event(None, "Three failed elections! Chaos policy enacted.")
        # Draw one policy from top of deck
        top_policy = self.draw_policies(1)[0]
        self.enact_policy(top_policy)
        # Reset election tracker after chaos policy
        self.election_tracker = 0
        # Term limits are forgotten
        self.term_limited_chancellor = None
        # Term limits are forgotten
        self.term_limited_president = None
        self.log_event(None, f"Chaos policy enacted was {top_policy}.")

    def increment_election_tracker(self):
        """Increments the election tracker.

        If tracker reaches 3, enacts top policy and resets tracker.
        """
        # Only if chaos policy not enacted
        if self.consecutive_failed_elections < 3:
            self.election_tracker += 1
            # Tracker maxes at 3, then resets
            if self.election_tracker > 3:
                # Draw one policy from top of deck
                top_policy = self.draw_policies(1)[0]
                self.enact_policy(top_policy)
                # Reset after policy enacted
                self.election_tracker = 0
                self.log_event(
                    None, f"Election Tracker reached 3! Top policy enacted.")
            else:
                self.log_event(
                    None,
                    f"Government failed. Election tracker is now {self.election_tracker}.",
                )
            self.check_game_end_conditions()

    def log_event(self, player_name, event_description, private_info=None):
        """Logs an event to public and private logs.

        Args:
            player_name: Name of the player initiating the event (or None).
            event_description: Public description of the event.
            private_info: Optional dict of player names to private information.
        """
        # Basic round counter
        log_entry = (
            f"Round {len(self.public_game_log) + 1 if not self.game_over else 'End'} - "
        )
        if player_name:
            log_entry += f"{player_name}: "
        log_entry += event_description
        self.public_game_log.append(log_entry)

        for name in self.player_names:
            # Start with the public log
            private_log_entry = log_entry
            if private_info and name in private_info:
                private_log_entry += f" (Private: {private_info[name]})"
            self.private_game_logs[name].append(private_log_entry)

    def get_game_state_for_player(self, player_name):
        """Returns a simplified game state view for a specific player.

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
            # Convert set to list
            "investigated_players": list(self.investigated_players),
        }
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
        # Add player's own role
        visible_state["my_role"] = self.roles[player_name]
        return visible_state

    def get_full_game_state(self):
        """Returns the full game state for debugging or replay purposes.

        Returns:
            A dictionary representing the complete game state.
        """
        full_state = {
            "player_names": self.player_names,
            "num_players": self.num_players,
            "roles": self.roles,
            # Just show deck size
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
        """Starts a discussion phase.

        Args:
            phase: The name of the discussion phase (e.g., "Nomination").
        """
        self.current_phase = phase
        # Clear discussion history for new phase
        self.discussion_history = []
        self.discussion_turn_order_index = 0
        # Reset turn counts
        self.discussion_turn_counts = {
            name: 0
            for name in self.player_names
            if name in self.player_names and self.player_status[name] == "alive"
        }

    def get_current_discussion_speaker(self):
        """Gets the name of the player whose turn it is to speak in discussion.

        Returns:
            The name of the current speaker (string) or None if no alive players.
        """
        # Get alive players only for discussion turn order
        alive_players = [
            player for player in self.player_names if self.player_status[player] == "alive"
        ]
        # No alive players to speak
        if not alive_players:
            return None

        current_president_alive_index = -1
        for i, player in enumerate(alive_players):
            if player == self.get_president():
                current_president_alive_index = i
                break

        # President is dead, find next alive president
        if current_president_alive_index == -1:
            # Default to first alive player if president is dead
            current_president_alive_index = 0

        speaker_index_relative_to_president = self.discussion_turn_order_index
        speaker_index_in_alive_players = (
            current_president_alive_index + speaker_index_relative_to_president
        ) % len(alive_players)

        return alive_players[speaker_index_in_alive_players]

    def record_discussion_message(self, player_name, message_text):
        """Records a discussion message, updates history, and logs the event.

        Args:
            player_name: Name of the player sending the message.
            message_text: The text of the message.
        """
        message = f"{player_name}: {message_text}"
        self.discussion_history.append(message)
        # Log publicly
        self.log_event(player_name, f"Discussion: {message_text}")
        self.discussion_turn_order_index += 1
        self.discussion_turn_counts[player_name] += 1

    def can_end_discussion(self, by_president=False):
        """Checks if the discussion phase can be ended.

        Discussion can be ended by the president after at least one message,
        or after all alive players have spoken once (optional condition).

        Args:
            by_president: True if the president is trying to end discussion.

        Returns:
            True if discussion can be ended, False otherwise.
        """
        # Need at least one message
        if not self.discussion_history:
            return False
        # President can end after anyone speaks once
        if by_president:
            return True
        # Check if everyone alive has had at least one turn (optional)
        alive_players = [
            name for name in self.player_names if self.player_status[name] == "alive"
        ]
        # Use get with default 0
        all_alive_players_spoke_once = all(
            self.discussion_turn_counts.get(player, 0) >= 1 for player in alive_players
        )
        # Only require if > 1 alive
        if all_alive_players_spoke_once and len(alive_players) > 1:
            return True

        # Check for max turns reached by all alive players (optional)
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
        """Returns a summary of the discussion history as a single string."""
        return "\n".join(self.discussion_history)


def is_valid_chancellor_nominee(game_state, president_name, nominee_name):
    """Checks if a player is a valid chancellor nominee.

    A player cannot be nominated if they are the president, dead,
    the term-limited chancellor, or the term-limited president (in 7+ player games).

    Args:
        game_state: The current game state.
        president_name: Name of the current president.
        nominee_name: Name of the proposed chancellor nominee.

    Returns:
        True if the nominee is valid, False otherwise.
    """
    # President cannot nominate themselves
    if nominee_name == president_name:
        return False
    # Cannot nominate a dead player.
    if game_state.player_status[nominee_name] == "dead":
        return False
    # Cannot nominate term-limited chancellor
    if nominee_name == game_state.term_limited_chancellor:
        return False
    # Term limit for president only in 7+ player games
    if (
        game_state.num_players > 5 and nominee_name == game_state.term_limited_president
    ):
        return False
        # Cannot nominate term-limited president
    return True


def get_player_role(game_state, player_name):
    """Returns the role of a player.

    Args:
        game_state: The current game state.
        player_name: Name of the player.

    Returns:
        The role of the player (string).
    """
    return game_state.roles[player_name]


def get_player_names(game_state):
    """Returns a list of all player names in the game.

    Args:
        game_state: The current game state.

    Returns:
        A list of player names (strings).
    """
    return game_state.player_names


def kill_player(game_state, player_name):
    """Kills a player, removing them from the game.

    Checks if the killed player is Hitler, and updates game state accordingly.

    Args:
        game_state: The current game state.
        player_name: Name of the player to kill.

    Returns:
        True if the player was successfully killed, False if player was already dead.
    """
    # Prevent killing dead players
    if game_state.player_status[player_name] == "dead":
        return False
        # Indicate invalid action
    game_state.player_status[player_name] = "dead"
    game_state.log_event(None, f"{player_name} has been executed.")
    if game_state.roles[player_name] == "Hitler":
        game_state.game_over = True
        game_state.winner = "Liberals"
        game_state.log_event(None, "Liberals win! Hitler has been executed.")
        # Double check win conditions
        game_state.check_game_end_conditions()
    # Indicate successful kill
    return True


def reveal_hitler(game_state):
    """Reveals Hitler's identity to all players."""
    game_state.hitler_revealed = True
    game_state.log_event(None, "Hitler's identity is now revealed.")


def investigate_player(game_state, president_name, target_player_name):
    """Investigates a player's party membership.

    Only usable once per player per game.

    Args:
        game_state: The current game state.
        president_name: Name of the president using the power.
        target_player_name: Name of the player to investigate.

    Returns:
        The membership card of the investigated player ('Fascist' in this version),
        or None if the investigation is invalid.
    """
    # Already investigated
    if target_player_name in game_state.investigated_players:
        return None
        # No player may be investigated twice
    # Cannot investigate dead
    if game_state.player_status[target_player_name] == "dead":
        return None
    # Cannot investigate self.
    if president_name == target_player_name:
        return None

    # Mark as investigated
    game_state.investigated_players.add(target_player_name)
    # Return membership card
    return game_state.player_membership_cards[target_player_name]


def call_special_election(game_state, president_name, target_player_name):
    """Calls a special election, setting the next president.

    Args:
        game_state: The current game state.
        president_name: Name of the president using the power.
        target_player_name: Name of the player to be the next president.

    Returns:
        True if special election was successful, False if target is invalid.
    """
    # Cannot choose dead
    if game_state.player_status[target_player_name] == "dead":
        return False
        # Cannot choose dead player
    # Cannot choose self
    if president_name == target_player_name:
        return False
        # Cannot choose self

    # Set next president
    game_state.special_election_president = target_player_name
    game_state.log_event(
        president_name, f"Called special election. {target_player_name} will be next president."
    )
    return True


def policy_peek(game_state, president_name):
    """Allows the president to peek at the top 3 policies in the deck.

    Args:
        game_state: The current game state.
        president_name: Name of the president using the power.

    Returns:
        A list of the top 3 policy cards (strings), or an empty list if deck is empty.
    """
    top_policies = game_state.draw_policies(3)
    # Handle case where deck is empty
    if not top_policies:
        return []
        # No policies to peek at
    # Put back on top
    game_state.policy_deck = top_policies + game_state.policy_deck
    # Return peeked policies
    return top_policies


def enact_top_policy_chaos(game_state):
    """Enacts the top policy from the deck due to chaos (election tracker).

    Args:
        game_state: The current game state.

    Returns:
        The enacted policy card (string), or None if no policy was enacted.
    """
    top_policy = game_state.draw_policies(1)
    # Only enact if there's a policy to draw
    if top_policy:
        game_state.enact_policy(top_policy[0])
        # Return enacted policy
        return top_policy[0]
    # No policy enacted if deck is empty
    return None

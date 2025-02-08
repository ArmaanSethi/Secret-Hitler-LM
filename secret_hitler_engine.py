"""Engine for the Secret Hitler game, managing game state and logic."""

import random

# Constants
LIBERAL = "Liberal"
FASCIST = "Fascist"
ALIVE = "alive"
DEAD = "dead"


class GameState:
    """Represents the state of a Secret Hitler game.

    Attributes:
        player_names (list[str]): Names of the players.
        num_players (int): Number of players.
        use_ai_players (bool): Flag for AI players (currently unused).
        roles (dict[str, str]): Player names mapped to their roles.
        policy_deck (list[str]): The policy deck.
        policy_discard_pile (list[str]): The policy discard pile.
        liberal_policies_enacted (int): Number of Liberal policies enacted.
        fascist_policies_enacted (int): Number of Fascist policies enacted.
        election_tracker (int): The election tracker.
        government (dict[str, str | None]): Current President and Chancellor.
        previous_governments (list[tuple[str, str]]): History of governments.
        president_order (list[str]): Order of presidents.
        current_president_index (int): Index of the current president.
        term_limited_chancellor (str | None): Term-limited chancellor.
        term_limited_president (str | None): Term-limited president.
        hitler_revealed (bool): Flag if Hitler's identity is revealed.
        game_over (bool): Flag if the game is over.
        winner (str | None): The winner of the game.
        player_status (dict[str, str]): Player status (alive or dead).
        player_membership_cards (dict[str, str]): Player membership cards.
        investigated_players (set[str]): Players who have been investigated.
        special_election_president (str | None): Next president after special election.
        veto_power_available (bool): Flag if veto power is available.
        consecutive_failed_elections (int): Counter for consecutive failed elections.
        public_game_log (list[str]): Public game log.
        private_game_logs (dict[str, list[str]]): Private game logs for each player.
        current_phase (str): The current game phase (e.g., "Nomination").
        discussion_history (list[str]): History of discussion messages.
        discussion_turn_order_index (int): Index for discussion turn order.
        max_discussion_turns_per_player (int): Max discussion turns per player.
        discussion_turn_counts (dict[str, int]): Discussion turn counts per player.
    """

    def __init__(self, player_names: list[str], use_ai_players: bool = False):
        """Initializes the game state.

        Args:
            player_names: A list of player names (strings).
            use_ai_players: A boolean flag indicating if AI players are used.
        """
        self.player_names = player_names
        self.num_players = len(player_names)
        self.use_ai_players = use_ai_players
        self.roles = self.assign_roles()
        self.policy_deck = self.create_policy_deck()
        self.policy_discard_pile = []
        self.liberal_policies_enacted = 0
        self.fascist_policies_enacted = 0
        self.election_tracker = 0
        self.government = {"president": None, "chancellor": None}
        self.previous_governments = []
        self.president_order = player_names[:]
        self.current_president_index = 0
        self.term_limited_chancellor = None
        self.term_limited_president = None
        self.hitler_revealed = False
        self.game_over = False
        self.winner = None
        self.player_status = {name: ALIVE for name in player_names}
        self.player_membership_cards = self.assign_party_membership()
        self.investigated_players = set()
        self.special_election_president = None
        self.veto_power_available = False
        self.consecutive_failed_elections = 0
        self.public_game_log = []
        self.private_game_logs = {name: [] for name in player_names}
        self.current_phase = "Nomination"
        self.discussion_history = []
        self.discussion_turn_order_index = 0
        self.max_discussion_turns_per_player = 2
        self.discussion_turn_counts = {
            name: 0 for name in player_names if name in self.player_names
        }

    def assign_roles(self) -> dict[str, str]:
        """Assigns roles to players based on the number of players.

        Returns:
            A dictionary mapping player names to their roles.
        """
        roles_distribution = {
            5: 1 * [FASCIST] + [ "Hitler"] + 3 * [LIBERAL],
            6: 1 * [FASCIST] + ["Hitler"] + 4 * [LIBERAL],
            7: 2 * [FASCIST] + ["Hitler"] + 4 * [LIBERAL],
            8: 2 * [FASCIST] + ["Hitler"] + 5 * [LIBERAL],
            9: 3 * [FASCIST] + ["Hitler"] + 5 * [LIBERAL],
            10: 3 * [FASCIST] + ["Hitler"] + 6 * [LIBERAL],
        }
        roles = roles_distribution[self.num_players][:]
        random.shuffle(roles)
        return dict(zip(self.player_names, roles))

    def assign_party_membership(self) -> dict[str, str]:
        """Assigns party membership cards (all 'Fascist').

        Returns:
            A dictionary mapping player names to 'Fascist' membership.
        """
        return {name: FASCIST for name in self.player_names}

    def create_policy_deck(self) -> list[str]:
        """Creates the policy deck with 6 Liberal and 11 Fascist policies.

        Returns:
            A list representing the shuffled policy deck.
        """
        deck = [LIBERAL] * 6 + [FASCIST] * 11
        random.shuffle(deck)
        return deck

    def draw_policies(self, num: int) -> list[str]:
        """Draws a specified number of policies from the deck.

        Reshuffles the discard pile if necessary.

        Args:
            num: The number of policies to draw.

        Returns:
            A list of drawn policy cards.
        """
        drawn_policies = []
        for _ in range(num):
            if not self.policy_deck:
                self.policy_deck = self.policy_discard_pile[:]
                self.policy_discard_pile = []
                random.shuffle(self.policy_deck)
                self.log_event(None, "Policy deck reshuffled.")
            if self.policy_deck:
                drawn_policies.append(self.policy_deck.pop())
            else:
                break  # Handle empty deck after reshuffle
        return drawn_policies

    def discard_policy(self, policy: str):
        """Discards a policy card to the discard pile.

        Args:
            policy: The policy card to discard.
        """
        self.policy_discard_pile.append(policy)
        self.log_event(None, f"Policy discarded.", private_info={
                       self.get_president(): f"You discarded a {policy} policy."})

    def enact_policy(self, policy: str):
        """Enacts a policy and updates the game state.

        Args:
            policy: The policy card to enact.
        """
        if policy == LIBERAL:
            self.liberal_policies_enacted += 1
            self.log_event(
                None,
                f"Liberal policy enacted. Liberal policies: {self.liberal_policies_enacted}",
                private_info={
                    self.government['chancellor']: "You enacted a Liberal policy."}
            )
        elif policy == FASCIST:
            self.fascist_policies_enacted += 1
            self.log_event(
                None,
                f"Fascist policy enacted. Fascist policies: {self.fascist_policies_enacted}",
                private_info={
                    self.government['chancellor']: "You enacted a Fascist policy."}
            )
            if self.fascist_policies_enacted >= 5:
                self.veto_power_available = True
        self.check_game_end_conditions()

    def check_game_end_conditions(self):
        """Checks if any game end conditions are met."""
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
        if self.consecutive_failed_elections >= 3:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win due to 3 failed elections.")

    def get_president(self) -> str:
        """Returns the name of the current president.

        Returns:
            The name of the current president.
        """
        return self.president_order[self.current_president_index % self.num_players]

    def next_president(self):
        """Moves to the next president in the order."""
        self.current_president_index += 1
        self.special_election_president = None

    def set_government(self, president_name: str, chancellor_name: str):
        """Sets the president and chancellor.

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
        """Resets the government and handles failed elections."""
        if self.government["president"] and self.government["chancellor"]:
            self.previous_governments.append(
                (self.government["president"], self.government["chancellor"])
            )
            self.term_limited_president = self.government["president"]
            self.term_limited_chancellor = self.government["chancellor"]
        self.government = {"president": None, "chancellor": None}
        self.consecutive_failed_elections += 1
        if self.consecutive_failed_elections >= 3:
            self.enact_chaos_policy()
            self.consecutive_failed_elections = 0

    def enact_chaos_policy(self):
        """Enacts the top policy due to chaos (3 failed elections)."""
        self.log_event(None, "Three failed elections! Chaos policy enacted.")
        top_policy = self.draw_policies(1)[0]
        self.enact_policy(top_policy)
        self.election_tracker = 0
        self.term_limited_chancellor = None
        self.term_limited_president = None
        self.log_event(None, f"Chaos policy enacted was {top_policy}.")

    def increment_election_tracker(self):
        """Increments the election tracker and handles chaos."""
        if self.consecutive_failed_elections < 3:
            self.election_tracker += 1
            if self.election_tracker >= 3:
                top_policy = self.draw_policies(1)[0]
                self.enact_policy(top_policy)
                self.election_tracker = 0
                self.log_event(
                    None, f"Election Tracker reached 3! Top policy enacted.")
            else:
                self.log_event(
                    None,
                    f"Government failed. Election tracker is now {self.election_tracker}.",
                )
            self.check_game_end_conditions()

    def log_event(self, player_name: str | None, event_description: str, private_info: dict[str, str] | None = None):
        """Logs an event to public and private logs.

        Args:
            player_name: Name of the player initiating the event (or None).
            event_description: Description of the event.
            private_info: Optional dictionary of private information.
        """
        log_entry = (
            f"Round {len(self.public_game_log) + 1 if not self.game_over else 'End'} - "
        )
        if player_name:
            log_entry += f"{player_name}: "
        log_entry += event_description
        self.public_game_log.append(log_entry)

        for name in self.player_names:
            private_log_entry = log_entry
            if private_info and name in private_info:
                private_log_entry += f" (Private: {private_info[name]})"
            self.private_game_logs[name].append(private_log_entry)

    def get_game_state_for_player(self, player_name: str) -> dict:
        """Returns a simplified game state view for a specific player.

        Args:
            player_name: The name of the player.

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
            "investigated_players": list(self.investigated_players),
        }
        if (
            self.roles[player_name] == FASCIST
            or self.roles[player_name] == "Hitler"
        ):
            visible_state["fascist_players"] = [
                name
                for name, role in self.roles.items()
                if role in (FASCIST, "Hitler")
            ]
            if self.fascist_policies_enacted >= 3:
                visible_state["hitler_name"] = [
                    name for name, role in self.roles.items() if role == "Hitler"
                ][0]
        visible_state["my_role"] = self.roles[player_name]
        return visible_state

    def get_full_game_state(self) -> dict:
        """Returns the full game state (for debugging/replay).

        Returns:
            A dictionary representing the complete game state.
        """
        return {
            "player_names": self.player_names,
            "num_players": self.num_players,
            "roles": self.roles,
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
    
    def start_discussion(self, phase: str):
        """Starts a discussion phase.

        Args:
            phase: The name of the discussion phase (e.g., "Nomination").
        """
        self.current_phase = phase
        self.discussion_history = []
        self.discussion_turn_order_index = 0
        self.discussion_turn_counts = {
            name: 0
            for name in self.player_names
            if name in self.player_names and self.player_status[name] == ALIVE
        }

    def get_current_discussion_speaker(self) -> str | None:
        """Gets the name of the current discussion speaker.

        Returns:
            The name of the current speaker or None if no alive players.
        """
        alive_players = [
            player for player in self.player_names if self.player_status[player] == ALIVE
        ]
        if not alive_players:
            return None

        current_president_alive_index = -1
        for i, player in enumerate(alive_players):
            if player == self.get_president():
                current_president_alive_index = i
                break

        if current_president_alive_index == -1:
            current_president_alive_index = 0

        speaker_index_relative_to_president = self.discussion_turn_order_index
        speaker_index_in_alive_players = (
            current_president_alive_index + speaker_index_relative_to_president
        ) % len(alive_players)

        return alive_players[speaker_index_in_alive_players]

    def record_discussion_message(self, player_name: str, message_text: str):
        """Records a discussion message.

        Args:
            player_name: Name of the speaker.
            message_text: The message text.
        """
        message = f"{player_name}: {message_text}"
        self.discussion_history.append(message)
        self.log_event(None, f"Discussion: {message}")
        self.discussion_turn_order_index += 1
        self.discussion_turn_counts[player_name] += 1

    def can_end_discussion(self, by_president: bool = False) -> bool:
        """Checks if the discussion phase can be ended.

        Args:
            by_president: True if the president is trying to end discussion.

        Returns:
            True if discussion can be ended, False otherwise.
        """
        if not self.discussion_history:
            return False
        if by_president:
            return True
        alive_players = [
            name for name in self.player_names if self.player_status[name] == ALIVE
        ]
        all_alive_players_spoke_once = all(
            self.discussion_turn_counts.get(player, 0) >= 1 for player in alive_players
        )
        if all_alive_players_spoke_once and len(alive_players) > 1:
            return True

        max_turns_reached = all(
            self.discussion_turn_counts.get(player, 0)
            >= self.max_discussion_turns_per_player
            for player in self.player_names
            if self.player_status[player] == ALIVE
        )
        if max_turns_reached:
            return True
        return False

    def get_discussion_summary(self) -> str:
        """Returns a summary of the discussion history.

        Returns:
            A string containing all discussion messages.
        """
        return "\n".join(self.discussion_history)


def is_valid_chancellor_nominee(game_state: GameState, president_name: str, nominee_name: str) -> bool:
    """Checks if a player is a valid chancellor nominee.

    Args:
        game_state: The current game state.
        president_name: Name of the current president.
        nominee_name: Name of the proposed chancellor nominee.

    Returns:
        True if the nominee is valid, False otherwise.
    """
    if nominee_name == president_name:
        return False
    if game_state.player_status[nominee_name] == DEAD:
        return False
    if nominee_name == game_state.term_limited_chancellor:
        return False
    if (
        game_state.num_players >= 7 and nominee_name == game_state.term_limited_president
    ):
        return False
    return True


def get_player_role(game_state: GameState, player_name: str) -> str:
    """Returns the secret role of a player.

    Args:
        game_state: The current game state.
        player_name: Name of the player.

    Returns:
        The role of the player.
    """
    return game_state.roles[player_name]


def get_player_names(game_state: GameState) -> list[str]:
    """Returns a list of all player names.

    Args:
        game_state: The current game state.

    Returns:
        A list of player names.
    """
    return game_state.player_names


def kill_player(game_state: GameState, player_name: str) -> bool:
    """Kills a player, removing them from the game.

    Args:
        game_state: The current game state.
        player_name: Name of the player to kill.

    Returns:
        True if the player was killed, False if already dead.
    """
    if game_state.player_status[player_name] == DEAD:
        return False
    game_state.player_status[player_name] = DEAD
    game_state.log_event(None, f"{player_name} has been executed.")
    if game_state.roles[player_name] == "Hitler":
        game_state.game_over = True
        game_state.winner = "Liberals"
        game_state.log_event(None, "Liberals win! Hitler has been executed.")
        game_state.check_game_end_conditions()
    return True


def reveal_hitler(game_state: GameState):
    """Reveals Hitler's identity.

    Args:
        game_state: The current game state.
    """
    game_state.hitler_revealed = True
    game_state.log_event(None, "Hitler's identity is now revealed.")


def investigate_player(game_state: GameState, president_name: str, target_player_name: str) -> str | None:
    """Investigates a player's party membership.

    Args:
        game_state: The current game state.
        president_name: Name of the investigating president.
        target_player_name: Name of the player to investigate.

    Returns:
        The membership card ('Fascist'), or None if invalid.
    """
    if target_player_name in game_state.investigated_players:
        return None
    if game_state.player_status[target_player_name] == DEAD:
        return None
    if president_name == target_player_name:
        return None

    game_state.investigated_players.add(target_player_name)
    return game_state.player_membership_cards[target_player_name]


def call_special_election(game_state: GameState, president_name: str, target_player_name: str) -> bool:
    """Calls a special election, setting the next president.

    Args:
        game_state: The current game state.
        president_name: Name of the calling president.
        target_player_name: Name of the next president.

    Returns:
        True if successful, False if invalid target.
    """
    if game_state.player_status[target_player_name] == DEAD:
        return False
    if president_name == target_player_name:
        return False

    game_state.special_election_president = target_player_name
    game_state.log_event(
        president_name, f"Called special election. {target_player_name} will be next president."
    )
    return True


def policy_peek(game_state: GameState, president_name: str) -> list[str]:
    """Allows the president to peek at the top 3 policies.

    Args:
        game_state: The current game state.
        president_name: Name of the peeking president.

    Returns:
        A list of the top 3 policy cards, or [] if empty.
    """
    top_policies = game_state.draw_policies(3)
    if not top_policies:
        return []
    game_state.policy_deck = top_policies + game_state.policy_deck

    # Notify other players that the President peeked (without revealing the policies)
    for player in game_state.player_names:
        if player != president_name:
            game_state.log_event(
                None, "The President used Policy Peek.", private_info={player: "The President peeked at the top policies."}
            )

    return top_policies


def enact_top_policy_chaos(game_state: GameState) -> str | None:
    """Enacts the top policy due to chaos (election tracker).

    Args:
        game_state: The current game state.

    Returns:
        The enacted policy card, or None if no policy.
    """
    top_policy = game_state.draw_policies(1)
    if top_policy:
        game_state.enact_policy(top_policy[0])
        return top_policy[0]
    return None

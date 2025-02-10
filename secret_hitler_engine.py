import random
from enum import Enum
from collections import namedtuple


class Role(Enum):
    LIBERAL = "Liberal"
    FASCIST = "FASCIST"
    HITLER = "Hitler"


class PlayerStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"


class GamePhase(Enum):
    NOMINATION = "Nomination"
    ELECTION = "Election"
    LEGISLATIVE = "Legislative"
    VOTING = "Voting"
    EXECUTIVE_ACTION = "Executive Action"
    DISCUSSION = "Discussion"


Government = namedtuple("Government", ["president", "chancellor"])


class GameState:
    def __init__(self, players, game_logger):
        self.players = players
        self.num_players = len(players)
        self.roles = self._assign_roles()
        self.deck = self._create_deck()
        self.discard = []
        self.lib_policies = 0
        self.fasc_policies = 0
        self.election_tracker = 0
        self.gov = Government(president=None, chancellor=None)
        self.prev_govs = []
        self.president_order = players[:]
        self.current_president_index = 0
        self.term_limit_chancellor = None
        self.term_limit_president = None
        self.hitler_revealed = False
        self.game_over = False
        self.winner = None
        self.player_status = {p: PlayerStatus.ALIVE for p in players}
        self.membership_cards = self._assign_membership()
        self.investigated = set()
        self.special_president = None
        self.veto_power = False
        self.failed_elections = 0
        self.public_log = []
        self.private_logs = {p: [] for p in players}
        self.phase = GamePhase.NOMINATION
        self.discussion_history = []
        self.discussion_speaker_index = 0
        self.max_discussion_turns = 2
        self.discussion_turn_counts = {p: 0 for p in players}
        self.game_logger = game_logger

    def _assign_roles(self):
        role_dist = {
            5: [Role.FASCIST] * 1 + [Role.HITLER] + [Role.LIBERAL] * 3,
            6: [Role.FASCIST] * 1 + [Role.HITLER] + [Role.LIBERAL] * 4,
            7: [Role.FASCIST] * 2 + [Role.HITLER] + [Role.LIBERAL] * 4,
            8: [Role.FASCIST] * 2 + [Role.HITLER] + [Role.LIBERAL] * 5,
            9: [Role.FASCIST] * 3 + [Role.HITLER] + [Role.LIBERAL] * 5,
            10: [Role.FASCIST] * 3 + [Role.HITLER] + [Role.LIBERAL] * 6,
        }
        roles = role_dist[self.num_players][:]
        random.shuffle(roles)
        return dict(zip(self.players, roles))

    def _assign_membership(self):
        return {p: Role.FASCIST for p in self.players}

    def _create_deck(self):
        deck = [Role.LIBERAL] * 6 + [Role.FASCIST] * 11
        random.shuffle(deck)
        return deck

    def draw_policies(self, num):
        drawn = []
        for _ in range(num):
            if not self.deck:
                self.deck = self.discard[:]
                self.discard = []
                random.shuffle(self.deck)
                self.log_event(None, "Deck reshuffled.")
            if self.deck:
                drawn.append(self.deck.pop())
            else:
                break
        return drawn

    def discard_policy(self, policy):
        self.discard.append(policy)

    def enact_policy(self, policy):
        policy_type = "Unknown Policy Type"
        if policy == Role.LIBERAL:
            self.lib_policies += 1
            policy_type = "Liberal"
        elif policy == Role.FASCIST:
            self.fasc_policies += 1
            policy_type = "Fascist"
            if self.fasc_policies >= 5:
                self.veto_power = True
        self._check_game_over()
        self.log_event(
            None, f"Policy enacted: {policy_type}. Liberal policies enacted: {self.lib_policies}, Fascist policies enacted: {self.fasc_policies}")
        return policy_type

    def _check_game_over(self):
        game_end_conditions = [
            (self.lib_policies >= 5, Role.LIBERAL, "Liberals win by policies."),
            (self.fasc_policies >= 6, Role.FASCIST, "Fascists win by policies."),
            (self.check_hitler_chancellor_win(), Role.FASCIST,
             "Fascists win: Hitler Chancellor."),
        ]
        for condition, winner, message in game_end_conditions:
            if condition:
                self.game_over = True
                self.winner = winner
                self.log_event(None, message)
                return

    def check_hitler_chancellor_win(self):
        return (self.fasc_policies >= 3 and self.gov.chancellor and self.roles[self.gov.chancellor] == Role.HITLER)

    def get_president(self):
        return self.president_order[self.current_president_index % self.num_players]

    def next_president(self):
        self.current_president_index += 1
        self.special_president = None

    def set_government(self, president, chancellor):
        self.gov = Government(president=president, chancellor=chancellor)

    def reset_government(self):
        if self.gov.president and self.gov.chancellor:
            self.prev_govs.append(
                (self.gov.president, self.gov.chancellor))
            self.term_limit_president = self.gov.president
            self.term_limit_chancellor = self.gov.chancellor
        self.gov = Government(president=None, chancellor=None)
        self.failed_elections += 1
        if self.failed_elections >= 3:
            self.enact_chaos_policy()
            self.failed_elections = 0

    def enact_chaos_policy(self):
        self.log_event(None, "Chaos policy enacted!")
        policy = self.draw_policies(1)[0]
        policy_type = self.enact_policy(policy)
        self.election_tracker = 0
        self.term_limit_chancellor = None
        self.term_limit_president = None
        self.log_event(None, f"Chaos policy was {policy_type}.")
        return policy_type

    def increment_election_tracker(self):
        if self.election_tracker < 3:
            self.election_tracker += 1
            if self.election_tracker >= 3:
                policy = self.draw_policies(1)[0]
                policy_type = self.enact_policy(policy)
                self.election_tracker = 0
                self.log_event(
                    None, f"Election Tracker maxed! {policy_type} policy enacted .")
            else:
                self.log_event(
                    None, f"Government failed. Election tracker: {self.election_tracker}.")
            self._check_game_over()

    def log_event(self, player, event_desc, private_info=None, private_only=False):
        log_entry = f"Round {len(self.public_log) + 1 if not self.game_over else 'End'} - "
        if player:
            log_entry += f"{player}: "
        log_entry += event_desc

        if not private_only:
            self._log_public(log_entry)

        self._log_private(log_entry, private_info, player=player)

    def _log_public(self, log_entry):
        self.public_log.append(log_entry)
        if self.game_logger:
            self.game_logger.log_public_event(log_entry)

    def _log_private(self, log_entry, private_info=None, player=None):
        for p in self.players:
            private_log_entry = log_entry
            if private_info and p in private_info:
                private_log_entry += f" (Private: {private_info[p]})"
            self.private_logs[p].append(private_log_entry)
        if self.game_logger:
            player_name = player if player else "Game"
            self.game_logger.log_to_debug_file(
                player_name, f"Game Event: {log_entry}")

    def get_player_role(self, player):
        return self.roles[player]

    def get_player_names(self):
        return self.players

    def kill_player(self, player):
        if self.player_status[player] == PlayerStatus.DEAD:
            return False
        self.player_status[player] = PlayerStatus.DEAD
        self.log_event(None, f"{player} executed.")
        if self.roles[player] == Role.HITLER:
            self.game_over = True
            self.winner = "Liberals"
            self.log_event(None, "Liberals win: Hitler executed.")
            self._check_game_over()
        return True

    def investigate_player(self, president, target_player):
        if target_player in self.investigated:
            return None
        if self.player_status[target_player] == PlayerStatus.DEAD:
            return None
        if president == target_player:
            return None

        self.investigated.add(target_player)
        return self.membership_cards[target_player]

    def call_special_election(self, president, target_player):
        if self.player_status[target_player] == PlayerStatus.DEAD:
            return False
        if president == target_player:
            return False

        self.special_president = target_player
        return True

    def policy_peek(self):
        policies = self.draw_policies(3)
        if not policies:
            return []
        self.deck = policies + self.deck
        return policies

    def start_discussion(self, phase_name):
        self.current_discussion_phase = phase_name
        self.discussion_speaker_index = 0
        self.discussion_turn_counts = {p: 0 for p in self.players}

    def get_current_discussion_speaker(self):
        alive_players = [
            p for p in self.players if self.player_status[p] == PlayerStatus.ALIVE]
        if not alive_players:
            return None
        return alive_players[self.discussion_speaker_index % len(alive_players)]

    def next_discussion_speaker(self):
        current_speaker = self.get_current_discussion_speaker()
        if current_speaker:
            self.discussion_turn_counts[current_speaker] += 1
            self.discussion_speaker_index += 1
        return self.get_current_discussion_speaker()

    def get_first_discussion_speaker(self):
        alive_players = [
            p for p in self.players if self.player_status[p] == PlayerStatus.ALIVE]
        return alive_players[0] if alive_players else None

    def record_discussion_message(self, player_name, message_text):
        message = f"{player_name}: {message_text}"
        self.discussion_history.append(message)

    def get_state_string(self):
        return f"""
        Liberal Policies Enacted: {self.lib_policies}
        Fascist Policies Enacted: {self.fasc_policies}
        Election Tracker: {self.election_tracker}
        President: {self.gov.president or 'None'}
        Chancellor: {self.gov.chancellor or 'None'}
        Veto Power Available: {'Yes' if self.veto_power else 'No'}
        Investigated Players: {', '.join(self.investigated)}
        Current Players: {', '.join(self.players)}
        Player Status: {self.player_status}
        """

    def get_public_log_string(self):
        return "\n".join([f"- {event}" for event in self.public_log])

    def get_private_log_string(self, player_name):
        return "\n".join([f"- {event}" for event in self.private_logs[player_name]])

    def get_discussion_string(self):
        return "\n".join([f"- {message}" for message in self.discussion_history])

    def get_player_names_by_role(self, role_name: Role):
        return [name for name, role in self.roles.items() if role == role_name]


def is_valid_chancellor_nominee(game_state, president_name, nominee_name):
    if nominee_name == president_name:
        return False
    if game_state.player_status[nominee_name] == PlayerStatus.DEAD:
        return False
    if nominee_name == game_state.term_limit_chancellor:
        return False
    if (game_state.num_players >= 7 and nominee_name == game_state.term_limit_president):
        return False
    return True

# secret_hitler_engine.py (SIMPLIFIED AND REFACTORED)
import random

LIBERAL = "Liberal"
FASCIST = "Fascist"
ALIVE = "alive"
DEAD = "dead"


class GameState:
    def __init__(self, players):
        self.players = players
        self.num_players = len(players)
        self.roles = self._assign_roles()
        self.deck = self._create_deck()
        self.discard = []
        self.lib_policies = 0
        self.fasc_policies = 0
        self.election_tracker = 0
        self.gov = {"president": None, "chancellor": None}
        self.prev_govs = []
        self.president_order = players[:]
        self.current_president_index = 0
        self.term_limit_chancellor = None
        self.term_limit_president = None
        self.hitler_revealed = False
        self.game_over = False
        self.winner = None
        self.player_status = {p: ALIVE for p in players}
        self.membership_cards = self._assign_membership()
        self.investigated = set()
        self.special_president = None
        self.veto_power = False
        self.failed_elections = 0
        self.public_log = []
        self.private_logs = {p: [] for p in players}
        self.phase = "Nomination"
        self.discussion_history = []
        self.discussion_speaker_index = 0
        self.max_discussion_turns = 2
        self.discussion_turn_counts = {p: 0 for p in players}

    def _assign_roles(self):
        role_dist = {
            5: [FASCIST] * 1 + ["Hitler"] + [LIBERAL] * 3,
            6: [FASCIST] * 1 + ["Hitler"] + [LIBERAL] * 4,
            7: [FASCIST] * 2 + ["Hitler"] + [LIBERAL] * 4,
            8: [FASCIST] * 2 + ["Hitler"] + [LIBERAL] * 5,
            9: [FASCIST] * 3 + ["Hitler"] + [LIBERAL] * 5,
            10: [FASCIST] * 3 + ["Hitler"] + [LIBERAL] * 6,
        }
        roles = role_dist[self.num_players][:]
        random.shuffle(roles)
        return dict(zip(self.players, roles))

    def _assign_membership(self):
        # Everyone fascist membership for now
        return {p: FASCIST for p in self.players}

    def _create_deck(self):
        deck = [LIBERAL] * 6 + [FASCIST] * 11
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
        self.log_event(self.get_president(), "Discarded policy.", private_info={
                       self.get_president(): f"Discarded {policy} policy."})

    def enact_policy(self, policy):
        if policy == LIBERAL:
            self.lib_policies += 1
            self.log_event(None, f"Liberal policy enacted. Liberal policies: {self.lib_policies}", private_info={
                           self.gov['chancellor']: "You enacted a Liberal policy."})
        elif policy == FASCIST:
            self.fasc_policies += 1
            self.log_event(None, f"Fascist policy enacted. Fascist policies: {self.fasc_policies}", private_info={
                           self.gov['chancellor']: "You enacted a Fascist policy."})
            if self.fasc_policies >= 5:
                self.veto_power = True
        self._check_game_over()

    def _check_game_over(self):
        if self.lib_policies >= 5:
            self.game_over = True
            self.winner = "Liberals"
            self.log_event(None, "Liberals win by policies.")
        if self.fasc_policies >= 6:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win by policies.")
        if self.check_hitler_chancellor_win():
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win: Hitler Chancellor.")
        if self.failed_elections >= 3:
            self.game_over = True
            self.winner = "Fascists"
            self.log_event(None, "Fascists win by failed elections.")

    def check_hitler_chancellor_win(self):
        return (self.fasc_policies >= 3 and self.gov["chancellor"] and self.roles[self.gov["chancellor"]] == "Hitler")

    def get_president(self):
        return self.president_order[self.current_president_index % self.num_players]

    def next_president(self):
        self.current_president_index += 1
        self.special_president = None

    def set_government(self, president, chancellor):
        self.gov["president"] = president
        self.gov["chancellor"] = chancellor
        self.log_event(
            None, f"Government: President {president}, Chancellor {chancellor}")

    def reset_government(self):
        if self.gov["president"] and self.gov["chancellor"]:
            self.prev_govs.append(
                (self.gov["president"], self.gov["chancellor"]))
            self.term_limit_president = self.gov["president"]
            self.term_limit_chancellor = self.gov["chancellor"]
        self.gov = {"president": None, "chancellor": None}
        self.failed_elections += 1
        if self.failed_elections >= 3:
            self.enact_chaos_policy()
            self.failed_elections = 0

    def enact_chaos_policy(self):
        self.log_event(None, "Chaos policy enacted!")
        policy = self.draw_policies(1)[0]
        self.enact_policy(policy)
        self.election_tracker = 0
        self.term_limit_chancellor = None
        self.term_limit_president = None
        self.log_event(None, f"Chaos policy was {policy}.")

    def increment_election_tracker(self):
        if self.failed_elections < 3:
            self.election_tracker += 1
            if self.election_tracker >= 3:
                policy = self.draw_policies(1)[0]
                self.enact_policy(policy)
                self.election_tracker = 0
                self.log_event(None, "Election Tracker maxed! Policy enacted.")
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
            self.public_log.append(log_entry)

        for p in self.players:
            private_log_entry = log_entry
            if private_info and p in private_info:
                private_log_entry += f" (Private: {private_info[p]})"
            self.private_logs[p].append(private_log_entry)

    def get_player_role(self, player):
        return self.roles[player]

    def get_player_names(self):
        return self.players

    def kill_player(self, player):
        if self.player_status[player] == DEAD:
            return False
        self.player_status[player] = DEAD
        self.log_event(None, f"{player} executed.")
        if self.roles[player] == "Hitler":
            self.game_over = True
            self.winner = "Liberals"
            self.log_event(None, "Liberals win: Hitler executed.")
            self._check_game_over()
        return True

    def investigate_player(self, president, target_player):
        if target_player in self.investigated:
            return None
        if self.player_status[target_player] == DEAD:
            return None
        if president == target_player:
            return None

        self.investigated.add(target_player)
        return self.membership_cards[target_player]

    def call_special_election(self, president, target_player):
        if self.player_status[target_player] == DEAD:
            return False
        if president == target_player:
            return False

        self.special_president = target_player
        self.log_event(
            president, f"Special election called. {target_player} next president.")
        return True

    def policy_peek(self, president):
        policies = self.draw_policies(3)
        if not policies:
            return []
        self.deck = policies + self.deck

        for p in self.players:
            if p != president:
                self.log_event(None, "President used Policy Peek.", private_info={
                               p: "President peeked at policies."})
        return policies

    def start_discussion(self, phase_name):
        self.current_discussion_phase = phase_name
        self.discussion_speaker_index = 0
        self.discussion_turn_counts = {p: 0 for p in self.players}

    def get_current_discussion_speaker(self):
        alive_players = [
            p for p in self.players if self.player_status[p] == ALIVE]
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
            p for p in self.players if self.player_status[p] == ALIVE]
        return alive_players[0] if alive_players else None

    def record_discussion_message(self, player_name, message_text):
        message = f"{player_name}: {message_text}"
        self.discussion_history.append(message)
        self.log_event(None, f"Discussion: {message}")
        self.discussion_turn_counts[player_name] += 1

    # --- String representation methods for simplified output ---
    def get_state_string(self):
        """Returns a string representation of the core game state."""
        return f"""
        Liberal Policies Enacted: {self.lib_policies}
        Fascist Policies Enacted: {self.fasc_policies}
        Election Tracker: {self.election_tracker}
        President: {self.gov['president'] or 'None'}
        Chancellor: {self.gov['chancellor'] or 'None'}
        Veto Power Available: {'Yes' if self.veto_power else 'No'}
        Investigated Players: {', '.join(self.investigated)}
        Current Players: {', '.join(self.players)}
        Player Status: {self.player_status}
        """

    def get_public_log_string(self):
        """Returns a string of the public game log."""
        return "\n".join([f"- {event}" for event in self.public_log])

    def get_private_log_string(self, player_name):
        """Returns a string of the private game log for a player."""
        return "\n".join([f"- {event}" for event in self.private_logs[player_name]])

    def get_discussion_string(self):
        """Returns a string of the discussion history."""
        return "\n".join([f"- {message}" for message in self.discussion_history])


def is_valid_chancellor_nominee(game_state, president_name, nominee_name):
    if nominee_name == president_name:
        return False
    if game_state.player_status[nominee_name] == DEAD:
        return False
    if nominee_name == game_state.term_limit_chancellor:
        return False
    if (game_state.num_players >= 7 and nominee_name == game_state.term_limit_president):
        return False
    return True

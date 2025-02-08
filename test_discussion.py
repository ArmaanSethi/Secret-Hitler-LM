import unittest
from secret_hitler_engine import GameState

class TestDiscussion(unittest.TestCase):
    """Test suite for Secret Hitler discussion mechanics.
    
    This class contains unit tests that verify the discussion functionality
    of the Secret Hitler game implementation, including discussion phase
    initialization, turn management, message recording, and discussion ending
    conditions.
    """
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.player_names = [f"Player{i}" for i in range(1, 6)]  # 5 players for tests
        self.game_state = GameState(self.player_names)

    def test_discussion_initialization(self):
        """Test if discussion phase initializes correctly."""
        phase_name = "Nomination"
        self.game_state.start_discussion(phase_name)
        
        self.assertEqual(self.game_state.current_phase, phase_name)
        self.assertEqual(len(self.game_state.discussion_history), 0)
        self.assertEqual(self.game_state.discussion_turn_order_index, 0)
        
        # Check if turn counts are initialized for alive players only
        for player in self.player_names:
            self.assertEqual(self.game_state.discussion_turn_counts[player], 0)

    def test_current_discussion_speaker(self):
        """Test if the current speaker is determined correctly."""
        self.game_state.start_discussion("Nomination")
        
        # First speaker should be the president
        first_speaker = self.game_state.get_current_discussion_speaker()
        self.assertEqual(first_speaker, self.game_state.get_president())
        
        # Move to next speaker
        self.game_state.discussion_turn_order_index += 1
        second_speaker = self.game_state.get_current_discussion_speaker()
        self.assertNotEqual(first_speaker, second_speaker)

    def test_record_discussion_message(self):
        """Test if discussion messages are recorded correctly."""
        self.game_state.start_discussion("Nomination")
        speaker = self.game_state.get_current_discussion_speaker()
        message = "I think we should be careful who we elect."
        
        self.game_state.record_discussion_message(speaker, message)
        
        # Check if message is in history
        self.assertEqual(len(self.game_state.discussion_history), 1)
        self.assertEqual(self.game_state.discussion_history[0], f"{speaker}: {message}")
        
        # Check if turn count increased
        self.assertEqual(self.game_state.discussion_turn_counts[speaker], 1)
        
        # Check if turn index increased
        self.assertEqual(self.game_state.discussion_turn_order_index, 1)

    def test_can_end_discussion(self):
        """Test various conditions for ending discussion."""
        self.game_state.start_discussion("Nomination")
        
        # Cannot end with no messages
        self.assertFalse(self.game_state.can_end_discussion())
        
        # Record a message
        speaker = self.game_state.get_current_discussion_speaker()
        self.game_state.record_discussion_message(speaker, "Test message")
        
        # President can end after one message
        self.assertTrue(self.game_state.can_end_discussion(by_president=True))
        
        # Others cannot end until all alive players spoke
        self.assertFalse(self.game_state.can_end_discussion(by_president=False))
        
        # Record messages for all other players
        for _ in range(len(self.player_names) - 1):
            current_speaker = self.game_state.get_current_discussion_speaker()
            self.game_state.record_discussion_message(current_speaker, "Test message")
        
        # Now anyone can end discussion
        self.assertTrue(self.game_state.can_end_discussion(by_president=False))

    def test_max_turns_limit(self):
        """Test if discussion ends when max turns are reached."""
        self.game_state.start_discussion("Nomination")
        
        # Record max turns for each player
        for _ in range(self.game_state.max_discussion_turns_per_player * len(self.player_names)):
            current_speaker = self.game_state.get_current_discussion_speaker()
            if self.game_state.discussion_turn_counts[current_speaker] < self.game_state.max_discussion_turns_per_player:
                self.game_state.record_discussion_message(current_speaker, "Test message")
        
        # Check if discussion can end due to max turns
        self.assertTrue(self.game_state.can_end_discussion())

    def test_discussion_with_dead_players(self):
        """Test discussion mechanics when some players are dead."""
        self.game_state.start_discussion("Nomination")
        
        # Kill a player
        dead_player = self.player_names[1]
        self.game_state.player_status[dead_player] = "dead"
        
        # Check if dead player is skipped in speaker order
        current_speaker = self.game_state.get_current_discussion_speaker()
        self.assertNotEqual(current_speaker, dead_player)
        
        # Record messages for all alive players
        alive_players = [p for p in self.player_names if self.game_state.player_status[p] == "alive"]
        for _ in range(len(alive_players)):
            speaker = self.game_state.get_current_discussion_speaker()
            self.game_state.record_discussion_message(speaker, "Test message")
        
        # Check if discussion can end after all alive players spoke
        self.assertTrue(self.game_state.can_end_discussion())

    def test_discussion_summary(self):
        """Test if discussion summary is generated correctly."""
        self.game_state.start_discussion("Nomination")
        
        # Record multiple messages
        messages = [
            ("Player1", "First message"),
            ("Player2", "Second message"),
            ("Player3", "Third message")
        ]
        
        for speaker, message in messages:
            self.game_state.record_discussion_message(speaker, message)
        
        # Check summary format
        expected_summary = "\n".join([f"{speaker}: {message}" for speaker, message in messages])
        self.assertEqual(self.game_state.get_discussion_summary(), expected_summary)

if __name__ == '__main__':
    unittest.main()
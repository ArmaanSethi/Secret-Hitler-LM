import unittest
from secret_hitler_engine import GameState


class TestSecretHitler(unittest.TestCase):
    """Test suite for Secret Hitler game mechanics and rules.
    
    This class contains unit tests that verify the core functionality
    of the Secret Hitler game implementation, including game initialization,
    role distribution, policy deck management, government formation,
    and win conditions.
    """
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.player_names = [f"Player{i}" for i in range(
            1, 6)]  # 5 players for basic tests
        self.game_state = GameState(self.player_names)

    def test_game_initialization(self):
        """Test if game initializes correctly with proper number of players."""
        self.assertEqual(len(self.game_state.player_names), 5)
        self.assertEqual(len(self.game_state.roles), 5)
        # Check initial policy deck size
        self.assertEqual(len(self.game_state.policy_deck),
                         17)  # 6 Liberal + 11 Fascist

    def test_role_distribution(self):
        """Test if roles are distributed correctly for 5 players."""
        roles = list(self.game_state.roles.values())
        self.assertEqual(roles.count("Liberal"), 3)  # 3 Liberals
        self.assertEqual(roles.count("Fascist"), 1)  # 1 Fascist
        self.assertEqual(roles.count("Hitler"), 1)  # 1 Hitler

    def test_policy_deck_creation(self):
        """Test if policy deck is created with correct number of cards."""
        deck = self.game_state.create_policy_deck()
        self.assertEqual(len(deck), 17)
        self.assertEqual(deck.count("Liberal"), 6)
        self.assertEqual(deck.count("Fascist"), 11)

    def test_draw_policies(self):
        """Test drawing policies from the deck."""
        initial_deck_size = len(self.game_state.policy_deck)
        drawn_policies = self.game_state.draw_policies(3)
        self.assertEqual(len(drawn_policies), 3)
        self.assertEqual(len(self.game_state.policy_deck),
                         initial_deck_size - 3)

    def test_government_nomination(self):
        """Test government nomination process."""
        president = self.game_state.get_president()
        chancellor = [p for p in self.player_names if p != president][0]
        self.game_state.set_government(president, chancellor)
        self.assertEqual(self.game_state.government["president"], president)
        self.assertEqual(self.game_state.government["chancellor"], chancellor)

    def test_game_end_conditions(self):
        """Test various game end conditions."""
        # Test Liberal victory condition
        self.game_state.liberal_policies_enacted = 5
        self.game_state.check_game_end_conditions()
        self.assertTrue(self.game_state.game_over)
        self.assertEqual(self.game_state.winner, "Liberals")

        # Reset game state
        self.setUp()

        # Test Fascist victory condition (6 policies)
        self.game_state.fascist_policies_enacted = 6
        self.game_state.check_game_end_conditions()
        self.assertTrue(self.game_state.game_over)
        self.assertEqual(self.game_state.winner, "Fascists")

    def test_veto_power(self):
        """Test veto power activation."""
        self.assertFalse(self.game_state.veto_power_available)
        self.game_state.fascist_policies_enacted = 5
        self.game_state.enact_policy("Fascist")
        self.assertTrue(self.game_state.veto_power_available)


if __name__ == '__main__':
    unittest.main()

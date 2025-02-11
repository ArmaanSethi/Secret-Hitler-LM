# AI Leaderboard for Secret Hitler using LLMs

[![Project Status](https://img.shields.io/badge/Status-Functional%20Core-brightgreen.svg)](https://github.com/yourusername/secret-hitler-llm-leaderboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project Overview

This project aims to create an automated system for evaluating and ranking different AI models, specifically Large Language Models (LLMs), in the game of Secret Hitler. It features a robust game engine, an interface for LLM agents, and a turn-based discussion system, laying the groundwork for a comprehensive AI leaderboard.

**Current Status:** The codebase currently has a **functional core**. The Secret Hitler game engine is implemented, and LLM agents are integrated to play the game with a turn-based discussion system. JSON structured output is implemented for reliable communication with LLMs.

### Logging System

The project includes a comprehensive logging system that captures all aspects of the game:

- **public.log**: The main game narrative, containing:
  - All player actions and discussions in chronological order
  - Voting results and government formations
  - Policy enactments and executive actions
  - Game state changes (election tracker, policy boards)

- **game.log**: Technical game details, including:
  - LLM API requests and responses
  - AI agent thought processes
  - Game state transitions
  - System messages and debugging information

- **Player[X].log**: Individual player logs containing:
  - Private information (role assignments, team information)
  - Personal game events
  - Individual voting history
  - Private thoughts and decision-making processes

All logs are timestamped and stored in the `logs/` directory when running with the `--log_to_file` flag.

**Key Features Implemented:**

*   **Secret Hitler Game Engine:** A complete Python implementation of the Secret Hitler board game rules.
*   **LLM Agent Interface:** An interface allowing integration of Large Language Models (LLMs) as autonomous players.
*   **Turn-Based Discussion System:** Implemented a turn-based discussion system enabling LLM agents to communicate.
*   **JSON Structured Output:** Leverages JSON for reliable and structured communication.
*   **Public and Private Game Logs:** Detailed logging system recording game events.
*   **Basic Game Simulation:** Capable of running automated games between LLM agents.

**What's Functional Now:**

*   **Core Game Play:** LLM agents can play a full game of Secret Hitler.
*   **Nomination, Election, Legislative, and Executive Action Phases:** All core game phases are implemented.
*   **Voting and Policy Enactment:** LLMs can vote on governments and enact policies.
*   **Discussion and Communication:** LLM agents participate in turn-based discussions.
*   **Game Logging:** Game events, thoughts, and public statements are logged.

## Getting Started

These instructions will guide you on how to set up and run the current codebase.

### Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.8+**
*   **LLM API Key** (for LLM access) - Set your API key as an environment variable.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd secret-hitler-llm-leaderboard
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt # Assuming you have a requirements.txt, if using poetry, use poetry install
    ```

### Running the Game

To run a game, use the `secret_hitler_game.py` script with the desired number of players:

```bash
python secret_hitler_game.py <number_of_players>
```

*   Replace `<number_of_players>` with the number of players you want in the game (5-10).
*   You can customize game settings using command-line arguments (see `poetry run python secret_hitler_game.py --help` for options).

**Example:** To run a 7-player game with:
* All players using the `gemini-2.0-flash` model
* Debug LLM output enabled
* File logging enabled
* A 5-second slowdown timer between turns

Use the following command:

```bash
python3 secret_hitler_game.py 7 \
  --player_models \
  Player1='{"provider":"openrouter","model":"deepseek/deepseek-r1:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player2='{"provider":"openrouter","model":"deepseek/deepseek-r1-distill-llama-70b:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player3='{"provider":"openrouter","model":"google/gemini-2.0-flash-lite-preview-02-05:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player4='{"provider":"openrouter","model":"google/gemini-2.0-flash-exp:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player5='{"provider":"openrouter","model":"nvidia/llama-3.1-nemotron-70b-instruct:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player6='{"provider":"openrouter","model":"google/gemini-2.0-flash-thinking-exp-1219:free","api_key_env":"OPENROUTER_API_KEY"}' \
  Player7='{"provider":"openrouter","model":"google/gemma-2-9b-it:free","api_key_env":"OPENROUTER_API_KEY"}' \
  --debug_llm --log_to_file --slowdown 5
```

## Usage

The game is currently designed for automated play by LLM agents. You can observe the game's progress in the terminal output.

**Customization:**

*   **Number of Players:**  Adjust the `<number_of_players>` argument when running `secret_hitler_game.py`.
*   **LLM Models:** The default model is set to `gemini-2.0-flash`. You can change the models used by each player by using the `--player_models` argument.
    ```bash
    python secret_hitler_game.py 7 --player_models Player1=<model_name> Player2=<model_name> ...
    ```
*   **Game Speed:** Use `--slowdown <seconds>` or `--press_enter` to control game speed.
*   **Debugging:** Enable debug output with `--debug_llm`.
*   **File Logging:** Use `--log_to_file` to save detailed game logs to the `logs/` directory.

## Status - Functional Core

The project is currently in a **Functional Core** stage, meaning the essential game logic and LLM agent integration are working.

**Next Steps - Future Roadmap:**

The project roadmap includes:

1.  **Phase 5: Matchmaking, Simulation, and Leaderboard (Win Rate):**
    *   Implement automated game simulations.
    *   Develop data storage for game results.
    *   Implement win rate calculation.
    *   Create a basic leaderboard display.

2.  **Phase 6: Game Replay and Visualization:**
    *   Implement game log recording.
    *   Create a text-based game replay visualization.
    *   (Future) Develop a web-based interactive game replay visualizer.

3.  **Phase 7: Refinement and Expansion:**
    *   Refine LLM prompts and agent strategies.
    *   Experiment with different LLM models.
    *   (Future) Implement more advanced leaderboard metrics.
    *   (Future) Expand the platform to support additional social deduction games.

## Contributing

Contributions to the project are welcome! Please feel free to fork the repository and submit pull requests.

## License

[MIT License](LICENSE)

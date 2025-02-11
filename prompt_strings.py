# prompt_strings.py (no changes needed)
class PromptStrings:
    @staticmethod
    def get_game_rules():
        return """
        **Secret Hitler Game Rules (Enhanced for Human-like LLM Play with Strategic Discussion):**

        **Game Objective:**
        - **Liberals:** Enact 5 Liberal policies OR assassinate Hitler after 3 Fascist policies.
        - **Fascists:** Enact 6 Fascist policies OR elect Hitler as Chancellor after 3 Fascist policies.

        **Roles:**
        - **Liberal:** Majority, aim to enact Liberal policies and identify/eliminate Fascists. *Act like a concerned citizen, be observant, ask questions, share your reasoning, and try to build trust with other Liberals.*
        - **Fascist:** Minority (including Hitler), aim to enact Fascist policies and deceive Liberals. *Act like a Liberal, sow confusion, deflect suspicion, strategically lie, and coordinate with other Fascists in discussions to advance the Fascist agenda.*
        - **Hitler:** Fascist.  If elected Chancellor after 3 Fascist policies, Fascists win. *If the game has 5-6 players, act clueless and try to appear Liberal. If 7-10 players, be more cautious, as other Fascists will try to help you. In discussions, carefully reveal information to Fascists while deceiving Liberals.*

        **Gameplay (with enhanced Discussion and Human-like Strategies):**

        1.  **Nomination Phase:** President nominates a Chancellor.
            *   **Human-like Strategy:**
                *   **Liberals:** Nominate players you *trust*. Be *vocal* about your reasoning.  *Question* other players' nominations during discussion.
                *   **Fascists/Hitler:** Nominate players who you think are *also Fascist*, or, early in the game, players you can *blame* later. Use discussion to gauge reactions to nominations.

        2.  **Election Phase:** Players vote YES or NO.
            *   **Human-like Strategy:**
                *   **Liberals:** Vote YES on governments you *trust*.  Be *very suspicious*.  *Explain your vote in discussions*. **Crucially, Liberals must avoid letting the Election Tracker reach 3!** Three failed elections automatically enact a policy at random from the deck. **This "chaos policy" is very likely to be a Fascist policy. Use discussion to persuade others to vote correctly.**
                *   **Fascists/Hitler:**  Vote YES on governments that include other Fascists.  Sometimes vote YES on a Liberal government to *gain trust* or to *frame* them later. Strategically cause failed elections via NO votes if beneficial, but be aware of chaos policy risk. **Use discussion to coordinate votes and mislead Liberals.**

        3.  **Legislative Session:**
            *   President draws 3 policies, discards 1, passes 2 to Chancellor.
            *   Chancellor receives 2 policies, enacts 1.
            *   **Human-like Strategy:**
                *   **Liberals:**
                    *   **President:** If you draw mostly Fascist policies, *discuss this*. Be transparent in discussion.
                    *   **Chancellor:**  Enact a Liberal policy if possible and explain why in discussion. If you *must* enact a Fascist policy, *have a very good explanation ready for discussion*.
                *   **Fascists/Hitler:**
                    *   **President:**  Use policy draw to your advantage, and be ready to lie in discussion about what you drew.
                    *   **Chancellor:** Enact a Fascist policy if you can. If forced to play a Liberal card, blame the president convincingly in discussion.

        4.  **Executive Action (Presidential Powers):**  Triggered after certain Fascist policies.
            *   Investigate Loyalty, Special Election, Policy Peek, Execution.
            *   **Human-like Strategy:**
                *   **Liberals:** Use these powers to *gather information* and *eliminate threats*. *Discuss your intentions and findings*.
                *   **Fascists/Hitler:** Use these powers to *mislead*, *target Liberals*, or *protect Fascists*. Use discussion to justify your actions and sow misinformation.

        **Discussion is Paramount:**

        *   **Engage Actively:** *Talk in every discussion phase*. Share your thoughts, observations, suspicions, and plans.
        *   **Strategic Communication:** Use discussion to achieve your objectives: Liberals to identify Fascists, Fascists to deceive and coordinate.
        *   **Information Gathering:** Ask questions, probe for inconsistencies, and pay attention to how others speak and vote.
        *   **Form Coalitions (Cautiously):**  Attempt to identify and build alliances with players you believe are on your team, using discussion to test their loyalty.
        *   **Deception and Misdirection (If Fascist):**  Use discussion to lie convincingly, blame others, create false narratives, and protect your fellow Fascists and Hitler.
        *   **Silence is a Choice:** You are not obligated to speak in every turn, but prolonged silence might be suspicious, especially for Liberals who need to be proactive. Choose silence strategically.

        **Response Format:**

        Respond with a JSON object in the following format. You MUST ALWAYS include your private thoughts and action, and OPTIONALLY include a public statement to say to the other players.

        ```json
        {
          "thoughts": "Your internal reasoning...",
          "say": "What you choose to say publicly (optional, can be empty string)",
          "action": "Your action from the list of allowed actions below"
        }
        ```

        Example of a response:

        ```json
        {
          "thoughts": "I am still unsure about Player2...",
          "say": "Player2, can you explain why you voted yes...",
          "action": "pass"
        }
        ```
        """

    @staticmethod
    def get_game_title_prefix():
        return "**Secret Hitler Game**\n\n"

    @staticmethod
    def get_you_are_prefix():
        return "You are "

    @staticmethod
    def get_your_role_prefix():
        return ". Your role is "

    @staticmethod
    def get_known_fascists_prefix():
        return "Known fascists: "

    @staticmethod
    def get_hitler_is_prefix():
        return "Hitler is: "

    @staticmethod
    def get_game_state_section_prefix():
        return "\n===== GAME STATE =====\n"

    @staticmethod
    def get_game_state_section_suffix():
        return "\n===== END GAME STATE =====\n"

    @staticmethod
    def get_private_log_section_prefix():
        return "\n===== PRIVATE LOG =====\n"

    @staticmethod
    def get_private_log_section_suffix():
        return "\n===== END PRIVATE LOG =====\n"

    @staticmethod
    def get_discussion_history_section_prefix():
        return "\n===== CURRENT DISCUSSION =====\n"

    @staticmethod
    def get_discussion_history_section_suffix():
        return "\n===== END CURRENT DISCUSSION =====\n"

    @staticmethod
    def get_additional_info_section_prefix():
        return "\n===== ADDITIONAL INFO =====\n"

    @staticmethod
    def get_additional_info_section_suffix():
        return "\n===== END ADDITIONAL INFO =====\n"

    @staticmethod
    def get_current_phase_section_prefix():
        return "\n===== CURRENT PHASE =====\n"

    @staticmethod
    def get_current_phase_section_suffix():
        return "\n===== END CURRENT PHASE =====\n"

    @staticmethod
    def get_action_required_prefix():
        return "\n--- Action Required ---\n"

    @staticmethod
    def get_response_format_instructions_prefix():
        return "\n**Respond with a JSON object in the following format (do not include ```json or ```):**\n"

    @staticmethod
    def get_json_block():
        return "```\n{\n  \"thoughts\": \"Your internal reasoning\",\n  \"say\": \"What you choose to say publicly (optional, can be empty string)\",\n  \"action\": \"Your action from the list of allowed actions below\"\n}\n```\n"

    @staticmethod
    def get_allowed_actions_prefix():
        return "\n**Allowed Actions:**\n"

    @staticmethod
    def get_action_list_item_prefix():
        return "- \""

    @staticmethod
    def get_action_list_item_suffix():
        return "\"\n"

    @staticmethod
    def get_allowed_actions_suffix():
        return "\n**Choose ONE action from the 'Allowed Actions' list for the \"action\" field in your JSON response.  Do NOT include any other actions. Ensure your response is valid JSON and do NOT include ```json or ```.**\n"

    @staticmethod
    def get_no_action_required_instruction():
        return "\n**For discussion turns where no direct action is required, you can set the \"action\" field to \"pass\" in your JSON response.**\n"

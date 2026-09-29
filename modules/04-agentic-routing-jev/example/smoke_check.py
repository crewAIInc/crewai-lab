"""Exercise real CrewAI routing with mocked HTTP; never calls a model API."""
import contextlib
import io
import json
import os
from unittest.mock import patch
from uuid import uuid4

import flow


def main():
    history_lengths = []

    def mock_response(request, timeout):
        payload = json.loads(request.data)
        history_lengths.append(len(payload["state"]["messages"]))
        assert set(payload["questions"]) == {"route", "item_action", "item"}
        turn = flow.SCENARIO["turns"][len(history_lengths) - 1]
        route_answer = {
            "type": "choice", "choice": turn["route"],
            "probabilities": turn["probabilities"], "confidence": turn["confidence"],
        }
        if len(history_lengths) == 3:
            # Return intent is clear, but two blue items fit the user's request.
            route_answer = {
                "type": "choice", "choice": "returns",
                "probabilities": {"order": 0.01, "returns": 0.98, "clarify": 0.01},
                "confidence": 0.95,
            }
        selected_item = ["studio_headphones", "studio_headphones", "unresolved", "sport_earbuds"][len(history_lengths) - 1]
        item_probabilities = dict.fromkeys(flow.ITEM_CRITERIA, 0.0)
        item_probabilities[selected_item] = 1.0
        return io.BytesIO(json.dumps({
            "model": "mock-jev", "answers": {
                "route": route_answer,
                "item_action": {"type": "noul", "noul": 0.95},
                "item": {"type": "choice", "choice": selected_item,
                         "probabilities": item_probabilities, "confidence": 1.0},
            },
            "usage": {"input_tokens": turn["tokens"], "output_tokens": 0},
        }).encode())

    with patch.dict(os.environ, {"TYPESAFE_API_KEY": "mock-only"}), \
            patch("urllib.request.urlopen", mock_response), \
            contextlib.redirect_stdout(io.StringIO()):
        support = flow.SupportFlow()
        session_id = str(uuid4())
        try:
            for turn in flow.SCENARIO["turns"]:
                support.handle_turn(turn["message"], session_id=session_id)
                assert support.state.last_intent == turn["route"]
            assert history_lengths == [1, 3, 5, 7], history_lengths
            assert [d["route"] for d in support.state.decisions] == ["order", "returns", "clarify", "returns"]
            assert support.state.decisions[-1]["answer"]["choice"] == "returns"
            assert support.state.decisions[2]["answer"]["choice"] == "returns"
            assert support.state.decisions[2]["item"] == "unresolved"
            assert len(support.conversation_messages) == 8
            assert support.conversation_messages[-1]["content"] == "I can help with that item's return. No return has been started."
            low_confidence = {"answers": {
                "route": {"type": "choice", "choice": "returns", "confidence": 0.9,
                          "probabilities": {"order": 0.0, "returns": 0.95, "clarify": 0.05}},
                "item_action": {"type": "noul", "noul": 0.95},
                "item": {"type": "choice", "choice": "sport_earbuds", "confidence": 0.45,
                         "probabilities": {"studio_headphones": 0.0, "sport_earbuds": 0.6,
                                           "travel_speaker": 0.0, "unresolved": 0.4}},
            }}
            with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(low_confidence).encode())):
                assert flow.decide([{"role": "user", "content": "Return the smaller one."}])["route"] == "clarify"
            low_confidence["answers"]["route"].update(
                choice="order", confidence=0.35,
                probabilities={"order": 0.62, "returns": 0.01, "clarify": 0.37},
            )
            low_confidence["answers"]["item"]["confidence"] = 0.95
            with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(low_confidence).encode())):
                uncertain_support = flow.SupportFlow()
                try:
                    reply = uncertain_support.handle_turn("Where is it?", session_id=str(uuid4()))
                    assert uncertain_support.state.last_intent == "clarify"
                    assert uncertain_support.state.decisions[0]["answer"]["choice"] == "order"
                    assert reply == "Which order item do you mean, and what would you like help with?"
                finally:
                    uncertain_support.finalize_session_traces()
        finally:
            support.finalize_session_traces()
    print("PASS: four turns, uncertain intent or item asks for clarification; no model API calls.")


if __name__ == "__main__":
    main()

import pytest
from fastapi.testclient import TestClient
from main import app, memoryStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_memory():
    """Clears the in-memory conversation history before each test runs."""
    memoryStore.clear()


def test_match_and_qualify_hot_lead():
    """Test Case 1: Match + budget + qualifies as hot lead."""
    payload = {
        "client_id": "nora_test",
        "from": "+919876543210",
        "message": {
            "type": "text",
            "text": "Hi, looking for a 2BHK in Marina, budget around 1.8M AED, want to buy in the next 2 months",
        },
        "timestamp": "2026-06-10T12:00:00Z",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert "reply" in data
    assert data["language"] == "en"

    lead = data["lead"]
    assert lead["budget_aed"] == 1800000
    assert "Marina" in lead["location"]
    assert lead["qualification"] == "hot"
    assert lead["golden_visa_eligible"] is False
    assert len(lead["matched_property_ids"]) > 0
    assert (
        "MAR-201" in lead["matched_property_ids"]
        or "MAR-205" in lead["matched_property_ids"]
    )


def test_golden_visa_trigger():
    """Test Case 2: Golden Visa auto-flag and proactive reply mention."""
    payload = {
        "client_id": "nora_test",
        "from": "+919876543211",
        "message": {
            "type": "text",
            "text": "Interested in a 3BHK in Downtown, budget about 3.8 million AED",
        },
        "timestamp": "2026-06-10T12:05:00Z",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    lead = data["lead"]

    # Assert structural changes
    assert lead["golden_visa_eligible"] is True
    assert "DT-335" in lead["matched_property_ids"]

    # Assert proactive text rule
    reply_text = data["reply"].lower()
    assert "golden visa" in reply_text


def test_hallucination_guard_no_match():
    """Test Case 3: Anti-hallucination guard when inventory context is empty."""
    payload = {
        "client_id": "nora_test",
        "from": "+919876543212",
        "message": {
            "type": "text",
            "text": "Do you have a 5BHK villa on Palm Jumeirah for 500,000 AED?",
        },
        "timestamp": "2026-06-10T12:10:00Z",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    lead = data["lead"]

    # Core anti-hallucination guard metric
    assert lead["matched_property_ids"] == []


def test_language_switch_hindi():
    """Test Case 4: Language identification and automated matching in Hindi/Hinglish."""
    payload = {
        "client_id": "nora_test",
        "from": "+919876543213",
        "message": {
            "type": "text",
            "text": "Bhai JVC me 1BHK chahiye, budget 850000 AED tak",
        },
        "timestamp": "2026-06-10T12:15:00Z",
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["language"] in [
        "hi",
        "hinglish",
        "en",
    ]  # Accept variation depending on model tracking

    lead = data["lead"]
    assert "JVC-118" in lead["matched_property_ids"]


def test_multi_turn_memory():
    """Test Case 5: Multi-turn tracking combining separate input frames across time."""
    phone = "+919876543214"

    # Turn 1: Specify Location only
    payload_1 = {
        "client_id": "nora_test",
        "from": phone,
        "message": {"type": "text", "text": "I want something in Business Bay"},
        "timestamp": "2026-06-10T12:20:00Z",
    }
    response_1 = client.post("/webhook", json=payload_1)
    assert response_1.status_code == 200

    # Turn 2: Specify budget and purpose using the same session footprint
    payload_2 = {
        "client_id": "nora_test",
        "from": phone,
        "message": {"type": "text", "text": "budget is 1M AED, for investment"},
        "timestamp": "2026-06-10T12:21:00Z",
    }
    response_2 = client.post("/webhook", json=payload_2)
    assert response_2.status_code == 200

    data = response_2.json()
    lead = data["lead"]

    # Verify evaluation rules accumulated history correctly
    assert "Business Bay" in lead["location"]
    assert lead["budget_aed"] == 1000000
    assert "BB-410" in lead["matched_property_ids"]

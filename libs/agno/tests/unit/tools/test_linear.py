from unittest.mock import patch

import pytest

from agno.tools.linear import LinearTools


@pytest.fixture
def linear_tools():
    return LinearTools(api_key="test-key")


# === Initialization ===


def test_init_requires_api_key():
    with patch.dict("os.environ", clear=True):
        with pytest.raises(ValueError, match="Linear API key"):
            LinearTools()


def test_init_registers_default_tools():
    tools = LinearTools(api_key="test-key")
    names = [f.name for f in tools.functions.values()]
    assert "update_issue" in names
    assert len(names) == 8


# === update_issue ===


def _issue_update_payload(title: str = "New title"):
    return {
        "issueUpdate": {
            "success": True,
            "issue": {
                "id": "issue-1",
                "title": title,
                "state": {"id": "state-1", "name": "Todo"},
            },
        }
    }


def test_update_issue_sends_only_provided_fields(linear_tools):
    with patch.object(linear_tools, "_execute_query", return_value=_issue_update_payload()) as mock_query:
        result = linear_tools.update_issue("issue-1", title="New title")

    assert result is not None
    variables = mock_query.call_args[0][1]
    assert variables == {"issueId": "issue-1", "input": {"title": "New title"}}


def test_update_issue_state_change_sends_state_id(linear_tools):
    """The docstring promises state updates; $title: String! rejects title=None."""
    with patch.object(linear_tools, "_execute_query", return_value=_issue_update_payload()) as mock_query:
        result = linear_tools.update_issue("issue-1", title=None, state_id="state-2")

    assert result is not None
    variables = mock_query.call_args[0][1]
    assert variables == {"issueId": "issue-1", "input": {"stateId": "state-2"}}
    assert "title" not in variables["input"]


def test_update_issue_with_no_fields_returns_none_without_querying(linear_tools):
    """title=None means 'unchanged' per the docstring, not a null $title binding."""
    with patch.object(linear_tools, "_execute_query") as mock_query:
        result = linear_tools.update_issue("issue-1", title=None)

    assert result is None
    mock_query.assert_not_called()


def test_update_issue_unsuccessful_returns_none(linear_tools):
    payload = {"issueUpdate": {"success": False, "issue": None}}
    with patch.object(linear_tools, "_execute_query", return_value=payload):
        result = linear_tools.update_issue("issue-1", title="New title")

    assert result is None

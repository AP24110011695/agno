"""Unit tests for AgentQLTools class."""

from unittest.mock import MagicMock, Mock, patch

import pytest

# Check if agentql can be imported without errors
# The library may be installed but have broken dependencies (playwright_stealth)
try:
    import agentql  # noqa: F401

    AGENTQL_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    AGENTQL_AVAILABLE = False

# Skip entire module if agentql is not properly available
if not AGENTQL_AVAILABLE:
    pytest.skip("agentql not available or has broken dependencies", allow_module_level=True)

from agno.tools.agentql import AgentQLTools


@pytest.fixture
def mock_playwright():
    """Create a mock Playwright instance.

    The browser is entered as a context manager by the tools, so the mock
    must support the protocol (MagicMock) and yield itself on __enter__.
    """
    with patch("agno.tools.agentql.sync_playwright") as mock_pw:
        mock_browser = MagicMock()
        mock_page = Mock()
        mock_browser.__enter__.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        yield mock_pw


@pytest.fixture
def mock_agentql():
    """Create a mock AgentQL wrapper."""
    with patch("agno.tools.agentql.agentql") as mock_agentql_module:
        wrapped_page = Mock()
        mock_agentql_module.wrap.return_value = wrapped_page
        yield mock_agentql_module, wrapped_page


@pytest.fixture
def agentql_tools():
    """Create AgentQLTools instance with test API key."""
    with patch.dict("os.environ", {"AGENTQL_API_KEY": "test_key"}):
        return AgentQLTools()


def test_init_with_api_key():
    """Test initialization with API key."""
    tools = AgentQLTools(api_key="test_key")
    assert tools.api_key == "test_key"


def test_init_without_api_key():
    """Test initialization without API key."""
    with patch.dict("os.environ", clear=True):
        with pytest.raises(ValueError, match="AGENTQL_API_KEY not set"):
            AgentQLTools()


def test_scrape_website_no_url(agentql_tools):
    """Test scraping with no URL provided."""
    result = agentql_tools.scrape_website("")
    assert result == "No URL provided"


def test_scrape_website_no_api_key():
    """Test scraping without API key."""
    with patch.dict("os.environ", clear=True):
        with pytest.raises(ValueError, match="AGENTQL_API_KEY not set"):
            tools = AgentQLTools()
            tools.scrape_website("https://example.com")


def test_custom_scrape_no_query(agentql_tools):
    """Test custom scraping without a query."""
    result = agentql_tools.custom_scrape_website("https://example.com")
    assert "Custom AgentQL query not provided" in result


def test_scrape_website_success(mock_playwright, mock_agentql, agentql_tools):
    """Test successful website scraping."""
    # Unpack the mock_agentql fixture
    mock_agentql_module, wrapped_page = mock_agentql

    # Set up the mock response for query_data
    wrapped_page.query_data.return_value = {
        "text_content": ["Example Domain", "This domain is for use in illustrative examples"]
    }

    result = agentql_tools.scrape_website("https://example.com")

    # Verify the page navigation occurred
    wrapped_page.goto.assert_called_once_with("https://example.com")

    # Verify query_data was called with correct query
    wrapped_page.query_data.assert_called_once_with("""
        {
            text_content[]
        }
        """)

    # Check the result contains expected content
    assert "Example Domain" in result
    assert "This domain is for use in illustrative examples" in result
    assert isinstance(result, str)


def test_custom_scrape_returns_values_not_keys(mock_playwright, mock_agentql):
    """The scraped values are returned, not the query's field names."""
    _, wrapped_page = mock_agentql
    wrapped_page.query_data.return_value = {"title": "AgentQL Guide", "price": "$9.99"}

    with patch.dict("os.environ", {"AGENTQL_API_KEY": "test_key"}):
        tools = AgentQLTools(agentql_query="{ title price }")
    result = tools.custom_scrape_website("https://example.com")

    assert result == "AgentQL Guide $9.99"


def test_custom_scrape_flattens_lists_and_blocks(mock_playwright, mock_agentql):
    """List values and nested blocks contribute their items to the text."""
    _, wrapped_page = mock_agentql
    wrapped_page.query_data.return_value = {
        "items": ["first", "second"],
        "block": {"inner": "nested text", "empty": None},
    }

    with patch.dict("os.environ", {"AGENTQL_API_KEY": "test_key"}):
        tools = AgentQLTools(agentql_query="{ items[] block { inner } }")
    result = tools.custom_scrape_website("https://example.com")

    assert "first" in result
    assert "second" in result
    assert "nested text" in result
    assert "None" not in result

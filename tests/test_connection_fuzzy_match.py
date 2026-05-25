import pytest
from unittest.mock import MagicMock, patch
from quads_client.connection import ConnectionManager, ConnectionError


@pytest.fixture
def mock_config_fuzzy():
    """Mock config with various server name formats"""
    config = MagicMock()
    config.get_all_servers.return_value = {
        "quads2-dev.rdu2.scalelab": {
            "url": "https://quads2-dev.rdu2.scalelab.example.com",
            "username": "user@example.com",
            "password": "pass123",
        },
        "quads2-stage.rdu2.scalelab.example.com": {
            "url": "https://quads2-stage.rdu2.scalelab.example.com",
            "username": "user@example.com",
            "password": "pass123",
        },
        "quads-prod": {
            "url": "https://quads-prod.example.com",
            "username": "user@example.com",
            "password": "pass123",
        },
    }
    config.get_server_url.side_effect = lambda name: config.get_all_servers()[name]["url"]
    config.get_server_credentials.side_effect = lambda name: (
        config.get_all_servers()[name]["username"],
        config.get_all_servers()[name]["password"],
    )
    config.get_server_verify.return_value = True
    config.get_server_api_token.return_value = ""
    return config


def test_resolve_server_exact_match(mock_config_fuzzy):
    """Test exact server name match"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("quads2-dev.rdu2.scalelab")
    assert result == "quads2-dev.rdu2.scalelab"


def test_resolve_server_fqdn_match(mock_config_fuzzy):
    """Test matching by full FQDN from URL"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("quads2-dev.rdu2.scalelab.example.com")
    assert result == "quads2-dev.rdu2.scalelab"


def test_resolve_server_url_match_with_protocol(mock_config_fuzzy):
    """Test matching by URL with protocol"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("https://quads2-dev.rdu2.scalelab.example.com")
    assert result == "quads2-dev.rdu2.scalelab"


def test_resolve_server_prefix_match(mock_config_fuzzy):
    """Test prefix matching when unique"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("quads-prod")
    assert result == "quads-prod"


def test_resolve_server_no_match(mock_config_fuzzy):
    """Test unknown server returns None"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("unknown-server")
    assert result is None


def test_resolve_server_stage_fqdn(mock_config_fuzzy):
    """Test stage server FQDN exact match"""
    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("quads2-stage.rdu2.scalelab.example.com")
    assert result == "quads2-stage.rdu2.scalelab.example.com"


def test_connect_with_fqdn(mock_config_fuzzy, mock_api):
    """Test connecting with FQDN when config has shortened name resolves via URL match"""
    conn = ConnectionManager(mock_config_fuzzy)
    with patch("quads_client.connection.QuadsApi", return_value=mock_api):
        conn.connect("quads2-dev.rdu2.scalelab.example.com")
    assert conn._current_server == "quads2-dev.rdu2.scalelab"


def test_connect_unknown_server_error(mock_config_fuzzy):
    """Test connecting to unknown server raises error"""
    conn = ConnectionManager(mock_config_fuzzy)
    with pytest.raises(ConnectionError) as exc_info:
        conn.connect("nonexistent-server.example.com")
    assert "Unknown server" in str(exc_info.value)


def test_resolve_ambiguous_prefix(mock_config_fuzzy):
    """Test that ambiguous prefixes are handled"""
    # Add another server with similar prefix
    servers = mock_config_fuzzy.get_all_servers()
    servers["quads2-dev.rdu3.scalelab"] = {
        "url": "https://quads2-dev.rdu3.scalelab.example.com",
        "username": "user@example.com",
        "password": "pass123",
    }
    mock_config_fuzzy.get_all_servers.return_value = servers

    conn = ConnectionManager(mock_config_fuzzy)
    # "quads2-dev" prefix matches both quads2-dev.rdu2.scalelab and quads2-dev.rdu3.scalelab
    # Should return one of them (implementation dependent)
    result = conn._resolve_server_name("quads2-dev")
    assert result in ["quads2-dev.rdu2.scalelab", "quads2-dev.rdu3.scalelab"]


def test_resolve_http_protocol(mock_config_fuzzy):
    """Test matching URL with HTTP protocol"""
    # Add HTTP server
    servers = mock_config_fuzzy.get_all_servers()
    servers["quads-dev-http"] = {
        "url": "http://quads-dev.internal.local",
        "username": "user@example.com",
        "password": "pass123",
    }
    mock_config_fuzzy.get_all_servers.return_value = servers
    mock_config_fuzzy.get_server_url.side_effect = lambda name: servers[name]["url"]

    conn = ConnectionManager(mock_config_fuzzy)
    result = conn._resolve_server_name("quads-dev.internal.local")
    assert result == "quads-dev-http"


def test_resolve_url_with_trailing_slash(mock_config_fuzzy):
    """Test matching URL even if it has trailing slash"""
    conn = ConnectionManager(mock_config_fuzzy)
    # Should strip trailing slash and match
    result = conn._resolve_server_name("https://quads-prod.example.com/")
    assert result == "quads-prod"

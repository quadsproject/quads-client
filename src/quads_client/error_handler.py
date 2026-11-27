"""Error handling utilities for QUADS Client"""


def auto_refresh_on_auth_error(shell, api_call_func, *args, **kwargs):
    """
    Wrapper that automatically refreshes token on 401 errors

    Args:
        shell: QuadsClientShell instance
        api_call_func: Function to call (e.g., shell.connection.api.create_assignment)
        *args, **kwargs: Arguments to pass to api_call_func

    Returns:
        Result from api_call_func

    Raises:
        Exception if the operation fails even after token refresh
    """
    try:
        return api_call_func(*args, **kwargs)
    except Exception as e:
        error_str = str(e).lower()
        # Check if this is an authentication error
        if (
            type(e).__name__ == "APIUnauthorized"
            or "401" in str(e)
            or "unauthorized" in error_str
            or "token" in error_str
        ):
            # Try to refresh the token
            if shell.connection and shell.connection.refresh_token():
                # Retry the operation with fresh token
                try:
                    return api_call_func(*args, **kwargs)
                except Exception as retry_error:
                    # Still failed after refresh
                    raise retry_error
        # Not an auth error, or refresh failed - propagate original error
        raise e


def handle_api_error(shell, error, operation="operation"):
    """
    Handle API errors with user-friendly messages

    Args:
        shell: QuadsClientShell instance
        error: Exception raised during API call
        operation: Description of the operation that failed
    """
    error_msg = str(error).lower()

    # Handle server-enforced limit violations
    if "host limit exceeded" in error_msg or "ssm_host_limit" in error_msg:
        shell.perror(f"Server limit: {error}")
        shell.perror("Hint: SSM users can schedule max 10 hosts per assignment")
    elif "cloud limit exceeded" in error_msg or "user cloud limit" in error_msg or "ssm_user_cloud_limit" in error_msg:
        shell.perror(f"Server limit: {error}")
        shell.perror("Hint: You have 3 active assignments. Terminate one first with 'terminate'")
        shell.perror("Run 'my-assignments' to see your active assignments")
    # Handle ticketing system errors (SSM should not require tickets)
    # Check for missing ticket first (more specific)
    elif "missing" in error_msg and "ticket" in error_msg:
        shell.perror(f"Server configuration issue: {error}")
        shell.perror("Hint: The server requires a ticket number but auto-ticket creation is disabled.")
        shell.perror("Server admin should enable: 'ssm_jira_create_ticket: true' in server config")
    # Check for Jira errors
    elif "ticketing system not configured" in error_msg or "jira" in error_msg:
        shell.perror(f"Server configuration issue: {error}")
        shell.perror("Hint: The server has automatic ticket creation enabled but Jira is not configured.")
        shell.perror("")
        shell.perror("Server admin should either:")
        shell.perror("  1. Configure Jira credentials in QUADS config (jira_url, jira_username, jira_password), OR")
        shell.perror("  2. Disable automatic tickets: set 'ssm_jira_create_ticket: false' in server config")
    # Handle authentication errors
    elif type(error).__name__ == "APIUnauthorized" or "401" in str(error) or "unauthorized" in error_msg:
        shell.perror(f"Authentication failed: {error}")
        shell.perror("Hint: Run 'login' to refresh your session")
    # Handle permission errors
    elif "403" in str(error) or "forbidden" in error_msg:
        shell.perror(f"Permission denied: {error}")
    # Handle not found errors
    elif "404" in str(error) or "not found" in error_msg:
        shell.perror(f"Not found: {error}")
    # Handle server errors
    elif "500" in str(error) or "internal server" in error_msg:
        shell.perror(f"Server error: {error}")
        shell.perror("Hint: Contact your QUADS administrator if this persists")
    # Handle connection errors
    elif "connection" in error_msg or "timeout" in error_msg:
        shell.perror(f"Connection failed: {error}")
        shell.perror("Hint: Check 'status' or run 'connect <server>'")
    # Generic error
    else:
        shell.perror(f"{operation} failed: {error}")


def require_connection(shell):
    """Check if connected to a server"""
    if not shell.connection or not shell.connection.is_connected:
        shell.perror("Not connected to any server")
        return False
    return True


def require_auth(shell):
    """Check if user is authenticated"""
    if not require_connection(shell):
        return False
    if not shell.connection.is_authenticated:
        shell.perror("Not authenticated. Use 'login' command first.")
        return False
    return True


def require_admin(shell):
    """Check if user has admin role"""
    if not require_auth(shell):
        return False
    if not shell.connection.is_admin:
        shell.perror("Permission denied: This command requires admin role")
        return False
    return True

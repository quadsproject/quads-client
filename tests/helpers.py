def completions_to_list(completions):
    """Convert cmd2 Completions to a plain list of strings for assertions."""
    if hasattr(completions, "to_strings"):
        return list(completions.to_strings())
    return list(completions)

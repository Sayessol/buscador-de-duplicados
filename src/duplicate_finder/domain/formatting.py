"""Human-readable formatting of values shown to the user."""


def format_size(bytes_: float) -> str:
    """Converts a number of bytes to readable text (B, KB, MB, GB...).

    Same behaviour as the original console script: divides by
    1024 and shows one decimal.
    """
    value = float(bytes_)
    # Moves up a unit while the number does not fit below 1024.
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"        # just in case (petabytes)

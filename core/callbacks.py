"""Types repeated across several core modules (names only, no logic)."""

from collections.abc import Callable

# Function that receives the progress of a long operation: (done, total, message).
ProgressCallback = Callable[[int, int, str], None]

# Function that says whether the user has asked to cancel.
CancelledCallback = Callable[[], bool]

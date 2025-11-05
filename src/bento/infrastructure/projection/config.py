"""Configuration constants for OutboxProjector.

Based on Legend system's projector configuration.
"""

# Batch processing
DEFAULT_BATCH_SIZE = 200  # Number of events to process per batch
TRY_BATCH = 200  # Alias for consistency with Legend

# Sleep intervals (seconds)
SLEEP_BUSY = 0.1  # Sleep when backlog exists (quick polling)
SLEEP_IDLE = 1.0  # Sleep when queue is empty
SLEEP_IDLE_MAX = 5.0  # Maximum sleep time when idle

# Retry configuration
MAX_RETRY = 5  # Maximum retry attempts before marking as error

# Status values (matching Legend's naming)
STATUS_NEW = "NEW"  # New event, not yet published
STATUS_SENT = "SENT"  # Successfully published
STATUS_ERR = "ERR"  # Failed after max retries

# Legacy status values (for backward compatibility)
STATUS_PENDING = "pending"
STATUS_PUBLISHING = "publishing"
STATUS_PUBLISHED = "published"
STATUS_ERROR = "error"

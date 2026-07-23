"""Application-wide constants shared across modules.

Centralising these here prevents magic string duplication and ensures
a single source of truth for all status values.
"""

# ---------------------------------------------------------------------------
# Job status strings — use these everywhere instead of raw string literals
# ---------------------------------------------------------------------------
JOB_STATUS_PENDING = "PENDING"
JOB_STATUS_PROCESSING = "PROCESSING"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_FAILED = "FAILED"
JOB_STATUS_CANCELLED = "CANCELLED"

TERMINAL_JOB_STATUSES: frozenset[str] = frozenset(
    {JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED}
)

ACTIVE_JOB_STATUSES: frozenset[str] = frozenset(
    {JOB_STATUS_PENDING, JOB_STATUS_PROCESSING}
)

# ---------------------------------------------------------------------------
# Workflow identifiers
# ---------------------------------------------------------------------------
WORKFLOW_CATALOG_IMAGE = "CATALOG_IMAGE"
WORKFLOW_VIRTUAL_TRY_ON = "VIRTUAL_TRY_ON"
WORKFLOW_GEMSTONE_COLOR_CHANGE = "GEMSTONE_COLOR_CHANGE"
WORKFLOW_BACKGROUND_REPLACEMENT = "BACKGROUND_REPLACEMENT"
WORKFLOW_LUXURY_ENHANCEMENT = "LUXURY_ENHANCEMENT"
WORKFLOW_CUSTOM_PROMPT = "CUSTOM_PROMPT"
# Legacy — kept for history regenerate compatibility
WORKFLOW_JEWELRY_ON_MODEL = "JEWELRY_ON_MODEL"
WORKFLOW_CUSTOMER_TRY_ON = "CUSTOMER_TRY_ON"
WORKFLOW_REFERENCE_STYLE_MATCH = "REFERENCE_STYLE_MATCH"
WORKFLOW_BULK_GENERATION = "BULK_GENERATION"

BULK_SUPPORTED_WORKFLOWS: frozenset[str] = frozenset(
    {
        WORKFLOW_CATALOG_IMAGE,
        WORKFLOW_VIRTUAL_TRY_ON,
        WORKFLOW_GEMSTONE_COLOR_CHANGE,
        WORKFLOW_BACKGROUND_REPLACEMENT,
        WORKFLOW_LUXURY_ENHANCEMENT,
        WORKFLOW_CUSTOM_PROMPT,
        # legacy remapped
        WORKFLOW_JEWELRY_ON_MODEL,
        WORKFLOW_CUSTOMER_TRY_ON,
        WORKFLOW_REFERENCE_STYLE_MATCH,
    }
)

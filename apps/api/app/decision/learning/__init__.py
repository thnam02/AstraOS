"""Intent → Offer → Outcome learning. Trained only on synthetic outcomes."""

LEARNING_DISCLAIMER = (
    "This model is trained on simulated buyer-agent outcomes and is "
    "included to demonstrate AstraOS's learning architecture. It should "
    "not be interpreted as a real-world conversion model."
)
SCORE_LABEL = "Synthetic Response Score"
FEATURE_SCHEMA_VERSION = "features.v1"
DATASET_VERSION_NAME = "synthetic.arena.v1"
TARGET_NAME = "offer_selected"
TARGET_DEFINITION = (
    "Y=1 if the simulated Buyer Agent selected this policy-safe, "
    "constraint-valid offer; Y=0 otherwise. Policy-unsafe and "
    "hard-constraint-invalid offers are excluded from training."
)
FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "buyer_utility",
        "utility_score",
        "simulated_utility",
        "utility_total",
        "selected",
        "accepted",
        "transacted",
        "outcome_type",
        "outcome_source",
        "strategy_name",
        "selected_strategy",
        "transaction_state",
        "y",
        "label",
        "target",
    }
)

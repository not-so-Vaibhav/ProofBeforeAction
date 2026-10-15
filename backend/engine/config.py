# Risk scoring weights
WEIGHT_S: float = 0.30  # Impact severity
WEIGHT_D: float = 0.25  # Dependency exposure
WEIGHT_V: float = 0.25  # Validation failures
WEIGHT_I: float = 0.10  # Irreversibility
WEIGHT_U: float = 0.10  # Uncertainty

# Decision score thresholds
THRESHOLD_REVIEW: float = 30.0
THRESHOLD_BLOCK: float = 70.0

import random

from abc import ABC, abstractmethod
from swesmith.constants import DEFAULT_PM_LIKELIHOOD, BugRewrite, CodeEntity


class ProceduralModifier(ABC):
    """Abstract base class for procedural modifiers."""

    min_complexity: int = 3
    max_complexity: int = float("inf")

    # To be defined in subclasses
    explanation: str
    name: str
    conditions: list = []

    def __init__(self, likelihood: float = DEFAULT_PM_LIKELIHOOD, seed: float = 24):
        assert 0 <= likelihood <= 1, "Likelihood must be between 0 and 1."
        self.rand = random.Random(seed)
        self.likelihood = likelihood

    def flip(self) -> bool:
        return self.rand.random() < self.likelihood

    def can_change(self, code_entity: CodeEntity) -> bool:
        """Check if the CodeEntity satisfies the conditions of the modifier."""
        return (
            all(c in code_entity._tags for c in self.conditions)
            and self.min_complexity <= code_entity.complexity <= self.max_complexity
        )

    @abstractmethod
    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """
        Apply procedural modifications to the given code entity.

        Args:
            code_entity: The code entity to modify

        Returns:
            BugRewrite if modification was successful, None otherwise
        """
        pass

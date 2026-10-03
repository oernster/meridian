from dataclasses import dataclass


class FilterSyntaxError(ValueError):
    """A filter that does not follow MMSP Appendix A; the message says where."""


@dataclass(frozen=True, slots=True)
class FilterExpression:
    expr: str

    def __post_init__(self) -> None:
        if not isinstance(self.expr, str):
            raise TypeError("Filter expression must be a string")
        stripped = self.expr.strip()
        if not stripped:
            raise ValueError("Filter expression must not be empty")
        object.__setattr__(self, "expr", stripped)

    def __bool__(self) -> bool:
        return bool(self.expr)

from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.golang.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)

MODIFIERS_GOLANG: list[ProceduralModifier] = [
    ControlIfElseInvertModifier(likelihood=0.25),
    ControlShuffleLinesModifier(likelihood=0.25),
]

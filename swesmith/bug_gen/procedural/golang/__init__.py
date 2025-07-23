from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.golang.control_flow import ControlIfElseInvertModifier


MODIFIERS_GOLANG: list[ProceduralModifier] = [
    ControlIfElseInvertModifier(likelihood=0.25),
]

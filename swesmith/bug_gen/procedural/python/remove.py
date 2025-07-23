import libcst

from swesmith.bug_gen.procedural.python.base import PythonProceduralModifier
from swesmith.constants import CodeProperty


class RemoveLoopModifier(PythonProceduralModifier):
    explanation: str = "There is one or more missing loops that is causing the bug."
    name: str = "func_pm_remove_loop"
    conditions: list = [
        CodeProperty.IS_FUNCTION,
        CodeProperty.HAS_LOOP,
    ]

    class Transformer(PythonProceduralModifier.Transformer):
        def leave_For(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node

        def leave_While(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node


class RemoveConditionalModifier(PythonProceduralModifier):
    explanation: str = "There is one or more missing conditionals that causes the bug."
    name: str = "func_pm_remove_cond"
    conditions: list = [
        CodeProperty.IS_FUNCTION,
        CodeProperty.HAS_IF,
    ]

    class Transformer(PythonProceduralModifier.Transformer):
        def leave_If(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node


class RemoveAssignModifier(PythonProceduralModifier):
    explanation: str = "There is likely a missing assignment in the code."
    name: str = "func_pm_remove_assign"
    conditions: list = [
        CodeProperty.IS_FUNCTION,
        CodeProperty.HAS_ASSIGNMENT,
    ]

    class Transformer(PythonProceduralModifier.Transformer):
        def leave_Assign(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node

        def leave_AugAssign(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node


class RemoveWrapperModifier(PythonProceduralModifier):
    explanation: str = "There are missing wrappers (with, try blocks) in the code."
    name: str = "func_pm_remove_wrapper"
    conditions: list = [
        CodeProperty.IS_FUNCTION,
        CodeProperty.HAS_WRAPPER,
    ]

    class Transformer(PythonProceduralModifier.Transformer):
        def leave_With(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node

        def leave_AsyncWith(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node

        def leave_Try(self, original_node, updated_node):
            return libcst.RemoveFromParent() if self.flip() else updated_node

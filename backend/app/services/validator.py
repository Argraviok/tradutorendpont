import ast
from typing import Optional
from pydantic import BaseModel


class ASTValidationResult(BaseModel):
    is_valid: bool
    syntax_error: Optional[str] = None
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    total_lines: int = 0
    detected_routes: list[str] = []
    detected_models: list[str] = []
    detected_imports: list[str] = []


def validate_python_code(code: str) -> ASTValidationResult:
    """
    Analyzes and validates the generated Python code using the native ast module.
    Verifies that the code compiles without any syntax errors and inspects
    defined routes, classes (Pydantic models), and imports.
    """
    total_lines = len(code.splitlines())
    if not code.strip():
        return ASTValidationResult(
            is_valid=False,
            syntax_error="O código está vazio.",
            total_lines=0
        )

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ASTValidationResult(
            is_valid=False,
            syntax_error=e.msg,
            error_line=e.lineno,
            error_column=e.offset,
            total_lines=total_lines
        )
    except Exception as e:
        return ASTValidationResult(
            is_valid=False,
            syntax_error=str(e),
            total_lines=total_lines
        )

    detected_routes = []
    detected_models = []
    detected_imports = []

    for node in ast.walk(tree):
        # Detect imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                detected_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                detected_imports.append(f"{module}.{alias.name}")

        # Detect Pydantic models / classes
        elif isinstance(node, ast.ClassDef):
            detected_models.append(node.name)

        # Detect route decorators e.g. @app.get(...), @router.post(...)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                dec_repr = ""
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        dec_repr = f"{getattr(decorator.func.value, 'id', '')}.{decorator.func.attr}"
                    elif isinstance(decorator.func, ast.Name):
                        dec_repr = decorator.func.id
                    # Try to extract route path if present
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        dec_repr += f"('{decorator.args[0].value}')"
                elif isinstance(decorator, ast.Attribute):
                    dec_repr = f"{getattr(decorator.value, 'id', '')}.{decorator.attr}"
                elif isinstance(decorator, ast.Name):
                    dec_repr = decorator.id

                if any(verb in dec_repr.lower() for verb in ["get", "post", "put", "delete", "patch", "route"]):
                    detected_routes.append(f"{dec_repr} -> def {node.name}()")

    return ASTValidationResult(
        is_valid=True,
        total_lines=total_lines,
        detected_routes=detected_routes,
        detected_models=detected_models,
        detected_imports=detected_imports
    )

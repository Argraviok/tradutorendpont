import json
import re
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from app.config import get_settings
from app.services.validator import validate_python_code, ASTValidationResult


class EndpointMapping(BaseModel):
    original_route: str = Field(description="Rota original, ex: /api/orders/{id}")
    target_route: str = Field(description="Rota no FastAPI/Flask, ex: /api/orders/{id}")
    http_method: str = Field(description="Método HTTP, ex: GET, POST, PUT, DELETE")
    original_handler: str = Field(description="Nome do método/função original")
    target_function: str = Field(description="Nome da função gerada em Python")


class ModelMapping(BaseModel):
    original_type: str = Field(description="Nome da classe, struct, interface ou tipo original")
    target_pydantic_model: str = Field(description="Nome do modelo Pydantic equivalente em Python")
    fields_summary: str = Field(description="Resumo dos campos mapeados")


class TranspileOutputSchema(BaseModel):
    detected_source_language: str = Field(description="Linguagem e framework identificados no código de origem")
    target_framework: str = Field(description="Framework de destino utilizado (ex: FastAPI ou Flask)")
    python_code: str = Field(description="Código Python completo, sintaticamente válido e sem blocos markdown extras")
    pip_dependencies: list[str] = Field(description="Lista de pacotes pip necessários para rodar o código, ex: ['fastapi', 'pydantic']")
    endpoints_mapping: list[EndpointMapping] = Field(description="Tabela de correspondência 1:1 dos endpoints convertidos")
    models_mapping: list[ModelMapping] = Field(description="Tabela de correspondência de tipos para modelos Pydantic")
    fidelity_notes: list[str] = Field(description="Notas de fidelidade garantindo que nenhuma regra de negócio foi alterada")


class TranspilationResponse(BaseModel):
    success: bool
    source_language: str
    target_framework: str
    python_code: str
    pip_dependencies: list[str] = []
    endpoints_mapping: list[EndpointMapping] = []
    models_mapping: list[ModelMapping] = []
    fidelity_notes: list[str] = []
    validation: ASTValidationResult
    error_message: Optional[str] = None


SYSTEM_PROMPT = """Você é um Transpilador de Código e Engenheiro de APIs ultra-especializado, rigoroso e DETERMINÍSTICO.
Sua ÚNICA missão é transladar os endpoints e modelos fornecidos para Python ({target_framework}) mantendo fidelidade estrita 1:1.

REGRAS ABSOLUTAS ANTI-ALUCINAÇÃO (GROUNDING):
1. FIDELIDADE LÓGICA 1:1: NÃO invente regras de negócio, dados fictícios, entidades ou rotas que não existam no código original.
2. ROTAS E MÉTODOS: Mantenha exatamente os mesmos caminhos de rota (/users/{id}, /v1/items, etc.) e os mesmos métodos HTTP (GET, POST, PUT, DELETE, PATCH).
3. PARÂMETROS: Todos os parâmetros de rota (path params), query strings e headers devem ser mapeados diretamente para a assinatura da função em Python com a tipagem estrita (int, str, UUID, float, Optional[...]).
4. CORPO DA REQUISIÇÃO (PAYLOAD/DTO): Se houver DTOs, classes, structs ou interfaces de payload/body, crie classes Pydantic BaseModel correspondentes com os exatos mesmos campos e tipos equivalentes do Python.
5. STATUS CODES E EXCEÇÕES: Mantenha os mesmos status HTTP de retorno (ex: 200, 201, 204, 400, 404, 500) usando HTTPException do FastAPI ou status codes equivalentes.
6. MODO DE CONVERSÃO:
   - Se modo for 'strict': Replique a lógica linha por linha o mais próximo possível da estrutura original.
   - Se modo for 'idiomatic': Mantenha toda a lógica intacta, mas use as melhores práticas modernas do Python (async/await, Pydantic v2, type hints completos e Depends onde couber).
7. O código Python em `python_code` deve ser código Python puro, pronto para ser gravado em um arquivo .py e compilado via `ast.parse` sem erros de sintaxe (NÃO inclua delimitadores ```python dentro da string json).
"""


async def transpile_api_code(
    code: str,
    source_language: str = "Auto-detect",
    target_framework: str = "FastAPI",
    conversion_mode: str = "strict",
    api_key_override: Optional[str] = None
) -> TranspilationResponse:
    settings = get_settings()
    api_key = api_key_override or settings.gemini_api_key

    if not api_key:
        return TranspilationResponse(
            success=False,
            source_language=source_language,
            target_framework=target_framework,
            python_code="",
            validation=ASTValidationResult(is_valid=False, syntax_error="Chave da API do Gemini não configurada."),
            error_message="Chave da API do Google Gemini não encontrada. Configure no arquivo .env do backend ou informe sua chave diretamente na interface."
        )

    client = genai.Client(api_key=api_key)
    model_name = settings.default_model

    prompt_user = f"""Por favor, transpile o seguinte código de endpoint para Python ({target_framework}).

Configurações:
- Linguagem de Origem declarada: {source_language}
- Framework de Destino: {target_framework}
- Modo de Conversão: {conversion_mode} (strict = fidelidade 1:1 linha por linha; idiomatic = boas práticas FastAPI com Pydantic v2 e async)

CÓDIGO ORIGINAL PARA TRANSPILAR:
```
{code}
```
"""

    formatted_system_prompt = SYSTEM_PROMPT.format(target_framework=target_framework)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_user,
            config=types.GenerateContentConfig(
                temperature=0.0,
                system_instruction=formatted_system_prompt,
                response_mime_type="application/json",
                response_schema=TranspileOutputSchema
            )
        )

        raw_text = response.text or ""
        parsed_data = json.loads(raw_text)
        transpile_output = TranspileOutputSchema(**parsed_data)

        # Clean python code if markdown fences were accidentally embedded
        cleaned_code = transpile_output.python_code.strip()
        if cleaned_code.startswith("```python"):
            cleaned_code = cleaned_code[9:].strip()
        elif cleaned_code.startswith("```"):
            cleaned_code = cleaned_code[3:].strip()
        if cleaned_code.endswith("```"):
            cleaned_code = cleaned_code[:-3].strip()

        # Validate with AST
        ast_result = validate_python_code(cleaned_code)

        return TranspilationResponse(
            success=True,
            source_language=transpile_output.detected_source_language or source_language,
            target_framework=transpile_output.target_framework or target_framework,
            python_code=cleaned_code,
            pip_dependencies=transpile_output.pip_dependencies,
            endpoints_mapping=transpile_output.endpoints_mapping,
            models_mapping=transpile_output.models_mapping,
            fidelity_notes=transpile_output.fidelity_notes,
            validation=ast_result
        )

    except json.JSONDecodeError as jde:
        # Fallback in case raw text wasn't strict JSON
        code_match = re.search(r"```python\s*(.*?)\s*```", response.text or "", re.DOTALL)
        extracted_code = code_match.group(1).strip() if code_match else (response.text or "").strip()
        ast_result = validate_python_code(extracted_code)
        return TranspilationResponse(
            success=True,
            source_language=source_language,
            target_framework=target_framework,
            python_code=extracted_code,
            pip_dependencies=["fastapi", "pydantic", "uvicorn"],
            validation=ast_result,
            fidelity_notes=["Aviso: Resposta extraída via fallback de texto."]
        )

    except Exception as e:
        return TranspilationResponse(
            success=False,
            source_language=source_language,
            target_framework=target_framework,
            python_code="",
            validation=ASTValidationResult(is_valid=False, syntax_error=str(e)),
            error_message=f"Falha ao executar transpilação com Gemini API: {str(e)}"
        )

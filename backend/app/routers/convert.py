from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from app.services.transpiler import transpile_api_code, TranspilationResponse
from app.services.validator import validate_python_code, ASTValidationResult

router = APIRouter(prefix="/api", tags=["Transpilation"])


class TranspileRequest(BaseModel):
    code: str = Field(..., min_length=5, description="Código original da API a ser transpilado")
    source_language: str = Field(default="Auto-detect", description="Linguagem de origem")
    target_framework: str = Field(default="FastAPI", description="Framework de destino (FastAPI ou Flask)")
    conversion_mode: str = Field(default="strict", description="Modo: 'strict' (1:1) ou 'idiomatic'")
    api_key: Optional[str] = Field(default=None, description="Chave opcional da API Gemini fornecida pelo usuário")


class ValidateRequest(BaseModel):
    code: str = Field(..., description="Código Python para validação sintática AST")


class PresetExample(BaseModel):
    id: str
    name: str
    language: str
    target_recommendation: str
    description: str
    code: str


PRESETS: list[PresetExample] = [
    PresetExample(
        id="csharp-aspnet",
        name="C# (ASP.NET Core Controller)",
        language="C# / .NET",
        target_recommendation="FastAPI",
        description="Controller de Usuários com rotas GET por ID, POST com validação de DTO, PUT e DELETE.",
        code="""[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService)
    {
        _userService = userService;
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<UserDto>> GetUserById(int id)
    {
        var user = await _userService.FindByIdAsync(id);
        if (user == null)
        {
            return NotFound(new { message = $"Usuário {id} não encontrado." });
        }
        return Ok(user);
    }

    [HttpPost]
    public async Task<ActionResult<UserDto>> CreateUser([FromBody] CreateUserRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Email))
        {
            return BadRequest(new { error = "O e-mail é obrigatório." });
        }
        var created = await _userService.CreateAsync(request);
        return StatusCode(201, created);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteUser(int id)
    {
        var deleted = await _userService.DeleteAsync(id);
        if (!deleted)
        {
            return NotFound();
        }
        return NoContent();
    }
}

public class CreateUserRequest
{
    public string Name { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string? Role { get; set; }
}

public class UserDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}"""
    ),
    PresetExample(
        id="nodejs-express",
        name="Node.js (Express / TypeScript)",
        language="TypeScript / Express",
        target_recommendation="FastAPI",
        description="Rotas de Produtos com parâmetros de query, paginação e cadastro de produto.",
        code="""import { Router, Request, Response } from 'express';

const router = Router();

interface CreateProductDto {
  title: string;
  price: number;
  category?: string;
  inStock: boolean;
}

// GET /api/products?page=1&limit=10&search=term
router.get('/products', async (req: Request, res: Response) => {
  const page = parseInt(req.query.page as string) || 1;
  const limit = parseInt(req.query.limit as string) || 20;
  const search = req.query.search as string | undefined;

  const results = await productDatabase.findMany({ page, limit, search });
  return res.status(200).json({
    data: results.items,
    total: results.total,
    page,
    limit
  });
});

// POST /api/products
router.post('/products', async (req: Request, res: Response) => {
  const payload: CreateProductDto = req.body;
  if (!payload.title || payload.price <= 0) {
    return res.status(400).json({ error: 'Título inválido ou preço menor/igual a zero.' });
  }

  const newProduct = await productDatabase.insert(payload);
  return res.status(201).json(newProduct);
});

export default router;"""
    ),
    PresetExample(
        id="java-spring",
        name="Java (Spring Boot RestController)",
        language="Java / Spring Boot",
        target_recommendation="FastAPI",
        description="RestController com @GetMapping, @PostMapping, tratamento de Optional e ResponseStatus.",
        code="""@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<OrderResponse> getOrder(@PathVariable("orderId") String orderId) {
        return orderService.findById(orderId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OrderResponse createOrder(@Valid @RequestBody OrderCreateDto dto) {
        return orderService.processOrder(dto);
    }
}

public record OrderCreateDto(
    String customerId,
    List<OrderItemDto> items,
    Double discount
) {}

public record OrderResponse(
    String id,
    String customerId,
    Double totalAmount,
    String status,
    LocalDateTime createdAt
) {}"""
    ),
    PresetExample(
        id="php-laravel",
        name="PHP (Laravel Controller)",
        language="PHP / Laravel",
        target_recommendation="FastAPI",
        description="Controller com validação $request->validate(), resource response e status 201.",
        code="""namespace App\\Http\\Controllers;

use App\\Models\\Customer;
use Illuminate\\Http\\Request;
use Illuminate\\Http\\JsonResponse;

class CustomerController extends Controller
{
    public function show(int $id): JsonResponse
    {
        $customer = Customer::find($id);
        if (!$customer) {
            return response()->json(['error' => 'Cliente não encontrado'], 404);
        }
        return response()->json($customer, 200);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email|unique:customers',
            'document' => 'nullable|string'
        ]);

        $customer = Customer::create($validated);
        return response()->json($customer, 201);
    }
}"""
    ),
    PresetExample(
        id="go-gin",
        name="Go (Gin Framework)",
        language="Go / Gin",
        target_recommendation="FastAPI",
        description="Handlers do Gin com ShouldBindJSON, c.Param, c.JSON com status http.",
        code="""package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

type InvoiceRequest struct {
    ClientName  string  `json:"client_name" binding:"required"`
    Amount      float64 `json:"amount" binding:"required,gt=0"`
    Description string  `json:"description"`
}

func GetInvoice(c *gin.Context) {
    id := c.Param("id")
    invoice, err := invoiceRepo.FindByID(id)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Fatura não encontrada"})
        return
    }
    c.JSON(http.StatusOK, invoice)
}

func CreateInvoice(c *gin.Context) {
    var req InvoiceRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    created, err := invoiceRepo.Save(req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Erro ao salvar"})
        return
    }
    c.JSON(http.StatusCreated, created)
}"""
    )
]


@router.get("/presets", response_model=list[PresetExample])
async def get_presets():
    """Retorna exemplos pré-definidos em várias linguagens para teste imediato."""
    return PRESETS


@router.post("/convert", response_model=TranspilationResponse)
async def convert_code(
    payload: TranspileRequest,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key")
):
    """
    Transpila o endpoint fornecido para Python (FastAPI/Flask) usando Gemini API
    em temperatura 0 e validação automática por AST.
    """
    api_key = payload.api_key or x_gemini_api_key
    result = await transpile_api_code(
        code=payload.code,
        source_language=payload.source_language,
        target_framework=payload.target_framework,
        conversion_mode=payload.conversion_mode,
        api_key_override=api_key
    )
    return result


@router.post("/validate", response_model=ASTValidationResult)
async def validate_code(payload: ValidateRequest):
    """Executa a validação de sintaxe Python utilizando o módulo AST nativo."""
    return validate_python_code(payload.code)

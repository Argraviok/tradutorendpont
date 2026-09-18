import { Component, OnInit, signal, computed, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, PresetExample, TranspilationResponse, ASTValidationResult } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  private apiService = inject(ApiService);

  // State Signals
  sourceCode = signal<string>('');
  targetCode = signal<string>('');
  sourceLanguage = signal<string>('Auto-detect');
  targetFramework = signal<string>('FastAPI');
  conversionMode = signal<'strict' | 'idiomatic'>('strict');
  
  isLoading = signal<boolean>(false);
  backendOnline = signal<boolean>(false);
  hasServerKey = signal<boolean>(false);
  userApiKey = signal<string>('');
  
  presets = signal<PresetExample[]>([]);
  activePresetId = signal<string | null>(null);
  lastResponse = signal<TranspilationResponse | null>(null);
  validationResult = signal<ASTValidationResult | null>(null);
  
  activeTab = signal<'endpoints' | 'models' | 'deps' | 'fidelity'>('endpoints');
  showApiKeyModal = signal<boolean>(false);
  apiKeyInput = signal<string>('');
  copyFeedback = signal<boolean>(false);
  
  toastMessage = signal<string | null>(null);
  toastType = signal<'success' | 'error' | 'info'>('info');

  // Computed line counts
  sourceLines = computed(() => {
    const code = this.sourceCode();
    if (!code) return [1];
    const count = code.split('\n').length;
    return Array.from({ length: count }, (_, i) => i + 1);
  });

  targetLines = computed(() => {
    const code = this.targetCode();
    if (!code) return [1];
    const count = code.split('\n').length;
    return Array.from({ length: count }, (_, i) => i + 1);
  });

  hasApiKey = computed(() => {
    return this.hasServerKey() || !!this.userApiKey();
  });

  ngOnInit(): void {
    this.userApiKey.set(this.apiService.getStoredApiKey());
    this.apiKeyInput.set(this.userApiKey());
    this.checkHealth();
    this.loadPresets();
  }

  checkHealth(): void {
    this.apiService.checkHealth().subscribe({
      next: (res) => {
        this.backendOnline.set(true);
        this.hasServerKey.set(res.has_gemini_key);
      },
      error: () => {
        this.backendOnline.set(false);
      }
    });
  }

  loadPresets(): void {
    this.apiService.getPresets().subscribe({
      next: (data) => {
        this.presets.set(data);
        // Load first preset by default as an interactive preview
        if (data.length > 0 && !this.sourceCode()) {
          this.applyPreset(data[0]);
        }
      },
      error: () => {
        // Fallback local preset if backend is still starting
        this.loadDefaultFallbackPreset();
      }
    });
  }

  loadDefaultFallbackPreset(): void {
    const fallbackCode = `[ApiController]
[Route("api/[controller]")]
public class ProductsController : ControllerBase
{
    private readonly IProductRepository _repo;

    public ProductsController(IProductRepository repo)
    {
        _repo = repo;
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<ProductDto>> GetProduct(int id)
    {
        var product = await _repo.GetByIdAsync(id);
        if (product == null) return NotFound();
        return Ok(product);
    }

    [HttpPost]
    public async Task<ActionResult<ProductDto>> CreateProduct([FromBody] CreateProductRequest req)
    {
        var created = await _repo.AddAsync(req);
        return CreatedAtAction(nameof(GetProduct), new { id = created.Id }, created);
    }
}`;
    this.sourceCode.set(fallbackCode);
    this.sourceLanguage.set('C# / .NET');
  }

  applyPreset(preset: PresetExample): void {
    this.activePresetId.set(preset.id);
    this.sourceCode.set(preset.code);
    this.sourceLanguage.set(preset.language);
    this.targetFramework.set(preset.target_recommendation || 'FastAPI');
    this.showToast(`Exemplo "${preset.name}" carregado.`, 'info');
  }

  transpile(): void {
    const code = this.sourceCode().trim();
    if (!code) {
      this.showToast('Por favor, insira ou cole o código do endpoint para converter.', 'error');
      return;
    }

    if (!this.hasApiKey()) {
      this.showApiKeyModal.set(true);
      this.showToast('Configure sua chave da API do Gemini para iniciar a conversão.', 'info');
      return;
    }

    this.isLoading.set(true);
    this.apiService.convert(
      code,
      this.sourceLanguage(),
      this.targetFramework(),
      this.conversionMode(),
      this.userApiKey()
    ).subscribe({
      next: (response) => {
        this.isLoading.set(false);
        this.lastResponse.set(response);
        if (response.success) {
          this.targetCode.set(response.python_code);
          this.validationResult.set(response.validation);
          this.showToast('Código transpilado com sucesso! Sintaxe Python validada.', 'success');
        } else {
          this.showToast(response.error_message || 'Erro durante a conversão.', 'error');
          if (response.error_message?.includes('Chave da API')) {
            this.showApiKeyModal.set(true);
          }
        }
      },
      error: (err) => {
        this.isLoading.set(false);
        const msg = err.error?.detail || err.message || 'Falha ao conectar com o backend.';
        this.showToast(`Erro na requisição: ${msg}`, 'error');
      }
    });
  }

  copyTargetCode(): void {
    const code = this.targetCode();
    if (!code) return;

    navigator.clipboard.writeText(code).then(() => {
      this.copyFeedback.set(true);
      this.showToast('Código Python copiado para a área de transferência!', 'success');
      setTimeout(() => this.copyFeedback.set(false), 2000);
    });
  }

  copyPipDependencies(): void {
    const deps = this.lastResponse()?.pip_dependencies || ['fastapi', 'uvicorn', 'pydantic'];
    const cmd = `pip install ${deps.join(' ')}`;
    navigator.clipboard.writeText(cmd).then(() => {
      this.showToast(`Comando copiado: "${cmd}"`, 'success');
    });
  }

  downloadTargetFile(): void {
    const code = this.targetCode();
    if (!code) return;

    const blob = new Blob([code], { type: 'text/x-python;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `endpoints_${this.targetFramework().toLowerCase()}.py`;
    link.click();
    URL.revokeObjectURL(url);
    this.showToast(`Arquivo "${link.download}" baixado!`, 'success');
  }

  clearSource(): void {
    this.sourceCode.set('');
    this.targetCode.set('');
    this.lastResponse.set(null);
    this.validationResult.set(null);
    this.activePresetId.set(null);
    this.showToast('Editor limpo.', 'info');
  }

  async pasteFromClipboard(): Promise<void> {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        this.sourceCode.set(text);
        this.showToast('Código colado com sucesso!', 'info');
      }
    } catch {
      this.showToast('Permissão de clipboard não autorizada. Use Ctrl+V.', 'info');
    }
  }

  saveApiKeyFromModal(): void {
    const key = this.apiKeyInput().trim();
    this.apiService.saveApiKey(key);
    this.userApiKey.set(key);
    this.showApiKeyModal.set(false);
    this.showToast(key ? 'Chave de API salva com sucesso!' : 'Chave removida.', 'success');
  }

  openApiKeyModal(): void {
    this.apiKeyInput.set(this.userApiKey());
    this.showApiKeyModal.set(true);
  }

  closeApiKeyModal(): void {
    this.showApiKeyModal.set(false);
  }

  showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    this.toastMessage.set(message);
    this.toastType.set(type);
    setTimeout(() => {
      if (this.toastMessage() === message) {
        this.toastMessage.set(null);
      }
    }, 3500);
  }

  // Keyboard shortcut: Ctrl + Enter to Transpile
  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      if (!this.isLoading()) {
        this.transpile();
      }
    }
  }
}

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface EndpointMapping {
  original_route: string;
  target_route: string;
  http_method: string;
  original_handler: string;
  target_function: string;
}

export interface ModelMapping {
  original_type: string;
  target_pydantic_model: string;
  fields_summary: string;
}

export interface ASTValidationResult {
  is_valid: boolean;
  syntax_error?: string | null;
  error_line?: number | null;
  error_column?: number | null;
  total_lines: number;
  detected_routes: string[];
  detected_models: string[];
  detected_imports: string[];
}

export interface TranspilationResponse {
  success: boolean;
  source_language: string;
  target_framework: string;
  python_code: string;
  pip_dependencies: string[];
  endpoints_mapping: EndpointMapping[];
  models_mapping: ModelMapping[];
  fidelity_notes: string[];
  validation: ASTValidationResult;
  error_message?: string | null;
}

export interface PresetExample {
  id: string;
  name: string;
  language: string;
  target_recommendation: string;
  description: string;
  code: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  has_gemini_key: boolean;
  default_model: string;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = 'http://localhost:8000/api';
  private readonly API_KEY_STORAGE = 'transpile_gemini_api_key';

  getStoredApiKey(): string {
    return localStorage.getItem(this.API_KEY_STORAGE) || '';
  }

  saveApiKey(key: string): void {
    if (key.trim()) {
      localStorage.setItem(this.API_KEY_STORAGE, key.trim());
    } else {
      localStorage.removeItem(this.API_KEY_STORAGE);
    }
  }

  checkHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`);
  }

  getPresets(): Observable<PresetExample[]> {
    return this.http.get<PresetExample[]>(`${this.baseUrl}/presets`);
  }

  convert(
    code: string,
    sourceLanguage: string,
    targetFramework: string,
    conversionMode: string,
    apiKeyOverride?: string
  ): Observable<TranspilationResponse> {
    const key = apiKeyOverride || this.getStoredApiKey();
    return this.http.post<TranspilationResponse>(`${this.baseUrl}/convert`, {
      code,
      source_language: sourceLanguage,
      target_framework: targetFramework,
      conversion_mode: conversionMode,
      api_key: key || undefined
    });
  }

  validate(code: string): Observable<ASTValidationResult> {
    return this.http.post<ASTValidationResult>(`${this.baseUrl}/validate`, { code });
  }
}

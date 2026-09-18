# Transpile.io — Conversor Universal de Endpoints de APIs ⚡

Sistema completo para transpilação determinística **1:1** de endpoints de APIs para **Python (FastAPI / Flask)**, com prevenção rigorosa de alucinações (Temperatura 0.0) e validação sintática nativa via AST.

---

## 🎯 Funcionalidades

- **Editor Split-View**: Entrada do endpoint em qualquer linguagem de origem e visualização do código Python gerado lado a lado com sincronização de linhas.
- **Zero Alucinação (Grounding)**: Motor estrito baseado na API do Google Gemini (`temperature: 0.0`) com regras para preservar 100% das rotas, métodos HTTP, query/path parameters, headers, status codes e regras de negócio.
- **Validação Sintática AST (Python `ast.parse`)**: Cada código gerado é analisado e compilado pelo backend antes de ser entregue.
- **Mapeamento de Tipos para Pydantic**: DTOs, structs e interfaces da linguagem de origem são convertidos para modelos `Pydantic BaseModel`.
- **Exemplos Prontos (Presets)**:
  - C# (ASP.NET Core Controller)
  - Node.js (Express / TypeScript)
  - Java (Spring Boot RestController)
  - PHP (Laravel Controller)
  - Go (Gin Framework)
- **Painel de Auditoria 1:1**: Tabela de rotas mapeadas, classes convertidas, dependências `pip` e relatório de fidelidade.
- **Exportação Rápida**: Copiar código com 1 clique ou baixar o arquivo `.py` pronto.

---

## 📂 Estrutura do Projeto

```
sistema de convercao/
├── backend/                  # API Python FastAPI
│   ├── app/
│   │   ├── routers/          # Endpoints (/api/convert, /api/validate, /api/presets)
│   │   ├── services/         # Motor de transpilação e validador AST
│   │   ├── config.py         # Configurações e variáveis de ambiente
│   │   └── main.py           # Inicialização da aplicação FastAPI
│   ├── requirements.txt      # Dependências Python
│   └── .env.example          # Exemplo de variáveis de ambiente
│
└── frontend/                 # Interface Moderna em Angular (Dark Mode Glassmorphic)
    ├── src/
    │   ├── app/              # Componente principal, toolbar, editores e modal
    │   │   ├── services/     # Serviço HTTP de integração com o Backend
    │   │   ├── app.ts        # Lógica de estado e atalhos (Ctrl+Enter)
    │   │   ├── app.html      # Layout split-view e painel de auditoria
    │   │   └── app.css       # Design system dark mode com glassmorphism
    │   ├── styles.css        # Variáveis globais e tipografia
    │   └── index.html        # Fontes (Plus Jakarta Sans & JetBrains Mono)
    └── package.json
```

---

## 🚀 Como Executar Localmente

### 1. Backend (FastAPI)
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate      # No Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
> O backend estará acessível em `http://127.0.0.1:8000` (documentação Swagger em `http://127.0.0.1:8000/docs`).

### 2. Frontend (Angular)
```bash
cd frontend
npm install
npm start
```
> O frontend estará acessível em `http://localhost:4200`.

---

## 🔑 Configuração da Chave Gemini
Você pode configurar sua chave da API do Gemini de duas formas:
1. No arquivo `backend/.env`:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   ```
2. Diretamente na interface visual clicando no botão **"Configurar Chave Gemini"** no cabeçalho.

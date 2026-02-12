# CIAI - Análise de Avaliações Externas (MEC/INEP) - UFPR

Este repositório é dedicado à análise de dados da **CIAI (Coordenadoria de Indicadores e Avaliação Institucional)** da **UFPR (Universidade Federal do Paraná)**.

Projeto de análise automatizada de relatórios de avaliação de cursos do MEC, utilizando Inteligência Artificial (Gemini) e técnicas de NLP (Bardin) para identificar gargalos, extrair justificativas de notas baixas e sugerir melhorias.

## 📂 Estrutura de Pastas

### `src/` (Código Fonte Principal)

Scripts principais e ferramentas de processamento de dados.

- **`legacy/`**: Scripts consolidados de pré-processamento (Renomeação, Extração, OCR e NLTK).
  - **`extração.py`**: **FERRAMENTA UNIFICADA (NOVO)**. Consolida todas as etapas em um único fluxo:
      1.  **Renomeação**: Padroniza nomes de arquivos (Ano - Curso - Cidade).
      2.  **Extração**: Extrai metadados, notas e justificativas de PDFs (com OCR automático).
      3.  **Análise**: Categoriza justificativas usando metodologia Bardin (Inovação, Gestão, Infraestrutura).
      - *Uso Interativo*: `python src/legacy/extração.py` (Menu)
      - *Uso Automatizado*: `python src/legacy/extração.py --pipeline`
  - *Outros scripts*: Mantidos como histórico (`ferramentas_legado.py`, `analise_conteudo_nlp.py`, etc.).

- **`processar_avaliacoes.py`**: **ANÁLISE COM IA (GEMINI)**. Script principal que consome os dados extraídos (`.json`/`.csv`) e gera relatórios estratégicos usando LLMs para análise profunda de sentimento e categorização semântica.
- **`humanizar_texto.py`**: Utilitário para reescrever textos técnicos em linguagem natural.

### `data/` (Dados)

Arquivos de entrada e saída.

- **`inputs/`**:
  - `rename_mapping.csv`: Mapeamento gerado para renomeação de arquivos.
  - Relatórios em PDF (na raiz ou subpastas configuradas).
- **`outputs/`**:
  - `relatorio_consolidado_extraido.json`: Dados estruturados (Notas, Metadados).
  - `relatorio_justificativas.json`: Justificativas extraídas por indicador.
  - `bardin_analysis_report.txt`: Relatório de análise categórica (Bardin).
  - `low_grades_justifications.txt`: Relatório focado em notas < 5.

### `reports/` (Relatórios Finais)

- **`relatorio_executivo.txt`**: Documento estratégico consolidado.
- **`log_analise_ia.txt`**: Logs técnicos da análise da IA.

## 🚀 Como Usar

### 1. Pré-Processamento (Renomeação e Extração)

Antes da análise com IA, execute a ferramenta unificada para preparar os dados:

```bash
# Modo Interativo (Menu)
python src/legacy/extração.py

# Modo Automático (Pipeline Completo)
python src/legacy/extração.py --pipeline
```

Isso irá:
1.  Renomear PDFs para o padrão `Ano - Curso - Cidade.pdf`.
2.  Extrair textos (usando OCR se necessário).
3.  Gerar JSONs de dados estruturados.
4.  Criar relatórios preliminares de análise de conteúdo (Bardin).

### 2. Análise Estratégica (IA)

Com os dados extraídos, execute a análise profunda com Gemini:

```bash
python src/processar_avaliacoes.py
```

### 3. Humanização (Opcional)

Para refinar textos gerados:

```bash
python src/humanizar_texto.py
```

## 📋 Pré-requisitos

- Python 3.8+
- Bibliotecas Python:
  ```bash
  pip install pandas pypdf tqdm google-generativeai nltk
  ```
- **Opcional (para OCR)**: `PyMuPDF`, `pytesseract`, `Pillow`.
  - Requer [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) instalado no sistema.
- **Chave de API**: Variável de ambiente `GOOGLE_API_KEY` configurada para uso do Gemini.

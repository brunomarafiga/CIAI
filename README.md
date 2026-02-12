# CIAI - Análise de Avaliações Externas (MEC/INEP)

Projeto de análise automatizada de relatórios de avaliação do MEC, utilizando Inteligência Artificial (Gemini) para identificar gargalos e sugerir melhorias.

## 📂 Estrutura de Pastas

### `src/` (Código Fonte)

Scripts principais do projeto.

- **`processar_avaliacoes.py`**: Script principal. Lê os dados, processa com Gemini e gera relatórios.
- **`humanizar_texto.py`**: Ferramenta para reescrever textos técnicos com linguagem natural e fluida.
- **`legacy/`**: Scripts antigos arquivados, mantidos para referência:
  - **`ferramentas_legado.py`**: **SCRIPT UNIFICADO**. Menu interativo para executar qualquer uma das ferramentas legadas abaixo.
  - **`analise_conteudo_nlp.py`**: Análise de conteúdo das justificativas usando técnicas de NLP (Bardin, RSLP Stemmer).
  - **`aplicar_renomeacao_arquivos.py`**: Aplica renomeação em massa de arquivos baseada em um CSV de mapeamento.
  - **`extracao_dados_pdf_ocr.py`**: Extração consolidada de dados de relatórios PDF, incluindo suporte a OCR.
  - **`extracao_justificativas_pdf.py`**: Extração focada apenas nas justificativas de conceitos nos PDFs.
  - **`gerar_mapa_renomeacao.py`**: Gera o mapeamento CSV para padronização de nomes de arquivos (Ano - Curso - Cidade).

### `data/` (Dados)

Arquivos de entrada e saída de dados brutos.

- **`inputs/`**:
  - `Relatórios.CSV`: Base original (se aplicável).
  - `justificativas_notas_baixas.txt`: Texto extraído das justificativas com nota < 5.
- **`outputs/`**:
  - `tabela_dados_processados.csv`: Dados estruturados gerados pela IA (Categorias, Tags, Pontos Negativos).

### `reports/` (Relatórios)

Documentos finais para consumo humano.

- **`relatorio_executivo.txt`**: **RELATÓRIO FINAL CONSOLIDADO**. Documento estratégico estilizado.
- **`log_analise_ia.txt`**: Logs detalhados da análise da IA.

## 🚀 Como Usar

1. **Análise de Dados:**
   Execute o script principal para processar novos dados:

   ```bash
   python src/processar_avaliacoes.py
   ```

2. **Humanização de Texto:**
   Para melhorar a redacção de um texto:

   ```bash
   python src/humanizar_texto.py
   ```

## 📋 Pré-requisitos

- Python 3.x
- Bibliotecas: `google-generativeai`, `pandas`, `tqdm`.
- Chave de API do Google Gemini configurada.

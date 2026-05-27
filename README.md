# CIAI – Scripts de Extração de Relatórios MEC

Pipeline de extração automática de dados dos **Relatórios de Avaliação In Loco** emitidos pelo e-MEC, desenvolvido pela Coordenadoria de Indicadores e Avaliação Institucional (CIAI) da UFPR.

---

## Visão Geral

O pipeline lê PDFs de avaliação in loco e extrai de forma automatizada:

- Metadados do curso (nome, código e-MEC, ano, modalidade, campus, cidade)
- Notas de cada indicador (1.1 a 3.17)
- Justificativas textuais por indicador
- Conceito Final Contínuo e Conceito Final Faixa

A saída é um arquivo `relatorio.json` com um registro por indicador por PDF.

---

## Estrutura dos Scripts

| Arquivo | Descrição |
|---|---|
| `config.py` | Configurações compartilhadas: paths, padrões regex de campus/modalidade/ano |
| `extração.py` | **Script principal** – extrai todos os PDFs e gera `relatorio.json` |
| `1_gerar_mapa_renomeacao.py` | Gera mapeamento de renomeação de arquivos PDF |
| `2_aplicar_renomeacao.py` | Aplica a renomeação padronizada nos PDFs |
| `4_analise_bardin.py` | Análise de categorias Bardin sobre as justificativas extraídas |
| `test_relatorio.py` | Testes de qualidade e cobertura sobre o `relatorio.json` gerado |

---

## Dependências

```bash
pip install pymupdf pandas tqdm pillow paddlepaddle==2.6.2 paddleocr==2.9.1
```

> **Nota:** O PaddleOCR é utilizado como fallback para PDFs cujas caixas de conceito final estão renderizadas como imagem (problema comum em relatórios e-MEC mais antigos).

---

## Como Usar

1. Coloque os PDFs dos relatórios na mesma pasta dos scripts.
2. Execute:

```bash
python extração.py
```

3. O arquivo `relatorio.json` será gerado na mesma pasta.
4. Para validar a qualidade da extração:

```bash
python test_relatorio.py
```

---

## Cobertura Típica (63 PDFs — 2022–2025)

| Campo | Cobertura |
|---|---|
| Id_MEC | 100% |
| Curso | 100% |
| Ano_avaliacao | 100% |
| Modalidade | 100% |
| Cidade | 100% |
| CONCEITO_FINAL_CONTINUO | ~98% |
| CONCEITO_FINAL_FAIXA | ~95% |

---

## Observações Técnicas

- O script usa **processamento sequencial** para evitar explosão de memória com o modelo PaddleOCR (~500 MB por instância).
- O PyMuPDF (`fitz`) é usado para extração nativa de texto; o OCR só é acionado como fallback.
- Os PDFs **não são versionados** (`.gitignore`) pois são dados sigilosos do MEC.

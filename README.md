<div align="center">

# 🏛️ CIAI — Pipeline de Extração & Análise de Conteúdo e-MEC
### Coordenadoria de Indicadores e Avaliação Institucional • UFPR

**Mineração Automatizada de Relatórios In Loco do MEC e Análise Textual Baseada na Metodologia Bardin**

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://python.org)
[![UFPR](https://img.shields.io/badge/Unidade-CIAI%20%2F%20PROPLAN%20UFPR-004587)](https://www.ufpr.br)
[![Metodologia](https://img.shields.io/badge/NLP%20%26%20An%C3%A1lise-Metodologia%20Bardin-purple)](#-análise-de-conteúdo-segundo-bardin)
[![Status](https://img.shields.io/badge/Status-Em%20Produ%C3%A7%C3%A3o-success)](#)

</div>

---

## 📌 Visão Geral

Desenvolvido para a **Coordenadoria de Indicadores e Avaliação Institucional (CIAI)** da Universidade Federal do Paraná (UFPR), este repositório contém a suíte completa de scripts para extração, higienização, mapeamento e análise de dados contidos nos **Relatórios de Avaliação In Loco** emitidos pelo Ministério da Educação (**e-MEC**).

O ecossistema transforma dezenas de relatórios em formato PDF não estruturado em bases analíticas estruturadas (`.json` e `.csv`), viabilizando a identificação de pontos de fragilidade e excelência nos cursos de graduação da universidade.

---

## 🔄 Fluxo de Processamento de Dados

```mermaid
flowchart LR
    PDF[Relatórios e-MEC em PDF] --> Parse[extração.py: Parser e Regex]
    Parse --> Norm[1 & 2: Renomeação e Padronização]
    Norm --> Export[3: Geração de Planilhas e Indicadores]
    Export --> Bardin[4: Análise de Conteúdo de Bardin]
    Bardin --> BI[Painéis e Tomada de Decisão CIAI]
```

---

## 🔬 Análise de Conteúdo segundo Bardin

O script [`4_analise_bardin.py`](4_analise_bardin.py) aplica a clássica metodologia de **Análise de Conteúdo de Laurence Bardin** sobre as justificativas textuais redigidas pelos avaliadores do MEC:
- **Pré-análise e Leitura Flutuante:** Segmentação dos blocos textuais associados a cada indicador (Eixos 1, 2 e 3).
- **Exploração do Material (Codificação):** Mapeamento léxico e categorial a partir do vocabulário controlado definido em [`config.py`](config.py).
- **Tratamento dos Resultados e Inferência:** Agrupamento por categorias semânticas (Infraestrutura, Corpo Docente, Projeto Pedagógico, Acessibilidade, Gestão Acadêmica).

---

## 📂 Arquitetura dos Scripts

| Script | Função Principal |
|---|---|
| `config.py` | Centralizador de caminhos, dicionários de regex para campus/modalidade e categorias de Bardin. |
| `extração.py` | Motor de parsing via regex e OCR para extrair metadados, notas contínuas/faixa e pareceres. |
| `1_gerar_mapa_renomeacao.py` | Varre os PDFs originais e gera tabela de equivalência para padronização de arquivos. |
| `2_aplicar_renomeacao.py` | Executa a renomeação segura dos PDFs em lote conforme o código e-MEC e ano. |
| `3_gerar_planilhas_indicadores.py` | Consolida os registros em tabelas relacionais com pivotamento de notas. |
| `4_analise_bardin.py` | Executa a classificação temática e gera a matriz de coocorrência de termos. |

---

## 🚀 Como Executar

```bash
git clone https://github.com/brunomarafiga/CIAI.git
cd CIAI
pip install pdfplumber pandas openpyxl
```

Para extrair e analisar:
```bash
python extração.py
python 4_analise_bardin.py
```

---

<div align="center">
Desenvolvido por <strong>Bruno Marafiga</strong><br>
Coordenadoria de Indicadores e Avaliação Institucional (CIAI) • UFPR
</div>

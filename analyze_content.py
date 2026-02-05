import pandas as pd
import re
from collections import Counter
import sys

# Define stopwords for Portuguese content analysis
STOPWORDS = {
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma', 'os', 'no', 'se',
    'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'ao', 'ele', 'das', 'à', 'seu', 'sua', 'ou',
    'quando', 'muito', 'nos', 'já', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela',
    'entre', 'depois', 'sem', 'mesmo', 'aos', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'você',
    'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'numa', 'pelos', 'elas', 'qual', 'nós',
    'lhe', 'te', 'pelas', 'este', 'dele', 'tu', 'esta', 'têm', 'foi', 'pelo', 'pela', 'pelas', 
    'pelo', 'ser', 'são', 'está', 'curso', 'ufpr', 'ppc', 'institucional', 'ensino', 'aprendizagem',
    'docente', 'discente', 'alunos', 'estudantes', 'coordenação', 'colegiado', 'nde', 'cpa',
    'universidade', 'federal', 'paraná', 'entretanto', 'embora', 'contudo', 'sendo', 'apenas',
    'assim', 'apesar', 'onde', 'quais', 'além', 'sobre', 'pois', 'cada', 'têm', 'tem'
}

# --- NLP Setup ---
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import RSLPStemmer
    stemmer = RSLPStemmer()
    STOPWORDS = set(stopwords.words('portuguese'))
    # Add custom stopwords relevant to the context
    STOPWORDS.update({
        'curso', 'ufpr', 'ppc', 'institucional', 'ensino', 'aprendizagem',
        'docente', 'discente', 'alunos', 'estudantes', 'coordenação', 
        'colegiado', 'nde', 'cpa', 'universidade', 'federal', 'paraná', 'entretanto', 
        'embora', 'contudo', 'sendo', 'apenas', 'assim', 'apesar', 'onde', 'quais', 'além',
        'ser', 'são', 'está', 'foi', 'pelo', 'pela', 'sobre', 'pois', 'cada', 'têm', 'tem'
    })
except ImportError:
    print("NLTK not found or data missing.")
    stemmer = None

# --- Helper Functions ---

def parse_grade(val):
    if pd.isna(val): return None
    val_str = str(val).strip().upper()
    if 'NSA' in val_str or 'NAN' in val_str or val_str == '': return None
    clean_val = re.sub(r'[^\d,.]', '', val_str)
    try:
        return float(clean_val.replace(',', '.'))
    except:
        return None

def indicator_key(s):
    try:
        parts = s.split('.')
        return (int(parts[0]), int(parts[1]))
    except:
        return (99, 99)

def get_top_keywords(text_series, n=15):
    all_lemmas = []
    for text in text_series:
        if not isinstance(text, str): continue
        
        # Simple tokenization by regex to avoid punkt issues if not perfect
        words = re.findall(r'\b[a-zA-ZçãéáíóúâêôãõüÇÃÉÁÍÓÚÂÊÔÃÕÜ]+\b', text.lower())
        
        for word in words:
            if len(word) < 3: continue
            if word in STOPWORDS: continue
            
            # Use stemmer if available to group similar words (e.g. laboratório/laboratórios)
            if stemmer:
                # Basic plural check or stemming
                if word.endswith('s') and word[:-1] in words: 
                    lemma = word[:-1]
                else:
                    lemma = stemmer.stem(word)
                    
                if lemma in STOPWORDS: continue
                all_lemmas.append(lemma)
            else:
                all_lemmas.append(word)

    # Count words first 
    word_counts = Counter()
    for text in text_series:
            if not isinstance(text, str): continue
            words = re.findall(r'\b[a-zA-ZçãéáíóúâêôãõüÇÃÉÁÍÓÚÂÊÔÃÕÜ]+\b', text.lower())
            filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]
            word_counts.update(filtered)
            
    if not stemmer:
        return word_counts.most_common(n)

    # Merge by stem
    stem_groups = {} # stem -> {main_word: count, variations: {word: count}}
    
    for word, count in word_counts.items():
        stem = stemmer.stem(word)
        if stem not in stem_groups:
            stem_groups[stem] = {'total': 0, 'words': Counter()}
        stem_groups[stem]['total'] += count
        stem_groups[stem]['words'][word] = count
        
    # Format output: "main_word (total)"
    final_list = []
    for stem, data in stem_groups.items():
        # Pick the most frequent word as the representative
        if data['words']:
            rep_word = data['words'].most_common(1)[0][0]
            final_list.append((rep_word, data['total']))
        
    return sorted(final_list, key=lambda x: x[1], reverse=True)[:n]


# --- Main Analysis Logic ---

def analyze_content():
    print("Loading data...")
    try:
        # Load Grades
        df_grades = pd.read_csv('Relatórios.CSV', sep=';', encoding='latin1') 
    except UnicodeDecodeError:
        df_grades = pd.read_csv('Relatórios.CSV', sep=';', encoding='utf-8')
    except Exception as e:
        print(f"Error loading Relatórios.CSV: {e}")
        return

    try:
        # Load Justifications
        df_justifs = pd.read_csv('relatorio_justificativas.csv', sep=';', encoding='utf-8-sig')
    except Exception as e:
        print(f"Error loading relatorio_justificativas.csv: {e}")
        return

    # 1. Clean Id_MEC and Ensure String Match
    print("Cleaning data...")
    df_grades['Id_MEC'] = df_grades['Id_MEC'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_justifs['Id_MEC'] = df_justifs['Id_MEC'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 2. Reshape (Melt) to Long Format
    # Identify Indicator Columns in Grades
    grade_cols = [c for c in df_grades.columns if re.match(r'^\d+\.\d+$', c)]
    
    # Ensure metadata columns exist
    meta_cols = ['Id_MEC', 'Curso', 'Modalidade', 'Campus']
    for c in meta_cols:
        if c not in df_grades.columns:
            df_grades[c] = 'Desconhecido'

    df_grades_melted = df_grades.melt(
        id_vars=meta_cols, 
        value_vars=grade_cols, 
        var_name='Indicator', 
        value_name='Grade'
    )
    
    # Identify Indicator Columns in Justifications
    justif_cols = [c for c in df_justifs.columns if re.match(r'^\d+\.\d+$', c)]
    
    df_justifs_melted = df_justifs.melt(
        id_vars=['Id_MEC'], 
        value_vars=justif_cols, 
        var_name='Indicator', 
        value_name='Justification'
    )
    
    # 3. Merge
    print("Merging datasets...")
    merged = pd.merge(df_grades_melted, df_justifs_melted, on=['Id_MEC', 'Indicator'], how='inner')
    
    # 4. Filter for Low Grades (< 5)
    merged['Grade_Float'] = merged['Grade'].apply(parse_grade)
    
    low_grades = merged[merged['Grade_Float'] < 5].copy()
    
    print(f"Found {len(low_grades)} instances of grades < 5.")
    
    if len(low_grades) == 0:
        print("No low grades found. Check parsing logic or data.")
        return

    # 5. Group and Analyze
    output_lines = []
    output_lines.append(f"ANÁLISE DE INDICADORES COM NOTA < 5\n")
    output_lines.append(f"Total de ocorrências encontradas: {len(low_grades)}\n")
    output_lines.append("Obs: Agrupamento realizado por Campus (como aproximação de Setor)\n")
    output_lines.append("="*80 + "\n")

    grouped = low_grades.groupby('Indicator')
    sorted_indicators = sorted(grouped.groups.keys(), key=indicator_key)

    for indicator in sorted_indicators:
        group_df = grouped.get_group(indicator)
        count = len(group_df)
        
        output_lines.append(f"\nINDICADOR: {indicator}")
        output_lines.append(f"Quantidade de notas < 5: {count}")
        
        avg_low_grade = group_df['Grade_Float'].mean()
        output_lines.append(f"Média destas notas: {avg_low_grade:.2f}")
        
        keywords = get_top_keywords(group_df['Justification'])
        output_lines.append(f"Termos Frequentes: {', '.join([f'{w}({c})' for w, c in keywords])}")
        
        # Group by Campus within Indicator
        campus_grouped = group_df.groupby('Campus')
        sorted_campuses = sorted(campus_grouped.groups.keys(), key=lambda x: str(x))

        for campus in sorted_campuses:
            campus_df = campus_grouped.get_group(campus)
            output_lines.append(f"\n  LOCALIZAÇÃO/SETOR: {campus} (Qtd: {len(campus_df)})")
            output_lines.append("  " + "-" * 30)

            for idx, row in campus_df.iterrows():
                # Format: [Grade] Course Name (Modality) - ID
                course_name = str(row['Curso']).strip()
                modality = str(row['Modalidade']).strip()
                grade = str(row['Grade']).strip()
                mec_id = str(row['Id_MEC']).strip()
                
                output_lines.append(f"    [Nota: {grade}] {course_name} ({modality}) - ID: {mec_id}")
                
                justification = str(row['Justification']).strip()
                
                # --- Text Cleaning ---
                justification = re.sub(r'\b0\b', 'O', justification) 
                justification = re.sub(r'^0\s', 'O ', justification)
                justification = re.sub(r'([a-zçãéáíóú])([.,;:])([A-Z])', r'\1\2 \3', justification)
                justification = re.sub(r'([a-zçãéáíóú])([A-Z])', r'\1 \2', justification)

                # Remove e-MEC URLs and footers
                justification = re.sub(r'https?://emec\.mec\.gov\.br.*?e-MEC - IES', '', justification, flags=re.DOTALL | re.IGNORECASE)
                justification = re.sub(r'https?://emec\.mec\.gov\.br\S*', '', justification, flags=re.IGNORECASE)

                # --- Negative Sentiment Extraction ---
                adversative_conjunctions = [
                    "no entanto", "contudo", "entretanto", "porém", "todavia", "mas", "apesar de"
                ]
                
                lower_justif = justification.lower()
                split_index = -1
                
                for term in adversative_conjunctions:
                    pattern = r'\b' + term + r'\b'
                    match = re.search(pattern, lower_justif)
                    if match:
                        start_pos = match.start()
                        if split_index == -1 or start_pos < split_index:
                            split_index = start_pos
                
                if split_index != -1:
                    filtered_text = justification[split_index:].strip()
                    if filtered_text:
                        filtered_text = filtered_text[0].upper() + filtered_text[1:]
                    justification = filtered_text
                
                for line in justification.split('\n'):
                     output_lines.append(f"      {line.strip()}")
                output_lines.append("") 
            
        output_lines.append("=" * 80 + "\n")

    # Save Report
    with open('low_grades_justifications.txt', 'w', encoding='utf-8') as f:
        f.writelines([l + '\n' for l in output_lines])
    
    print("Analysis complete. Saved to 'low_grades_justifications.txt'.")

if __name__ == "__main__":
    analyze_content()

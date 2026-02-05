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
    'assim', 'apesar', 'onde', 'quais', 'além'
}

def analyze_content():
    print("Loading data...")
    try:
        # Load Grades
        # Using separator ';' as seen in file inspection (though file extension is CSV, content seemed semicolon sep in `relatorio_justificativas.csv`, let's check `Relatórios.CSV`)
        # Inspecting previous tool output: Relatórios.CSV used semi-colons: "Curso;Id_MEC;..."
        df_grades = pd.read_csv('Relatórios.CSV', sep=';', encoding='latin1') # 'latin1' guessed from 'GESTO' chars in inspection
    except UnicodeDecodeError:
        df_grades = pd.read_csv('Relatórios.CSV', sep=';', encoding='utf-8')
    except Exception as e:
        print(f"Error loading Relatórios.CSV: {e}")
        return

    try:
        # Load Justifications
        # Using separator ';' as seen in file inspection
        df_justifs = pd.read_csv('relatorio_justificativas.csv', sep=';', encoding='utf-8-sig')
    except Exception as e:
        print(f"Error loading relatorio_justificativas.csv: {e}")
        return

    # 1. Clean Id_MEC and Ensure String Match
    print("Cleaning data...")
    df_grades['Id_MEC'] = df_grades['Id_MEC'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_justifs['Id_MEC'] = df_justifs['Id_MEC'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 2. Reshape (Melt) to Long Format
    
    # Identify Indicator Columns in Grades (1.1, 1.2, ..., 3.17)
    # We look for columns that match pattern \d+\.\d+
    grade_cols = [c for c in df_grades.columns if re.match(r'^\d+\.\d+$', c)]
    
    # Reshape Grades
    df_grades_melted = df_grades.melt(
        id_vars=['Id_MEC'], 
        value_vars=grade_cols, 
        var_name='Indicator', 
        value_name='Grade'
    )
    
    # Identify Indicator Columns in Justifications
    # Justification file has columns "1.1", "1.2" etc as well
    justif_cols = [c for c in df_justifs.columns if re.match(r'^\d+\.\d+$', c)]
    
    # Reshape Justifications
    df_justifs_melted = df_justifs.melt(
        id_vars=['Id_MEC'], 
        value_vars=justif_cols, 
        var_name='Indicator', 
        value_name='Justification'
    )
    
    # 3. Merge
    print("Merging datasets...")
    # Merge on Id_MEC and Indicator
    merged = pd.merge(df_grades_melted, df_justifs_melted, on=['Id_MEC', 'Indicator'], how='inner')
    
    # 4. Filter for Low Grades (< 5)
    # Grades might be comma separated strings "4,50" or "NSA"
    def parse_grade(val):
        if pd.isna(val): return None
        val_str = str(val).strip().upper()
        if 'NSA' in val_str or 'NAN' in val_str or val_str == '': return None
        # Remove non-numeric except comma/dot
        clean_val = re.sub(r'[^\d,.]', '', val_str)
        try:
            return float(clean_val.replace(',', '.'))
        except:
            return None

    merged['Grade_Float'] = merged['Grade'].apply(parse_grade)
    
    # Filter: Grade < 5
    low_grades = merged[merged['Grade_Float'] < 5].copy()
    
    print(f"Found {len(low_grades)} instances of grades < 5.")
    
    if len(low_grades) == 0:
        print("No low grades found. Check parsing logic or data.")
        return

    # 5. Group and Analyze
    output_lines = []
    output_lines.append(f"ANALYSIS OF INDICATORS WITH GRADE < 5\n")
    output_lines.append(f"Total instances found: {len(low_grades)}\n")
    output_lines.append("="*80 + "\n")

    # Define a helper to extract keywords
    def get_top_keywords(text_series, n=15):
        all_words = []
        for text in text_series:
            if not isinstance(text, str): continue
            # Basic tokenization
            words = re.findall(r'\b\w+\b', text.lower())
            filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]
            all_words.extend(filtered)
        return Counter(all_words).most_common(n)

    # Group by Indicator and sort by extraction number (1.1, 1.2 etc)
    # Helper to sort indicators naturally
    def indicator_key(s):
        try:
            parts = s.split('.')
            return (int(parts[0]), int(parts[1]))
        except:
            return (99, 99)

    grouped = low_grades.groupby('Indicator')
    sorted_indicators = sorted(grouped.groups.keys(), key=indicator_key)

    for indicator in sorted_indicators:
        group_df = grouped.get_group(indicator)
        count = len(group_df)
        
        output_lines.append(f"\nINDICATOR: {indicator}")
        output_lines.append(f"Count of grades < 5: {count}")
        
        # Calculate Average Grade for these low cases
        avg_low_grade = group_df['Grade_Float'].mean()
        output_lines.append(f"Average of these low grades: {avg_low_grade:.2f}")
        
        # Keyword Analysis
        keywords = get_top_keywords(group_df['Justification'])
        output_lines.append(f"Frequent Terms: {', '.join([f'{w}({c})' for w, c in keywords])}")
        output_lines.append("-" * 40)
        
        # List Justifications
        for idx, row in group_df.iterrows():
            output_lines.append(f"  [Grade: {row['Grade']}] (Course ID: {row['Id_MEC']})")
            justification = str(row['Justification']).strip()
            # Wrap text for readability
            # Wrap text for readability (simple approach without dedent)
            for line in justification.split('\n'):
                 output_lines.append(f"    {line.strip()}")
            output_lines.append("") # Empty line between items
            
        output_lines.append("=" * 80 + "\n")

    # Save Report
    with open('low_grades_justifications.txt', 'w', encoding='utf-8') as f:
        f.writelines([l + '\n' for l in output_lines])
    
    print("Analysis complete. Saved to 'low_grades_justifications.txt'.")

if __name__ == "__main__":
    analyze_content()

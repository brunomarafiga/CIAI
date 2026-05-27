import json
from pathlib import Path
import config

def test_relatorio():
    relatorio_path = config.OUTPUT_RELATORIO_JSON
    
    print(f"Testando {relatorio_path.name}...")
    
    # 1. Verifica existência do arquivo
    assert relatorio_path.exists(), "O arquivo relatorio.json não foi gerado."
    
    with open(relatorio_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # 2. Verifica se é uma lista
    assert isinstance(data, list), "O JSON deve ser uma lista de registros."
    assert len(data) > 0, "O JSON está vazio."
    
    # 3. Verifica os campos obrigatórios
    required_fields = [
        'ID_DOCUMENTO', 'Curso', 'Id_MEC', 'Ano_avaliacao', 'Modalidade', 
        'Cidade', 'Campus', 'Indicador', 'Nota_do_indicador', 'Justificativa'
    ]
    
    missing_fields_docs = []
    
    unique_pdfs = set()
    unique_courses = set()
    invalid_indicators = set()
    invalid_conceitos = set()
    invalid_mec_ids = set()
    invalid_notas = set()
    na_modality_count = 0
    ni_id_mec_count = 0
    
    valid_indicators = [f"1.{i}" for i in range(1, 25)] + \
                       [f"2.{i}" for i in range(1, 17)] + \
                       [f"3.{i}" for i in range(1, 18)] + \
                       ['CONCEITO_FINAL_CONTINUO', 'CONCEITO_FINAL_FAIXA']
    
    for idx, item in enumerate(data):
        for field in required_fields:
            if field not in item:
                missing_fields_docs.append((idx, field))
                
        if 'ID_DOCUMENTO' in item:
            unique_pdfs.add(item['ID_DOCUMENTO'])
        if 'Curso' in item and item['Curso'] != 'N/I':
            unique_courses.add(item['Curso'])
            
        if 'Modalidade' in item and item['Modalidade'] in ['N/A', 'N/I']:
            na_modality_count += 1
            
        if 'Id_MEC' in item:
            mec_id = item['Id_MEC']
            if mec_id == 'N/I':
                ni_id_mec_count += 1
            else:
                if not isinstance(mec_id, str) or len(mec_id) != 8 or not mec_id.isdigit():
                    invalid_mec_ids.add(mec_id)
            
        if 'Indicador' in item:
            if item['Indicador'] not in valid_indicators:
                invalid_indicators.add(item['Indicador'])
                
        if item['Indicador'] == 'CONCEITO_FINAL_CONTINUO':
            c_continuo = item.get('Nota_do_indicador')
            if c_continuo != "N/I":
                try:
                    val = float(c_continuo)
                    if not (1 <= val <= 5):
                        invalid_conceitos.add(f"Continuo={c_continuo}")
                except ValueError:
                    invalid_conceitos.add(f"Continuo={c_continuo}")
                    
        if item['Indicador'] == 'CONCEITO_FINAL_FAIXA':
            c_faixa = item.get('Nota_do_indicador')
            if c_faixa != "N/I":
                try:
                    val = float(c_faixa)
                    if not (1 <= val <= 5):
                        invalid_conceitos.add(f"Faixa={c_faixa}")
                except ValueError:
                    invalid_conceitos.add(f"Faixa={c_faixa}")
                
        nota = item.get('Nota_do_indicador')
        if item['Indicador'] not in ['CONCEITO_FINAL_CONTINUO', 'CONCEITO_FINAL_FAIXA']:
            if nota not in {"1", "2", "3", "4", "5", "NSA", ""}:
                invalid_notas.add(nota)
                
    # Asserções e Relatórios
    assert len(missing_fields_docs) == 0, f"Campos ausentes encontrados: {missing_fields_docs[:5]}..."
    
    print(f"✅ Arquivo JSON válido. Total de justificativas: {len(data)}")
    print(f"✅ Total de PDFs únicos processados: {len(unique_pdfs)} (Esperado: ~63)")
    print(f"✅ Total de Cursos únicos: {len(unique_courses)}")
    
    if invalid_indicators:
        print(f"❌ ERRO: Indicadores inválidos encontrados: {invalid_indicators}")
    else:
        print("✅ Todos os indicadores estão dentro do formato esperado (1.x, 2.x, 3.x).")
        
    if invalid_conceitos:
        print(f"❌ ERRO: Conceitos inválidos encontrados (devem ser numéricos entre 1 e 5): {invalid_conceitos}")
    else:
        print("✅ Todos os conceitos finais estão no formato numérico correto (entre 1 e 5).")

    if invalid_mec_ids:
        print(f"❌ ERRO: MEC IDs inválidos encontrados (devem ter 8 dígitos numéricos): {invalid_mec_ids}")
    else:
        print("✅ Todos os MEC IDs estão corretos (8 dígitos ou 'N/I').")

    if invalid_notas:
        print(f"❌ ERRO: Notas de indicador inválidas encontradas: {invalid_notas}")
    else:
        print("✅ Todas as notas de indicadores estão normalizadas (1-5, 'NSA' ou '').")
        
    if na_modality_count > 0:
        print(f"⚠️ AVISO: {na_modality_count} registros possuem Modalidade 'N/A' ou 'N/I'.")
    else:
        print("✅ Nenhuma Modalidade 'N/A' ou 'N/I' encontrada.")
        
    if ni_id_mec_count > 0:
        print(f"⚠️ AVISO: {ni_id_mec_count} registros possuem Id_MEC 'N/I'.")
    else:
        print("✅ Nenhum Id_MEC 'N/I' encontrado.")
        
    print("\nResumo do primeiro registro como exemplo:")
    for k, v in data[0].items():
        val_str = str(v)[:50] + ("..." if len(str(v)) > 50 else "")
        print(f"  {k}: {val_str}")
        
if __name__ == "__main__":
    test_relatorio()

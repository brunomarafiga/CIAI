"""
2_aplicar_renomeacao.py - CIAI
------------------------------
Le o rename_mapping.json gerado por 1_gerar_mapa_renomeacao.py
e PEDE CONFIRMAÇÃO EXPLÍCITA antes de renomear qualquer arquivo.

Uso:
    python 2_aplicar_renomeacao.py
"""

import json
from pathlib import Path

import config


def apply_renames():
    if not config.OUTPUT_MAP_JSON.exists():
        print("[ERRO] Arquivo rename_mapping.json nao encontrado.")
        print("       Execute primeiro: python 1_gerar_mapa_renomeacao.py")
        return

    with open(config.OUTPUT_MAP_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Filtra apenas originais onde o nome atual é diferente do nome novo
    to_rename = [r for r in records if r["Duplicate Status"] == "Original"
                 and Path(r["Original Path"]).name != r["New Name"]]

    if not to_rename:
        print("[Renamer] Nenhum arquivo precisa ser renomeado.")
        return

    print(f"\n[Renamer] {len(to_rename)} arquivo(s) serao renomeados:\n")
    for r in to_rename:
        orig_name = Path(r["Original Path"]).name
        print(f"  DE:   {orig_name}")
        print(f"  PARA: {r['New Name']}")
        print()

    resposta = input("Confirma a renomeacao? Digite SIM para continuar: ").strip().upper()
    if resposta != "SIM":
        print("[Renamer] Operacao cancelada pelo usuario.")
        return

    count = 0
    for row in to_rename:
        old_path = Path(row["Original Path"])
        if not old_path.exists():
            print(f"  [Ignorado] Nao encontrado: {old_path.name}")
            continue

        new_path = old_path.parent / row["New Name"]
        if new_path.exists():
            print(f"  [Skip] Destino ja existe: {row['New Name']}")
            continue

        try:
            old_path.rename(new_path)
            count += 1
            print(f"  [OK] {old_path.name} -> {row['New Name']}")
        except Exception as e:
            print(f"  [Erro] Falha ao renomear {old_path.name}: {e}")

    print(f"\n[Renamer] {count} arquivo(s) renomeados com sucesso.")


if __name__ == "__main__":
    apply_renames()

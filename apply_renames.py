import os
import csv

# Configuration
ROOT_DIR = r"c:/Users/bruno/OneDrive - ufpr.br/Arquivos de Coordenadoria de Indicadores E Avaliação Institucional - 1 - AVALIAÇÃO IN LOCO/2 - RELATÓRIOS/Relatórios 2022-2025"
MAPPING_CSV = r"c:/Users/bruno/OneDrive - ufpr.br/Arquivos de Coordenadoria de Indicadores E Avaliação Institucional - 1 - AVALIAÇÃO IN LOCO/2 - RELATÓRIOS/Relatórios 2022-2025/rename_mapping.csv"

def apply_renames():
    """Applies the renames based on the mapping CSV."""
    
    # Read the mapping
    renames = []
    duplicates = []
    
    with open(MAPPING_CSV, "r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            original_path = row["Original Path"]
            new_name = row["New Name"]
            duplicate_status = row["Duplicate Status"]
            
            if duplicate_status == "Duplicate":
                duplicates.append(original_path)
                continue
            
            # Get directory of original file
            original_dir = os.path.dirname(original_path)
            new_path = os.path.join(original_dir, new_name)
            
            renames.append((original_path, new_path))
    
    # Apply renames
    print(f"Found {len(renames)} files to rename")
    print(f"Found {len(duplicates)} duplicate files (will not be renamed)")
    
    renamed_count = 0
    error_count = 0
    
    for old_path, new_path in renames:
        try:
            if os.path.exists(old_path):
                # Check if target already exists
                if os.path.exists(new_path):
                    print(f"WARNING: Target already exists, skipping: {new_path}")
                    error_count += 1
                    continue
                    
                os.rename(old_path, new_path)
                renamed_count += 1
                print(f"✓ Renamed: {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
            else:
                print(f"ERROR: File not found: {old_path}")
                error_count += 1
        except Exception as e:
            print(f"ERROR renaming {old_path}: {e}")
            error_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Successfully renamed: {renamed_count} files")
    print(f"Errors: {error_count}")
    print(f"Duplicates found: {len(duplicates)}")
    
    if duplicates:
        print(f"\n=== Duplicate Files ===")
        for dup in duplicates:
            print(f"- {dup}")

if __name__ == "__main__":
    response = input("This will rename all files based on rename_mapping.csv. Continue? (yes/no): ")
    if response.lower() in ["yes", "y", "sim", "s"]:
        apply_renames()
    else:
        print("Renaming cancelled.")

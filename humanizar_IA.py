import google.generativeai as genai
import os

# Configuração da API (Mesma chave do seu script analisellm.py)
GOOGLE_API_KEY = "AIzaSyBdxeibulQKkm5XxdTLqb-uwXp7CwSPjT8"
genai.configure(api_key=GOOGLE_API_KEY)

# Modelo (usando o mesmo que já funcionou)
model = genai.GenerativeModel('models/gemini-3-flash-preview')

def humanizar_texto(texto):
    """
    Reescreve o texto para torná-lo mais natural, fluido e humano.
    """
    prompt = f"""
    Atue como um editor de texto sênior. Seu objetivo é "humanizar" o texto abaixo.
    
    TEXTO ORIGINAL:
    "{texto}"
    
    DIRETRIZES:
    1. Melhore a fluidez e a coesão.
    2. Substitua termos robóticos ou excessivamente repetitivos por sinônimos naturais.
    3. Mantenha o sentido original e a precisão das informações.
    4. O tom deve ser profissional, mas leve e agradável de ler.
    
    Retorne APENAS o texto reescrito.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Erro ao processar: {e}"

# Exemplo de uso
if __name__ == "__main__":
    texto_exemplo = "O cachorro marrom rápido pulou sobre o cão preguiçoso."
    print("--- Texto Original ---")
    print(texto_exemplo)
    print("\n--- Texto Humanizado (IA) ---")
    print(humanizar_texto(texto_exemplo))

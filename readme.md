# 1. Cria o ambiente virtual (opcional, mas recomendado)
python -m venv .venv

# 2. Ativa o ambiente virtual
# No Linux/macOS:
source .venv/bin/activate
# No Windows (Prompt de Comando):
.venv\Scripts\activate
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Instala as dependências a partir do arquivo
pip install -r requirements.txt

# No Linux/macOS
export GEMINI_API_KEY="sua_chave_aqui"

# No Windows (PowerShell)
$env:GEMINI_API_KEY="sua_chave_aqui"

# No Windows (CMD)
set GEMINI_API_KEY=sua_chave_aqui
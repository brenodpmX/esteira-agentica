"""Fonte única de verdade para arquivos protegidos do core.

Estes arquivos são memória exclusiva da esteira e NUNCA devem ser lidos,
escritos ou criados por nenhum agente (nem testes de forma não-isolada).

Usado por:
  - src/core/agent.py (validação de prompts)
  - src/core/context_generator.py (geração de CONTEXT.md)
"""

# Lista de padrões de arquivos protegidos.
# Exemplos: ".pipe/throttle" casa com o arquivo real; ".pipe/throttle-*.json"
# é um padrão glob que casa com ".pipe/throttle-github.json", etc.
PROTECTED_PATHS = [
    ".pipe/boards/*/snapshot.json",
    ".pipe/changeQueue.json",
    ".pipe/throttle",
    ".pipe/throttle.json",
    ".pipe/throttle-*.json",
    ".pipe/sessions.json",
    ".pipe/deadLetter.json",
    ".pipe/orphanFiles.json",
    ".pipe/pipe.lock",
]

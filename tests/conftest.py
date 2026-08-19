"""Configuração global de testes pytest.

Sandbox: os testes rodam em um diretório temporário isolado do cwd real.
Isso garante que:

1. Nenhum artefato de teste (logs, .pipe, .kiro) é gravado no repositório de código
2. Cada execução da suíte não interfere com estado pré-existente de produção
3. Imports de módulos do core (ex: src.core.log) que criam diretórios em tempo
   de import o fazem apenas no sandbox, não no cwd real.

O hook pytest_configure roda ANTES da importação de qualquer módulo de teste,
garantindo que a mudança de cwd ocorra antes que src.core.log (e outros módulos
que criam efeitos colaterais de escrita em tempo de import) seja importado.
"""

import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Roda ANTES de imports de testes e fixtures.
    
    Cria um diretório temporário, troca para ele, e registra o cwd original
    para restauração após os testes.
    """
    # Salva o cwd original para pytest restaurar depois.
    original_cwd = os.getcwd()
    config._original_cwd = original_cwd
    
    # Cria um diretório temporário único para essa execução de testes.
    temp_dir = tempfile.mkdtemp(prefix="pytest_pipe_", suffix="_sandbox")
    config._temp_dir = temp_dir
    
    # Muda para o sandbox.
    os.chdir(temp_dir)


def pytest_unconfigure(config):
    """Roda DEPOIS de todos os testes.
    
    Restaura o cwd original e limpa o diretório temporário.
    """
    if hasattr(config, '_original_cwd'):
        os.chdir(config._original_cwd)
    
    if hasattr(config, '_temp_dir'):
        import shutil
        try:
            shutil.rmtree(config._temp_dir, ignore_errors=True)
        except Exception:
            pass  # Se falhar a limpeza, não quebra o teste.

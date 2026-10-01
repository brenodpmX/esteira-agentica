"""Regressões dos cenários de referência sob o novo formato de camadas (CA-6/CA-7).

CT-08 — diretório de trabalho obrigatório no prompt
CT-09 — preparação de branch (reutilizar vs. criar atômica)
CT-11 — leitura/escrita dos arquivos da tarefa
CT-12 — finalização e transição de coluna
CT-14 — isolamento de repositório/diretório preservado (RN-06)
"""

import pytest

from tests._composicao_helpers import canonical_config, make_task, prompt_for


class TestDiretorioTrabalho:

    def test_secao_e_cd_presentes(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path)
        prompt = prompt_for(tmp_path, config, task)
        assert "## Diretório de trabalho (OBRIGATÓRIO)" in prompt
        assert "cd " in prompt
        assert "NUNCA rode git fora" in prompt

    def test_cita_clone_do_repo(self, tmp_path):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(tmp_path))
        assert "repo/main" in prompt.replace("\\", "/")


class TestBranch:

    @pytest.mark.parametrize("gitevents", ["create", "create-merge"])
    def test_criacao_atomica_de_origin(self, tmp_path, gitevents):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(tmp_path, gitevents=gitevents))
        assert "ATÔMICA" in prompt
        assert "origin/main" in prompt
        assert "NUNCA" in prompt and "HEAD" in prompt
        assert "#108" in prompt

    @pytest.mark.parametrize("gitevents", ["use", "merge"])
    def test_sem_criacao_opera_na_existente(self, tmp_path, gitevents):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(
            tmp_path, gitevents=gitevents,
            body="# foo\n\nDesc.\n\n📝\nbranch: feature/308-foo\n"))
        assert "não cria uma branch nova" in prompt
        assert "ATÔMICA" not in prompt

    def test_idempotencia_reuso(self, tmp_path):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(tmp_path, gitevents="create"))
        assert "idempotente" in prompt.lower()
        assert "NÃO crie outra branch" in prompt


class TestArquivosDaTarefa:

    def test_caminhos_absolutos_dos_tres_arquivos(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, issue_id="308", slug="foo")
        prompt = prompt_for(tmp_path, config, task)
        base = str((tmp_path / ".pipe" / "boards" / "entrega" / "desenvolvimento").resolve())
        assert f"{base}/308-foo-body.md" in prompt.replace("\\", "/")
        assert f"{base}/308-foo-history.md" in prompt.replace("\\", "/")
        assert f"{base}/308-foo-addcomment.md" in prompt.replace("\\", "/")
        assert "assine com" in prompt


class TestTransicao:

    def test_secao_e_mv_por_condicao(self, tmp_path):
        config = canonical_config()
        task = make_task(tmp_path, change={"advance": "execucao-testes",
                                           "revisar-caso-de-teste": "casos-de-teste"})
        prompt = prompt_for(tmp_path, config, task)
        assert "## Transição de coluna" in prompt
        assert "**advance**" in prompt
        assert "**revisar-caso-de-teste**" in prompt
        assert "execucao-testes" in prompt
        assert "casos-de-teste" in prompt


class TestIsolamentoRepo:

    def test_confina_ao_work_dir_do_repo(self, tmp_path):
        config = canonical_config()
        prompt = prompt_for(tmp_path, config, make_task(tmp_path))
        p = prompt.replace("\\", "/")
        assert "repo/main" in p
        # Não instrui operar no diretório da esteira (.pipe é só leitura dos arquivos).
        assert "cd " in prompt

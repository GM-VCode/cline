# ============================================================
# app/agent/apply.py — class PatchApplier
# Aplica edições cirúrgicas ("edits") em arquivos existentes:
# [{"file": ..., "find": ..., "replace": ...}].
#
# Regra de segurança:
# "find" deve ocorrer EXATAMENTE 1x no arquivo.
# 0x (não achou) ou 2x+ (ambíguo) rejeita a edição inteira
# sem modificar nada.
#
# Escrita completa continua via "files".
# ============================================================

import os

from typing import Any, cast


class PatchApplier:
    """Aplica edições de trecho em arquivos de projeto, com atomicidade."""

    def apply(
        self,
        project_dir: str,
        edits: object
    ) -> tuple[bool, list[str]]:
        """
        Aplica uma lista de edits.

        Retorna:
            (ok: bool, report: list[str])

        `edits` chega como saída não-confiável do modelo
        (objeto genérico), então é validado com isinstance antes do uso.

        Todas as edições são validadas ANTES de qualquer escrita.
        Se uma falhar, nenhuma é aplicada.
        """

        if not isinstance(edits, list):
            return False, ["campo 'edits' deve ser uma lista"]

        typed_edits = cast(list[dict[str, Any]], edits)

        project_dir = os.path.abspath(project_dir)

        # ========================================================
        # 1) VALIDA TUDO PRIMEIRO
        # ========================================================

        plans: list[tuple[str, str, str]] = []

        for i, edit in enumerate(typed_edits):
            plan = self._validate_one(
                project_dir,
                edit,
                i
            )

            if isinstance(plan, str):
                return False, [plan]

            plans.append(plan)

        # ========================================================
        # 2) APLICA AS EDIÇÕES
        # ========================================================

        report: list[str] = []

        for path, find, replace in plans:
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as fh:
                content = fh.read()

            with open(
                path,
                "w",
                encoding="utf-8",
                newline=""
            ) as fh:
                fh.write(
                    content.replace(
                        find,
                        replace,
                        1
                    )
                )

            report.append(
                f"editado: {os.path.relpath(path, project_dir)}"
            )

        return True, report

    def _validate_one(
        self,
        project_dir: str,
        edit: dict[str, Any],
        index: int
    ) -> str | tuple[str, str, str]:
        """
        Valida um edit.

        Retorna:
            (path, find, replace)
        ou:
            mensagem de erro.
        """

        # ========================================================
        # VALIDA O TIPO DO EDIT
        # ========================================================

        if not isinstance(edit, dict):
            return (
                f"edit[{index}]: "
                "deve ser objeto {file, find, replace}"
            )

        # ========================================================
        # PEGA OS CAMPOS
        # ========================================================

        rel = edit.get("file") or ""
        find = edit.get("find")
        replace = edit.get("replace")

        # ========================================================
        # VALIDA CAMPOS OBRIGATÓRIOS (AUSÊNCIA ANTES DO TIPO)
        # ========================================================
        # Edit incompleto (ex.: sem 'replace') deve reportar
        # "campos obrigatórios", e não "deve ser texto" — contrato
        # coberto por tests/test_patch.py
        # (test_edit_nao_dict_ou_incompleto).

        if not rel or find is None or replace is None:
            return (
                f"edit[{index}]: "
                "campos obrigatórios file/find/replace"
            )

        # ========================================================
        # VALIDA TIPOS (edits vem de fonte não-confiável)
        # ========================================================

        if not isinstance(rel, str):
            return f"edit[{index}]: campo 'file' deve ser texto"

        if not isinstance(find, str):
            return f"edit[{index}]: campo 'find' deve ser texto"

        if not isinstance(replace, str):
            return f"edit[{index}]: campo 'replace' deve ser texto"

        if find == "":
            return (
                f"edit[{index}]: "
                "campos obrigatórios file/find/replace"
            )

        # ========================================================
        # MONTA E VALIDA O CAMINHO
        # ========================================================

        path = os.path.abspath(
            os.path.join(
                project_dir,
                rel
            )
        )

        project_prefix = os.path.join(
            project_dir,
            ""
        )

        if not path.startswith(project_prefix):
            return (
                f"edit[{index}]: "
                f"caminho fora do projeto ({rel!r})"
            )

        # ========================================================
        # VERIFICA SE O ARQUIVO EXISTE
        # ========================================================

        if not os.path.isfile(path):
            return (
                f"edit[{index}]: arquivo não existe: {rel!r} "
                "(para criar, use 'files' em vez de 'edits')"
            )

        # ========================================================
        # LÊ O ARQUIVO
        # ========================================================

        try:
            with open(
                path,
                "r",
                encoding="utf-8"
            ) as fh:
                content = fh.read()

        except (OSError, UnicodeDecodeError) as exc:
            return (
                f"edit[{index}]: "
                f"não consegui ler {rel!r}: {exc}"
            )

        # ========================================================
        # GARANTE UMA ÚNICA OCORRÊNCIA
        # ========================================================

        count = content.count(find)

        if count == 0:
            return (
                f"edit[{index}]: "
                f"'find' não encontrado em {rel!r}. "
                f"Início real do arquivo: {content[:200]!r}"
            )

        if count > 1:
            return (
                f"edit[{index}]: "
                f"'find' ambíguo em {rel!r} "
                f"({count} ocorrências) — "
                "inclua mais contexto"
            )

        # ========================================================
        # RETORNA O PLANO VALIDADO
        # ========================================================

        return path, find, replace
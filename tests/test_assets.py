# tests/test_assets.py
"""O front não pode voltar a compilar CSS no navegador.

O `static/vendor/tailwind.js` era o build "Play CDN" do Tailwind: 407 KB
síncronos no <head> que varriam o DOM e geravam a folha de estilo em tempo de
execução (~3 s de tela sem estilo por carga) e recompilavam a cada swap do HTMX,
via MutationObserver. Agora o CSS é gerado no build (`npm run build:css`).
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BASE_HTML = RAIZ / "app" / "templates" / "base.html"


def test_compilador_de_runtime_nao_existe_mais():
    base = BASE_HTML.read_text(encoding="utf-8")
    assert not (RAIZ / "app" / "static" / "vendor" / "tailwind.js").exists()
    assert "vendor/tailwind.js" not in base
    # A config agora é um arquivo lido no build; o que não pode voltar é a
    # atribuição em runtime (`tailwind.config = {...}`) dentro da página.
    assert "tailwind.config =" not in base
    assert (RAIZ / "tailwind.config.js").exists()


def test_css_compilado_existe_e_esta_referenciado():
    css = RAIZ / "app" / "static" / "css" / "tailwind.css"
    assert css.exists(), "rode `npm run build:css`"
    assert "css/tailwind.css" in BASE_HTML.read_text(encoding="utf-8")
    # Um arquivo com utilitárias de verdade, não um stub vazio.
    assert len(css.read_text(encoding="utf-8")) > 5_000


def _luminancia(hexa: str) -> float:
    """Luminância relativa (WCAG 2.1, 1.4.3)."""
    canais = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lineares = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    r, g, b = lineares
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a: str, b: str) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _tokens_por_tema() -> dict[str, dict[str, str]]:
    """Lê theme.css e devolve {tema: {token: hex}} para os blocos data-theme."""
    import re

    texto = (RAIZ / "app" / "static" / "css" / "theme.css").read_text(encoding="utf-8")
    blocos = re.findall(r':root\[data-theme="(\w+)"\]\s*\{(.*?)\}', texto, re.S)
    return {
        tema: dict(re.findall(r"(--oriens-[\w-]+):\s*(#[0-9A-Fa-f]{6})", corpo))
        for tema, corpo in blocos
    }


@pytest.mark.parametrize("tema", ["dark", "light", "warm"])
def test_botao_primario_passa_em_45_1(tema):
    """O texto do botão primário precisa de 4,5:1 (WCAG AA, texto normal).

    Histórico: `.btn-primary` usava `--accent`, que no dark é #ffffff, com texto
    #EEEDFE — 1,07:1, invisível. Depois passou a usar `--oriens-btn`, que subiu
    para 3,76:1 (dark) e 3,87:1 (warm): legível, mas ainda abaixo de AA. Os
    valores atuais foram escurecidos preservando matiz e saturação.
    """
    tokens = _tokens_por_tema()[tema]
    fundo, texto = tokens["--oriens-btn"], tokens["--oriens-btn-text"]
    razao = _contraste(fundo, texto)
    assert razao >= 4.5, f"{tema}: {fundo} sobre {texto} = {razao:.2f}:1"

    # O hover nunca pode ser mais claro que o repouso (senão o contraste cai
    # justamente quando o cursor está no botão).
    razao_hover = _contraste(tokens["--oriens-btn-hover"], texto)
    assert razao_hover >= razao, f"{tema}: hover ({razao_hover:.2f}) mais claro que o repouso"


def test_botao_primario_tem_contraste_nos_tres_temas():
    """`.btn-primary` era `--accent` (#ffffff no dark) com texto #EEEDFE:
    contraste 1,07:1, ou seja, branco no branco."""
    theme = (RAIZ / "app" / "static" / "css" / "theme.css").read_text(encoding="utf-8")
    # Todo tema define o par do botão, e o texto do botão é sempre branco puro
    # sobre um fundo colorido (nunca sobre branco).
    assert theme.count("--oriens-btn-text:") == 4      # dark, light, warm, fallback
    assert theme.count("--oriens-btn-hover:") == 4
    # O azul fora de tema não é mais definido (o comentário que explica a
    # remoção cita o nome, então o que conta é a declaração).
    assert "--oriens-table-accent:" not in theme
    # E ninguém mais consome o token.
    for tpl in (RAIZ / "app" / "templates").rglob("*.html"):
        assert "var(--oriens-table-accent)" not in tpl.read_text(encoding="utf-8"), tpl


@pytest.mark.asyncio
async def test_paginas_nao_carregam_script_de_tailwind(client, test_user):
    for rota in ("/dashboard", "/projects", "/lists", "/capture", "/settings"):
        r = await client.get(rota)
        assert r.status_code == 200, rota
        assert "tailwind.js" not in r.text, rota
        assert "/static/css/tailwind.css" in r.text, rota

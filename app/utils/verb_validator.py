VERBS = frozenset({
    # Português
    "criar", "fazer", "implementar", "revisar", "atualizar", "corrigir",
    "testar", "escrever", "configurar", "definir", "organizar", "analisar",
    "planejar", "resolver", "verificar", "validar", "documentar", "refatorar",
    "adicionar", "remover", "editar", "migrar", "integrar", "publicar",
    "instalar", "estudar", "pesquisar", "aprender", "preparar", "enviar",
    "responder", "agendar", "reunir", "conversar", "ligar", "comprar",
    "pagar", "cancelar", "finalizar", "completar", "iniciar", "começar",
    "terminar", "continuar", "pausar", "retomar", "fechar", "abrir",
    "coletar", "processar", "mapear", "listar", "priorizar", "mover",
    "transferir", "sincronizar", "automatizar", "otimizar", "melhorar",
    "ajustar", "limpar", "deletar", "rever", "entregar", "apresentar",
    "aprovar", "rejeitar", "solicitar", "submeter", "confirmar", "checar",
    "construir", "montar", "projetar", "desenhar", "desenvolver", "depurar",
    "deployar", "lançar", "ler", "assistir", "falar", "gravar", "filmar",
    "fotografar", "postar", "compartilhar", "cobrar", "negociar", "contratar",
    "treinar", "avaliar", "mensurar", "reportar", "acompanhar", "monitorar",
    "rastrear", "registrar", "catalogar", "arquivar", "exportar", "importar",
    "baixar", "notificar", "informar", "comunicar", "discutir", "debater",
    "decidir", "delegar", "executar", "subir", "rodar", "mergir", "mergear",
    "clonar", "commitar", "levantar", "mapear", "priorizar", "separar",
    "conectar", "desconectar", "instalar", "desinstalar", "habilitar",
    "desabilitar", "ativar", "desativar", "prototipar", "reproduzir",
    # English
    "create", "make", "implement", "review", "update", "fix", "test",
    "write", "configure", "define", "organize", "analyze", "plan", "resolve",
    "verify", "validate", "document", "refactor", "add", "remove", "edit",
    "migrate", "integrate", "publish", "deploy", "install", "study",
    "research", "learn", "prepare", "send", "respond", "schedule", "meet",
    "call", "buy", "pay", "cancel", "finish", "complete", "start", "begin",
    "end", "continue", "pause", "resume", "close", "open", "collect",
    "process", "map", "prioritize", "transfer", "sync", "automate",
    "optimize", "improve", "adjust", "clean", "delete", "deliver", "present",
    "approve", "reject", "request", "submit", "confirm", "check", "build",
    "set", "run", "push", "pull", "read", "watch", "record", "post",
    "share", "hire", "train", "evaluate", "measure", "report", "track",
    "monitor", "register", "catalog", "archive", "export", "import",
    "download", "setup", "debug", "launch", "release", "notify", "discuss",
    "decide", "delegate", "execute", "ship", "draft", "sketch", "prototype",
    "refine", "merge", "clone", "commit", "rebase", "deploy", "enable",
    "disable", "connect", "disconnect",
})


def validate_starts_with_verb(title: str) -> tuple[bool, list[str]]:
    """Returns (is_valid, suggestions). Suggestions only when invalid."""
    words = title.strip().split()
    if not words:
        return False, []
    first = words[0].lower().rstrip(".,!?:;")
    if first in VERBS:
        return True, []
    rest = title.strip()
    return False, [
        f"Criar {rest}",
        f"Revisar {rest}",
        f"Implementar {rest}",
    ]

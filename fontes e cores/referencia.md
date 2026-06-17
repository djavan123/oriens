# Referência Visual — Kanban.png (Trello Dark Mode)

## Fonte

| Elemento         | Família              | Peso  | Tamanho |
|------------------|----------------------|-------|---------|
| Títulos de cards | System sans-serif    | 400   | 14px    |
| Header colunas   | System sans-serif    | 600   | 14px    |
| Metadata / tags  | System sans-serif    | 400   | 12px    |
| Botão "+"        | System sans-serif    | 400   | 14px    |

Stack usada pelo Trello:
```
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", Ubuntu, "Helvetica Neue", sans-serif
```
No projeto: usar **Inter** (já carregada via Google Fonts) — visualmente equivalente.

---

## Cores

### Backgrounds
| Token         | Hex       | Uso                          |
|---------------|-----------|------------------------------|
| page-bg       | #1D2125   | Fundo geral da página        |
| column-bg     | #282E33   | Fundo das colunas Kanban     |
| card-bg       | #22272B   | Fundo dos cards              |
| card-hover    | #2C333A   | Hover dos cards              |

### Texto
| Token         | Hex       | Uso                          |
|---------------|-----------|------------------------------|
| text-primary  | #B6C2CF   | Texto principal (títulos)    |
| text-secondary| #8C9BAB   | Texto secundário (metadata)  |
| text-muted    | #738496   | Placeholders, labels         |

### Bordas
| Token         | Hex       | Uso                          |
|---------------|-----------|------------------------------|
| border        | #3D4B55   | Bordas de cards e divisores  |

### Ação / Status
| Token         | Hex       | Uso                          |
|---------------|-----------|------------------------------|
| accent-blue   | #0C66E4   | Botão primário ("Criar")     |
| accent-light  | #579DFF   | Links, hover, foco ativo     |
| success-green | #4BCE97   | Labels verdes (concluído)    |
| warning-yellow| #E2B203   | Alertas amarelos             |
| alert-red     | #F87462   | Erros, alertas               |

### Labels de cards (cor na barra superior)
| Cor       | Hex       | Significado sugerido |
|-----------|-----------|----------------------|
| Verde     | #4BCE97   | Concluído / OK       |
| Amarelo   | #E2B203   | Atenção / pausa      |
| Vermelho  | #F87462   | Bloqueado / urgente  |
| Azul      | #579DFF   | Ativo / em andamento |
| Cinza     | #8C9BAB   | Sem status / neutro  |

---

## Layout das colunas (Kanban)

- **Largura da coluna:** ~272px (Trello usa 272px fixo)
- **Raio da coluna:** `border-radius: 12px` (rounded-xl)
- **Padding interno:** `12px`
- **Gap entre colunas:** `8-12px`
- **Raio dos cards:** `8-10px` (rounded-lg)
- **Padding dos cards:** `8-12px`
- **Sombra nos cards:** sutil (`box-shadow: 0 1px 0 rgba(9,30,66,.25)`)

## Estrutura de um card (Trello)
```
┌─────────────────────────┐
│ [tag colorida] [tag]    │  ← pequenos pills de cor no topo
│                         │
│ Título do card          │  ← text-primary, 14px, weight 400
│                         │
│ □ 0/1   📎 2   👤      │  ← metadata em text-secondary, 12px
└─────────────────────────┘
```

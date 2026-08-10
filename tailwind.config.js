/** Configuração do Tailwind do Oriens.
 *
 *  Antes isto vivia inline no <head> do base.html e era interpretado pelo
 *  compilador de runtime (tailwind.js, o build "Play CDN"). Agora o CSS é
 *  gerado no build (`npm run build:css`) e servido como arquivo estático —
 *  o navegador não compila mais nada.
 *
 *  As cores continuam apontando para os tokens `--oriens-*` de theme.css, que
 *  mudam por `data-theme`. Por isso a troca de tema segue sem reload: o CSS
 *  gerado é fixo, só o valor das variáveis muda.
 */
/** Cor de tema com suporte a modificador de opacidade.
 *
 *  Mapear direto para `var(--oriens-x)` faz `bg-oriens-accent/20` não gerar
 *  CSS nenhum — o Tailwind não sabe abrir um `var()` em canais. Eram 24 usos
 *  no app (hover dos checkboxes, badges de atraso/hoje, fundo de erro no
 *  login) todos silenciosamente sem cor, inclusive antes desta mudança.
 *
 *  `color-mix()` resolve sem tocar em theme.css: os tokens continuam hex e
 *  seguem servindo aos `style="color:var(--oriens-x)"` espalhados nos
 *  templates. Suportado por Chrome 111+, Safari 16.2+, Firefox 113+.
 */
const tema = (nome) => ({ opacityValue }) => {
  // Para a utilitária sem modificador, o Tailwind passa a *variável* de opacidade
  // (`var(--tw-bg-opacity)`), não um número — aí não há mistura a fazer.
  const alfa = Number(opacityValue)
  if (!Number.isFinite(alfa)) return `var(--${nome})`
  return `color-mix(in srgb, var(--${nome}) ${alfa * 100}%, transparent)`
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Os templates são a única fonte de classes. Nenhuma classe é montada em
  // Python (verificado), e as que vivem em variáveis Jinja (`{% set cb_border
  // = 'border-oriens-urgent' %}`) aparecem como string literal no arquivo —
  // então o extrator as encontra normalmente.
  content: ['./app/templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        'oriens-bg':          tema('oriens-bg'),
        'oriens-sidebar':     tema('oriens-sidebar'),
        'oriens-surface':     tema('oriens-surface'),
        'oriens-card':        tema('oriens-card'),
        'oriens-card-hover':  tema('oriens-card-hover'),
        'oriens-border':      tema('oriens-border'),
        'oriens-divider':     tema('oriens-divider'),
        'oriens-primary':     tema('oriens-primary'),
        'oriens-secondary':   tema('oriens-secondary'),
        'oriens-tertiary':    tema('oriens-tertiary'),
        'oriens-muted':       tema('oriens-muted'),
        'oriens-empty':       tema('oriens-empty'),
        'oriens-accent':      tema('oriens-accent'),
        'oriens-accent-hover':tema('oriens-accent-hover'),
        'oriens-accent-text': tema('oriens-accent-text'),
        'oriens-link':        tema('oriens-link'),
        'oriens-btn':         tema('oriens-btn'),
        'oriens-btn-text':    tema('oriens-btn-text'),
        'oriens-alert':       tema('oriens-alert'),
        'oriens-success':     tema('oriens-success'),
        'oriens-warning':     tema('oriens-warning'),
        'oriens-urgent':      tema('oriens-urgent'),
        'oriens-today':       tema('oriens-today'),
        'oriens-ok':          tema('oriens-ok'),
      },
      fontFamily: {
        sans: [
          '"Inter"',
          'ui-sans-serif',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Ubuntu',
          '"Helvetica Neue"',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}

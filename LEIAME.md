# Target Go · curso gratuito de trade e educação financeira

Feito a partir do AutoVídeo. Roda sozinho no GitHub (grátis):

- **Aula do dia, às 08:00 (Brasília):** vídeo longo (~12 min) seguindo a grade de `curso.json`.
  São 2 aulas de trade e depois 1 de educação financeira, e assim por diante.
  A aula entra na playlist do nível dela e ganha uma thumbnail com a foto do Leo (camisa, posição e layout mudam a cada aula).
  Também sai um corte vertical (Short) que você pode baixar e postar no TikTok.
- **Radar de notícias (de hora em hora, das 07h às 22h):** lê as manchetes. Quando alguma pode mexer forte com o
  mercado (nota 7 ou mais, de 0 a 10), publica um Short explicando o que aconteceu, por que pode mexer e o que observar.
  O gráfico usa cotações reais. Limite: 2 por dia.
- **Painel:** https://leoventurelli-cell.github.io/targetgo2026/

## Configuração (uma vez)

1. **Settings → Pages:** em Source escolha *Deploy from a branch*, depois Branch `main` e pasta `/docs`, e clique em Save.
2. **Settings → Secrets and variables → Actions → Secrets:** crie os mesmos segredos do autovideo:
   `GROQ_API_KEY` (ou `GEMINI_API_KEY`), `PEXELS_API_KEY`, `YT_CLIENT_SECRET`.
3. **Mesma tela → Variables:** crie `YT_CLIENT_ID` com o mesmo ID do cliente do autovideo.
4. **Google Cloud → APIs e serviços → Credenciais:** abra o cliente OAuth e, em *URIs de redirecionamento autorizados*,
   acrescente `https://leoventurelli-cell.github.io/targetgo2026/`.
5. **Painel → Conectar YouTube:** na tela do Google, escolha a conta de marca **Target Go**, e depois clique em Create no GitHub.
6. **Actions:** se aparecer o aviso, clique em *I understand… enable workflows*. Depois abra o **Relógio (aula das 8h)**
   e clique em *Run workflow* uma vez para ligar a corrente.

## Ajustes (Settings → Variables, todos opcionais)

| Variável | Padrão | Para quê |
|---|---|---|
| `VOZ` | `pt-BR-AntonioNeural` | voz masculina. A mais natural é `pt-BR-ThalitaMultilingualNeural` (feminina) |
| `VELOCIDADE_VOZ` | `+3%` | velocidade da fala |
| `DURACAO_AULA` | `12` | minutos de cada aula |
| `HORA_AULA` | `08:00` | hora em que a aula fica pública no YouTube |
| `YT_PRIVACIDADE` | `public` | `unlisted` para revisar antes de publicar |
| `NOTICIA_IMPACTO_MINIMO` | `7` | nota mínima para virar vídeo |
| `NOTICIAS_POR_DIA` | `2` | limite de notícias por dia |

## Grade de aulas

Está em `curso.json`. Para incluir uma aula, acrescente um item na lista `aulas` com `nivel`
(iniciante, intermediario, avancado, profissional ou educacao), `titulo` e `pontos` (o que a aula precisa cobrir).
O andamento fica em `docs/curso_estado.json`.

## Fotos da thumbnail

Ficam em `fotos/`, em PNG recortado com fundo transparente. Para a cor da camisa mudar, cada foto precisa de uma máscara
`<nome>.camisa.png` (branco = camisa). Com mais fotos (outras poses e expressões), o sistema alterna entre elas.

## Testar sem publicar

Actions → **Aula do dia** → Run workflow → desmarque "Publicar". O vídeo aparece no painel para baixar e a grade não avança.

---
Conteúdo educativo. Não é recomendação de investimento nem promessa de lucro.

# Dashboard de Vendas — Cartão de Todos

Dashboard estático (GitHub Pages) com as vendas das unidades Belém Centro, Manaus Centro, Manaus Norte, Osasco, Parintins e Porto Alegre Norte, a partir do relatório **Filiação por Vendedor** do CTN.

- `index.html` / `dashboard_vendas.html` — o dashboard (arquivo único, dados embutidos; abre offline).
- `data/base_vendas.csv` — a base linha a linha, no layout do CTN (Franquia, Matricula, Filiado, Telefone, Nome, Data, Vendedor, Login, Prospeccao).
- `data/resumo_diario.csv` — vendas por dia e unidade (vendas, filiação, refiliação).
- `data/por_vendedor.csv` — vendas por mês, unidade e vendedor.
- `data/meta.json` — período coberto e data da última atualização.
- `template.html` + `build.py` — geram o dashboard a partir dos CSVs do CTN.

## Atualizar

1. Exportar do CTN o relatório Filiação por Vendedor de cada unidade (CSV com as 9 colunas acima; a coluna Data aceita serial do Excel ou `dd/mm/aaaa hh:mm:ss`).
2. `python3 build.py <pasta_com_os_csvs> --repo .` — mescla com `data/base_vendas.csv` (sem duplicar matrículas) e regenera `index.html`.
3. Commit e push.

Links diretos por unidade: `#osasco`, `#belem_centro`, `#manaus_centro`, `#manaus_norte`, `#parintins`, `#porto_alegre_norte`.

## Atualização automática (GitHub Actions)

O workflow `.github/workflows/atualizar.yml` roda de hora em hora (07h–22h, horário de Brasília) e quando acionado manualmente (Actions → *Atualizar dashboard de vendas* → *Run workflow*). Ele usa `scripts/ctn_fetch.py` para baixar as vendas novas do CTN com uma sessão já logada, roda o `build.py` e faz commit só quando há venda nova (o GitHub Pages republica sozinho).

Configuração (uma vez, e sempre que a sessão do CTN expirar):

1. Faça login no CTN no seu navegador com **Lembrar de mim** marcado.
2. Com o CTN aberto, pressione F12 → aba **Network** → recarregue a página → clique na primeira requisição para `ctn.sistematodos.com.br` → em **Request Headers** copie o valor inteiro de `cookie`.
3. No repositório: **Settings → Secrets and variables → Actions → New repository secret**, nome `CTN_COOKIE`, cole o valor.
4. Em **Actions**, rode o workflow manualmente para testar. Se aparecer "SESSÃO EXPIRADA", repita os passos 1–3.

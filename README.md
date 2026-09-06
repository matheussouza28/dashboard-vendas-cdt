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

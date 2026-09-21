#!/usr/bin/env python3
"""Consolida CSVs do CTN (layout Filiação por Vendedor) em data/ e gera dashboard_vendas.html.
Uso: python3 build.py <pasta_com_csvs_ctn> [--repo <pasta_do_repo>]
Cada CSV: Franquia,Matricula,Filiado,Telefone,Nome,Data(serial Excel ou dd/mm/yyyy hh:mm:ss),Vendedor,Login,Prospeccao
Regras: dedup por Matricula (a última ocorrência vence); a base existente em data/base_vendas.csv é preservada e mesclada.
"""
import sys, os, glob, json, datetime as dt
import pandas as pd

src = sys.argv[1]
repo = sys.argv[sys.argv.index('--repo')+1] if '--repo' in sys.argv else os.path.dirname(os.path.abspath(__file__))
datadir = os.path.join(repo, 'data'); os.makedirs(datadir, exist_ok=True)
COLS = ['Franquia','Matricula','Filiado','Telefone','Nome','Data','Vendedor','Login','Prospeccao']

# Prefixo da matrícula de cada unidade. Rede de segurança do ctn_fetch.py: se
# uma venda de outra franquia passar pelo download (sessão do CTN trocada no
# meio do caminho), ela é descartada aqui e nunca chega ao dashboard. Também
# limpa o que já entrou antes desta checagem existir — em 21/09 uma venda de
# Alvorada entrou no CDT como Osasco. Mesma tabela do ctn_fetch.py.
PREFIXO = {
    'BELEM CENTRO': 'PA417', 'MANAUS CENTRO': 'AM348', 'MANAUS NORTE': 'AM312',
    'PORTO ALEGRE NORTE': 'RS329', 'OSASCO': 'SP266', 'PARINTINS': 'AM443',
    'ALVORADA': 'RS364',
}

def parse_dates(s):
    s = s.astype(str).str.strip()
    num = pd.to_numeric(s, errors='coerce')
    out = pd.to_datetime('1899-12-30') + pd.to_timedelta(num, unit='D')
    txt = pd.to_datetime(s.where(num.isna()), format='%d/%m/%Y %H:%M:%S', errors='coerce')
    return out.where(num.notna(), txt).dt.round('s')

frames = []
old = os.path.join(datadir, 'base_vendas.csv')
if os.path.exists(old):
    frames.append(pd.read_csv(old, dtype=str, encoding='utf-8-sig'))
for f in sorted(glob.glob(os.path.join(src, '*.csv'))):
    frames.append(pd.read_csv(f, dtype=str, encoding='utf-8-sig'))
df = pd.concat(frames, ignore_index=True)[COLS]
df['DataHora'] = parse_dates(df['Data'])
df = df.dropna(subset=['DataHora'])
# Antes do dedup: uma linha rotulada na unidade errada não pode esconder a certa.
_pref = df['Franquia'].map(PREFIXO)
_alheia = _pref.notna() & ~pd.Series([str(m).strip().startswith(p) if isinstance(p, str) else True
                                      for m, p in zip(df['Matricula'], _pref)], index=df.index)
if _alheia.any():
    print('DESCARTADAS %d vendas com matrícula de outra franquia:' % _alheia.sum())
    print(df.loc[_alheia, ['Franquia', 'Matricula', 'Data']].to_string(index=False))
    df = df[~_alheia]
df = df.sort_values(['DataHora','Matricula']).drop_duplicates(['Matricula'], keep='last')
df = df.sort_values(['Franquia','DataHora','Matricula'], kind='mergesort').reset_index(drop=True)
df['Data'] = df['DataHora'].dt.strftime('%d/%m/%Y %H:%M:%S')
df['Dia'] = df['DataHora'].dt.strftime('%Y-%m-%d'); df['Mes'] = df['Dia'].str[:7]
df[COLS].to_csv(old, index=False, encoding='utf-8')

d = df.assign(fil=(df.Prospeccao=='FILIAÇÃO').astype(int), ref=(df.Prospeccao=='REFILIAÇÃO').astype(int))
daily = d.groupby(['Dia','Franquia']).agg(vendas=('Matricula','size'), filiacao=('fil','sum'), refiliacao=('ref','sum')).reset_index()
vend = d.groupby(['Mes','Franquia','Vendedor']).agg(vendas=('Matricula','size'), filiacao=('fil','sum'), refiliacao=('ref','sum')).reset_index()
daily.to_csv(os.path.join(datadir,'resumo_diario.csv'), index=False)
vend.to_csv(os.path.join(datadir,'por_vendedor.csv'), index=False)

units = sorted(df.Franquia.unique().tolist())
last = df.Dia.max(); cutoff = (pd.Timestamp(last) - pd.Timedelta(days=13)).strftime('%Y-%m-%d')
rec = d[d.Dia >= cutoff]
recent = [[r.Dia, r.Franquia, int(r.DataHora.hour), r.Vendedor, int(r.fil)] for r in rec.itertuples()]
payload = {
  'atualizado_em': (dt.datetime.utcnow()-dt.timedelta(hours=3)).strftime('%d/%m/%Y %H:%M'),
  'periodo': {'inicio': df.Dia.min(), 'fim': df.Dia.max()},
  'unidades': units, 'total': int(len(df)),
  'daily': daily.values.tolist(),
  'vend': vend.values.tolist(),
  'recent': recent,
  'hoje': (dt.datetime.utcnow()-dt.timedelta(hours=3)).strftime('%Y-%m-%d'),
}
json.dump({k:v for k,v in payload.items() if k not in ('daily','vend','recent')}, open(os.path.join(datadir,'meta.json'),'w'), ensure_ascii=False, indent=1)
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html'), encoding='utf-8').read()
html = tpl.replace('__DATA__', json.dumps(payload, ensure_ascii=False, separators=(',',':')).replace('</', '<\\/'))
open(os.path.join(repo, 'dashboard_vendas.html'), 'w', encoding='utf-8').write(html)
open(os.path.join(repo, 'index.html'), 'w', encoding='utf-8').write(html)
print('base:', len(df), 'vendas |', df.Dia.min(), '→', df.Dia.max(), '| unidades:', units)
print(df.groupby(['Franquia','Mes']).size().unstack(fill_value=0).to_string())

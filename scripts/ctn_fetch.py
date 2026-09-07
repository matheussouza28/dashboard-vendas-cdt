#!/usr/bin/env python3
"""Baixa do CTN o relatório Filiação por Vendedor de cada unidade e grava CSVs em src/.

Usa a sessão já logada do CTN (variável de ambiente CTN_COOKIE = cabeçalho Cookie copiado do navegador).
Período: do último dia presente em data/meta.json (inclusive) até hoje, em blocos por mês.
Saída: src/ctn_<unidade>.csv com Franquia,Matricula,Filiado,Telefone,Nome,Data,Vendedor,Login,Prospeccao
"""
import os, sys, re, io, json, datetime as dt
import requests, openpyxl

BASE = 'https://ctn.sistematodos.com.br'
REPORT = BASE + '/paginas/filiado/FiliacaoPorVendedor.aspx'
UNITS = ['CARTAO DE BELEM CENTRO', 'CARTAO DE MANAUS CENTRO', 'CARTAO DE MANAUS NORTE',
         'CARTAO DE OSASCO', 'CARTAO DE PARINTINS', 'CARTAO DE PORTO ALEGRE NORTE']
COLS = ['Franquia', 'Matricula', 'Filiado', 'Telefone', 'Nome', 'Data', 'Vendedor', 'Login', 'Prospeccao']

cookie = os.environ.get('CTN_COOKIE', '').strip()
if not cookie:
    sys.exit('CTN_COOKIE não definido (Settings → Secrets and variables → Actions).')
mc_cookie = os.environ.get('MINHACONTA_COOKIE', '').strip()

s = requests.Session()
def load_cookies(header, domain):
    for part in header.split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            s.cookies.set(k.strip(), v.strip(), domain=domain, path='/')
load_cookies(cookie, 'ctn.sistematodos.com.br')
if mc_cookie:
    load_cookies(mc_cookie, 'minhaconta.sistematodos.com.br')
s.headers.update({
    'User-Agent': os.environ.get('CTN_UA', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'),
    'Accept-Language': 'pt-BR,pt;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': REPORT,
})

def now_br():
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)

def follow_forms(r, depth=0):
    """Se a resposta for um formulário de auto-envio (callback do login único), envia e continua."""
    ct = r.headers.get('content-type', '')
    if depth > 4 or not ct.startswith('text/html'):
        return r
    m = re.search(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>(.*?)</form>', r.text, re.S | re.I)
    if not m or 'name="code"' not in m.group(2) and "name='code'" not in m.group(2):
        return r
    action = m.group(1).replace('&amp;', '&')
    if action.startswith('/'):
        action = re.match(r'https?://[^/]+', r.url).group(0) + action
    fields = dict(re.findall(r'name=["\']([^"\']+)["\']\s+value=["\']([^"\']*)["\']', m.group(2)))
    fields = {k: v.replace('&amp;', '&') for k, v in fields.items()}
    r2 = s.post(action, data=fields, allow_redirects=True, timeout=60)
    return follow_forms(r2, depth + 1)

def hidden_fields(html):
    return {k: v.replace('&amp;', '&').replace('&quot;', '"') for k, v in re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)}

def confirm_franchise(r):
    """Tela 'Confirmar Franquia': escolhe Sub-Franquia EQUATORIAL (5) e CARTAO DE BELEM CENTRO (417) e confirma."""
    url = r.url
    html = r.text
    # 1) selecionar a sub-franquia (autopostback)
    data = hidden_fields(html)
    data.update({'__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlSubFranquia', '__EVENTARGUMENT': '',
                 'ctl00$ContentPlaceHolder1$ddlSubFranquia': '5'})
    r2 = s.post(url, data=data, allow_redirects=True, timeout=60)
    html2 = r2.text
    opts = dict((t.strip(), v) for v, t in re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>', html2))
    fr = opts.get('CARTAO DE BELEM CENTRO') or next(iter([v for t, v in opts.items() if t.startswith('CARTAO DE')]), '417')
    btn = re.search(r'<input[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="Confirmar"', html2) or re.search(r'<input[^>]*name="([^"]+)"[^>]*type="submit"[^>]*value="Confirmar"', html2)
    data = hidden_fields(html2)
    data.update({'__EVENTTARGET': '', '__EVENTARGUMENT': '',
                 'ctl00$ContentPlaceHolder1$ddlSubFranquia': '5',
                 'ctl00$ContentPlaceHolder1$ddlFranquia': fr})
    if btn:
        data[btn.group(1)] = 'Confirmar'
    else:
        data['ctl00$ContentPlaceHolder1$btnConfirmar'] = 'Confirmar'
    r3 = s.post(r2.url, data=data, allow_redirects=True, timeout=60)
    print('Tela "Confirmar Franquia" resolvida automaticamente (%s).' % ('ok' if 'ddlSubFranquia' not in r3.text else 'ainda pendente'))
    return r3

def get_page():
    r = follow_forms(s.get(REPORT, allow_redirects=True, timeout=60))
    if 'ddlSubFranquia' in r.text:
        confirm_franchise(r)
        r = follow_forms(s.get(REPORT, allow_redirects=True, timeout=60))
    if 'minhaconta.sistematodos.com.br' in r.url or 'Bem-vindo de volta' in r.text:
        sys.exit('SESSÃO EXPIRADA: o CTN pediu login. Faça login com "Lembrar de mim", copie o cookie novamente e atualize o secret CTN_COOKIE.')
    if 'ddlSubFranquia' in r.text:
        sys.exit('Não consegui passar da tela "Confirmar Franquia" automaticamente — abra o CTN no navegador, confirme uma franquia e copie o cookie de novo.')
    return r.text

def current_franchise(html):
    m = re.search(r'CARTAO DE [A-Z ]+', html)
    return m.group(0).strip() if m else None

def field(html, name):
    m = re.search(r'id="%s" value="([^"]*)"' % name, html)
    return m.group(1) if m else ''

def switch_to(unit):
    html = get_page()
    if current_franchise(html) == unit:
        return
    idx = {m.group(2).strip(): int(m.group(1)) for m in re.finditer(r'rptFranquias_lbtnFranquia_(\d+)"[^>]*>([^<]+)<', html)}
    if unit not in idx:
        sys.exit('Franquia %s não encontrada no menu (disponíveis: %s)' % (unit, ', '.join(idx)))
    data = {
        '__EVENTTARGET': 'ctl00$rptFranquias$ctl%02d$lbtnFranquia' % idx[unit],
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': field(html, '__VIEWSTATE'),
        '__VIEWSTATEGENERATOR': field(html, '__VIEWSTATEGENERATOR'),
        '__EVENTVALIDATION': field(html, '__EVENTVALIDATION'),
    }
    s.post(REPORT, data=data, allow_redirects=True, timeout=60)
    html = get_page()
    if current_franchise(html) != unit:
        sys.exit('Não consegui trocar para %s (cabeçalho mostra %s)' % (unit, current_franchise(html)))

def month_chunks(start, end):
    cur = start
    while cur <= end:
        last = (cur.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        yield cur, min(last, end)
        cur = last + dt.timedelta(days=1)

def fetch_xlsx(a, b):
    url = BASE + '/paginas/filiado/relatorio/FiliacaoPorVendedor.aspx'
    tries = [
        {'dataInicio': a.strftime('%d/%m/%Y'), 'dataFim': b.strftime('%d/%m/%Y')},
        {'dataInicio': a.strftime('%d/%m/%Y 00:00:00'), 'dataFim': b.strftime('%d/%m/%Y 23:59:59')},
    ]
    last = None
    for params in tries:
        r = follow_forms(s.get(url, params=params, timeout=120))
        if r.content[:2] != b'PK' and 'minhaconta' in r.url:
            # sessão do minhaconta necessária/expirada
            print('O gerador de relatório pediu login no minhaconta.' + ('' if mc_cookie else ' Cadastre o secret MINHACONTA_COOKIE (cookie do site minhaconta.sistematodos.com.br).'))
        ctype = r.headers.get('content-type', '')
        if r.content[:2] == b'PK':
            break
        last = (r.status_code, ctype, r.url, r.content[:400].decode('utf-8', 'replace'))
    else:
        st, ctype, u, body = last
        print('--- diagnóstico ---')
        print('status:', st, '| content-type:', ctype)
        print('url final:', u)
        print('início da resposta:', body.replace('\n', ' ')[:400])
        sys.exit('Parâmetros inválidos ou sessão perdida ao baixar %s–%s' % (a, b))
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c or '').strip() for c in rows[0]]
    if header[:9] != COLS:
        sys.exit('Layout inesperado do relatório: %s' % header)
    return rows[1:]

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta = json.load(open(os.path.join(root, 'data', 'meta.json'), encoding='utf-8'))
    start = dt.date.fromisoformat(meta['periodo']['fim'])
    today = now_br().date()  # Brasília
    if start > today:
        start = today
    out = os.path.join(root, 'src'); os.makedirs(out, exist_ok=True)
    total = 0
    for unit in UNITS:
        switch_to(unit)
        name = unit.replace('CARTAO DE ', '')
        lines = [','.join(COLS)]
        n = 0
        for a, b in month_chunks(start, today):
            for r in fetch_xlsx(a, b):
                r = list(r) + [None] * 9
                if not r[1]:
                    continue
                vals = [name] + [r[i] for i in range(1, 9)]
                d = vals[5]
                if isinstance(d, dt.datetime):
                    vals[5] = d.strftime('%d/%m/%Y %H:%M:%S')
                cells = []
                for v in vals:
                    v = '' if v is None else str(v)
                    cells.append('"%s"' % v.replace('"', '""') if re.search(r'[",\n;]', v) else v)
                lines.append(','.join(cells)); n += 1
        with open(os.path.join(out, 'ctn_%s.csv' % name.lower().replace(' ', '_')), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print('%-20s %5d vendas (%s a %s)' % (name, n, start, today))
        total += n
    print('total baixado:', total)

if __name__ == '__main__':
    main()

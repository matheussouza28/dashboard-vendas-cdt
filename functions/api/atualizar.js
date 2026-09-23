/**
 * Botão "Atualizar agora" do dashboard.
 *
 * Roda como Função do Cloudflare Pages, no MESMO endereço do dashboard —
 * por isso fica atrás do mesmo login do Cloudflare Access, sem precisar de
 * senha própria. O token do GitHub é um segredo do projeto Pages: ele nunca
 * é enviado ao navegador.
 *
 * Segredos/variáveis esperados no projeto Pages:
 *   GITHUB_TOKEN  (segredo)  fine-grained, permissão Actions: Read and write
 *   REPO          (variável) ex.: matheussouza28/dashboard-vendas-cdt
 *   WORKFLOW      (variável, opcional) padrão: atualizar.yml
 */
export async function onRequestPost({ env }) {
  const repo = env.REPO;
  const workflow = env.WORKFLOW || "atualizar.yml";
  const token = (env.GITHUB_TOKEN || "").trim();

  if (!token || !repo) {
    return json(500, { ok: false, erro: "Faltam GITHUB_TOKEN ou REPO nas configurações do Pages." });
  }

  const r = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        // A API do GitHub recusa requisição sem User-Agent.
        "User-Agent": "dashboard-botao-atualizar",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    },
  );

  // 204 é o sucesso deste endpoint — ele não devolve corpo.
  if (r.status === 204) {
    return json(200, { ok: true, mensagem: "Atualização pedida. Leva de 1 a 3 minutos." });
  }

  // 401 = token vencido; 403/404 = token sem Actions: write neste repositório.
  const corpo = await r.text().catch(() => "");
  return json(502, { ok: false, erro: `GitHub respondeu ${r.status}`, detalhe: corpo.slice(0, 300) });
}

/** Sem GET: o botão usa POST, e assim um link clicado por engano não dispara nada. */
export async function onRequestGet() {
  return json(405, { ok: false, erro: "Use POST." });
}

function json(status, corpo) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

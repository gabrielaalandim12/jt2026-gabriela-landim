"""
ANÁLISE CONSOLIDADA - VivaReal x Airbnb (Itapema/SC)

Regenera todas as tabelas-chave do projeto na pasta ./analisis/output.
NÃO apaga nada: cria um diretório novo de saída com CSV.

Premissas e limitações importantes (ver README_analisis.md):
  - A base com preço (Price_AV) cobre SOMENTE os anúncios ativos (n=1005 de 4441).
  - A receita anual é MODELADA (diária sazonal x dias x ocupação-cenário), NÃO real.
  - A ocupação é premissa (não há dados de reservas): conservador/base/otimista.
  - Usa-se mediana da diária (robusta a outliers).
  - O Airbnb não tem área: usa-se CAMAS como proxy de tamanho.
"""

import csv, os, io, collections, datetime, statistics, re, unicodedata, math

DATA_SRC = r"C:\Users\Gabriela\Desktop\Hackathon\jovens-talentos-2026-hackathon-data\data"
OUT_DIR = r"C:\Users\Gabriela\Desktop\Hackathon\analisis\output"
os.makedirs(OUT_DIR, exist_ok=True)

# ---------- utilidades ----------
def load(fname):
    with open(os.path.join(DATA_SRC, fname), encoding="utf-8-sig", newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        return header, list(r)

def fcv(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None

def norm_sub(t):
    t = (t or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = " ".join(t.split())
    rep = {"jardim praia mar":"jardim praiamar","taboleiro":"tabuleiro dos oliveiras",
           "tabuleiro":"tabuleiro dos oliveiras","meia praia frente mar":"meia praia",
           "none":"sem_bairro","itapema":"sem_bairro","ocean tower":"sem_bairro"}
    return rep.get(t, t)

def parse_dt(s):
    s = s.strip()
    if "." in s[:21]:
        s = s[:23]
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")

def wv(aq):
    return {"2025-01-06":"W1","2025-01-07":"W2","2025-01-20":"W3"}.get(aq.strip()[:10], "?")

def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None

OUTLIER_DIARIA = 10000.0     # diária absurda a limpar (vitrine/erro)
PRECIO_VENTA_MIN = 150000    # preço de venda mínimo aceito
PRECIO_VENTA_MAX = 13000000  # preço de venda máximo aceito (p99)
AREA_MIN, AREA_MAX = 15, 1000

# ============ 1. PRICE: diária final por (listing,date), última wave <= data ============
h, prows = load("Price_AV_Itapema.csv")
pix = {x:i for i,x in enumerate(h)}
daily = collections.defaultdict(dict)
for r in prows:
    lid, d, pr, aq = r[pix["airbnb_listing_id"]], r[pix["date"]], float(r[pix["price"]]), r[pix["aquisition_date"]]
    if pr > OUTLIER_DIARIA:
        continue                       # limpa outliers de diária (ex.: 10000)
    dd = parse_dt(aq).date()
    if d not in daily[lid] or dd > daily[lid][d][0]:
        daily[lid][d] = (dd, pr)
l_price = {lid: med(pr for d,(dd,pr) in dail.items()) for lid, dail in daily.items() if dail}

# ============ 2. períodos sazonais por listing ============
def period(dstr):
    m = dstr[:7]
    if m in ("2025-01","2025-02"): return "alta"
    if m == "2025-03":
        dd = datetime.datetime.strptime(dstr, "%Y-%m-%d").date()
        return "alta" if dd.day in (3,4,5) else "media"
    return "baixa"

per_l = collections.defaultdict(lambda: collections.defaultdict(list))
for lid, dail in daily.items():
    for dstr,(dd,pr) in dail.items():
        per_l[lid][period(dstr)].append(pr)

SCEN = {
    "conservador": {"alta":0.50,"media":0.35,"baixa":0.15},
    "base":         {"alta":0.65,"media":0.45,"baixa":0.25},
    "otimista":     {"alta":0.80,"media":0.60,"baixa":0.35},
}
M_ALTA, M_MEDIA, M_BAJA = 4, 4, 4
def receita_anual(lid, scen):
    tot = 0.0
    for pn, mn in (("alta",M_ALTA),("media",M_MEDIA),("baixa",M_BAJA)):
        dp = med(per_l[lid].get(pn, []))
        if dp is None:
            continue
        tot += dp * 30 * mn * scen[pn]
    return tot

# ============ 3. MESH (bairro) ============
h3, mrows = load("Mesh_Ids_Data_Itapema.csv")
mix = {x:i for i,x in enumerate(h3)}
sub_of = {r[mix["airbnb_listing_id"]]: norm_sub(r[mix["suburb"]]) for r in mrows}

# ============ 4. DETAILS (tipo, quartos, camas) ============
h2, drows = load("Details_Itapema.csv")
dix = {x:i for i,x in enumerate(h2)}
det = {}
for r in drows:
    det[r[dix["airbnb_listing_id"]]] = {
        "q": fcv(r[dix["number_of_bedrooms"]]),
        "camas": fcv(r[dix["number_of_beds"]]),
        "tipo": r[dix["listing_type"]].strip(),
        "rev": fcv(r[dix["number_of_reviews"]]),
    }

# ============ 5. VIVAREAL (preço de venda por bairro x quartos, faixa de área típica) ============
# Metodologia alinhada ao notebook final: o preço de venda considera somente imóveis
# dentro da faixa de área típica do seu nº de quartos (origem: relação quarto→área no VivaReal):
#   2q -> 60-90 m² | 3q -> 90-130 m² | 4q+ -> 130-200 m²  | 1q -> 0-60 m²
AREA_BAND_POR_Q = {"1q": (0, 60), "2q": (60, 90), "3q": (90, 130), "4q+": (130, 200)}

h4, vrows = load("VivaReal_Itapema.csv")
vix = {x:i for i,x in enumerate(h4)}
def qb(n):
    if n is None or n <= 0: return None
    return "1q" if n==1 else ("2q" if n==2 else ("3q" if n==3 else "4q+"))

viv = collections.defaultdict(list)   # (sub,q) -> [sale]
for r in vrows:
    sale = fcv(r[vix["sale_price"]]); area = fcv(r[vix["usable_area"]])
    beds = fcv(r[vix["bedrooms"]])
    ltype = r[vix["listing_type"]].strip()
    sub = norm_sub(r[vix["suburb"]])
    if sub in ("sem_bairro","") or ltype not in ("apartamento","casa"):
        continue
    if not sale or not (PRECIO_VENTA_MIN <= sale <= PRECIO_VENTA_MAX):
        continue
    if not area or not (AREA_MIN <= area <= AREA_MAX):
        continue
    q = qb(beds)
    if q is None:
        continue
    lo, hi = AREA_BAND_POR_Q[q]
    if not (lo <= area <= hi):
        continue
    viv[(sub, q)].append(sale)

# ============ 6. Tabela principal: retorno por (bairro x perfil) ============
MIN_N = 8   # amostra mínima de anúncios com preço (alinhado ao notebook)

# Perfis da tabela final (seleção curada, alinhada ao README): (bairro, quartos)
PERFIS = [
    ("morretes", "3q"),
    ("tabuleiro dos oliveiras", "3q"),
    ("tabuleiro dos oliveiras", "2q"),
    ("morretes", "2q"),
    ("centro", "2q"),
    ("meia praia", "3q"),
    ("centro", "3q"),
    ("meia praia", "2q"),
    ("meia praia", "4q+"),
]

def years_of(sub, q):
    """retorno (anos, cenário base) para um perfil de bairro x quartos."""
    ap = []
    for lid in l_price:
        if sub_of.get(lid) == sub and qb(det.get(lid,{}).get("q")) == q:
            rb = receita_anual(lid, SCEN["base"])
            if rb > 0:
                ap.append(rb)
    if len(ap) < MIN_N:
        return None
    rmed = statistics.median(ap)
    vs = viv.get((sub, q), [])
    if not vs:
        return None
    vmed = statistics.median(vs)
    return {"nAir": len(ap), "receita_base": rmed, "venda": vmed,
            "anos_base": vmed/rmed, "diaria": med([l_price[l] for l in l_price if sub_of.get(l)==sub and qb(det.get(l,{}).get("q"))==q])}

# % ativos por bairro
act_b = collections.Counter(sub_of.get(l, "?") for l in l_price)
tot_b = collections.Counter(sub_of.get(l, "?") for l in sub_of)

# ============ gerar tabelas ============
def csv_write(name, header, rows):
    with open(os.path.join(OUT_DIR, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)

# P1: retorno por perfil (perfis curados, amostra mínima 8, faixa de área típica)
p1 = []
for sub, q in PERFIS:
    yy = years_of(sub, q)
    if yy:
        p1.append([sub, q, yy["nAir"], round(yy["diaria"]), round(yy["receita_base"]),
                   round(yy["venda"]), round(yy["anos_base"], 1)])
csv_write("retorno_por_perfil.csv",
          ["bairro","perfil","nAir","diaria","receita_base","venda","anos_base"],
          sorted(p1, key=lambda x: x[6]))

# P2: diária por (bairro x quartos), somente apartamentos
p2 = []
for sub in ["meia praia","centro","morretes","tabuleiro dos oliveiras"]:
    for qq in [1,2,3,4]:
        v = [l_price[l] for l in l_price if sub_of.get(l)==sub
             and det.get(l,{}).get("tipo")=="apartamento" and int(det.get(l,{}).get("q") or 0)==qq]
        p2.append([sub, f"{qq}q", len(v), round(med(v) or 0)])
csv_write("diaria_por_bairro_quartos.csv", ["bairro","quartos","n","diaria_med"], p2)

# P3: sazonalidade global por período
p3 = []
d0 = datetime.date(2025,1,20); d1 = datetime.date(2025,4,6)
by_per = collections.defaultdict(list)
for lid, dail in daily.items():
    for d,(dd,pr) in dail.items():
        if d0 <= dd <= d1:
            by_per[period(d)].append(pr)
for per in ["alta","media","baixa"]:
    v = by_per.get(per, [])
    p3.append([per, len(v), round(med(v) or 0)])
csv_write("sazonalidad.csv", ["periodo","n_precios","diaria_med"], p3)

# P4: sazonalidade global por semana (usando a DATA DE ESTADIA `d`, não a data de aquisição)
p4 = []
wk = collections.defaultdict(list)
d0 = datetime.date(2025,1,20); d1 = datetime.date(2025,4,6)
for lid, dail in daily.items():
    for dstr, (dd, pr) in dail.items():
        ddt = datetime.datetime.strptime(dstr, "%Y-%m-%d").date()
        if d0 <= ddt <= d1:
            wk[ddt.isocalendar()[1]].append(pr)
for w in sorted(wk):
    v = wk[w]
    if len(v) >= 30:
        p4.append([f"wk{w:02d}", len(v), round(med(v) or 0)])
csv_write("sazonalidad_semana.csv", ["semana","n_precios","diaria_med"], p4)

print("Gerado em:", OUT_DIR)
for f in sorted(os.listdir(OUT_DIR)):
    print("  -", f)
print("OK")
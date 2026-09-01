# Análise VivaReal × Airbnb — Itapema/SC

Relatório consolidado da exploração completa dos dados. Não apaga nada: este relatório
documenta achados, premissas e limitações. O script `consolidar.py` regenera as tabelas
finais em `analisis/output/` com a limpeza de outliers aplicada.

## Fontes

| Arquivo | O que é | Chave |
|---|---|---|
| `Details_Itapema.csv` | Atributos dos anúncios Airbnb (aluguel de temporada) | `airbnb_listing_id` |
| `Hosts_ids_Itapema.csv` | Dados dos anfitriões | `owner_id` (± `airbnb_listing_id`) |
| `Mesh_Ids_Data_Itapema.csv` | Geolocalização + bairro por anúncio Airbnb | `airbnb_listing_id` |
| `Price_AV_Itapema.csv` | Série de preços diários por anúncio | `airbnb_listing_id` × `date` |
| `VivaReal_Itapema.csv` | Anúncios de venda | `listing_id` (sem chave comum Airbnb) |

`airbnb_listing_id` une Details/Mesh/Price; `owner_id` une Hosts/Details.
VivaReal não tem chave comum → comparação por bairro.

## Achados principais

### 1. A base com preço = mercado ATIVO (seleção)
- **Somente 1005 anúncios de 4441 têm série de preço.**
- Os "sem preço" (3442) têm mediana de **1 review e 8 fotos** vs 16/21 dos "com preço".
- ⇒ o Price_AV cobre o mercado em operação, não o inventário todo.
- **Cobertura por bairro**: Canto da Praia 32%, Centro 31%, Meia Praia 22%,
  Morretes 19%, Tabuleiro 16% → todos os números de receita são do mercado ativo.

### 2. Preço diário (última coleta ≤ data)
- Tratamos as 3 coletas (waves 06/01, 07/01, 20/01) usando a última válida por data
  (regra validada: não há coleta posterior à estadia).
- Diárias absurdas (ex.: R$ 10.000, vitrine/erro) limpas no script final.
- Mediana global da diária ≈ R$ 550 (janela 20/01–06/04).

### 3. O que explica a diária (regressão log, R² ≈ 0,45)
| Variável | Efeito | Leitura |
|---|---|--|
| Quartos | +19–21%/quarto | driver nº1 |
| Banheiros | +15%/banheiro | driver nº2 |
| Tipo (apto/casa/hotel vs outros) | +230–270% | importa muito |
| Hóspedes | +3%/hóspede | tamanho |
| Distância à orla | −12%/km | importa, mas menos |
| Nº de reviews | ≈0 (negativo) | NÃO é driver de preço |
| Fotos | ≈0 | não importa |

**Orla (proximidade do mar):** robusta — se mantém com exclusão de outliers, Huber e Winsor
(−10/−12%/km). Frente de mar paga ~12–26% a mais que a 1–2 km.
**Bairro:** agrega pouco depois da orla (R² +2 p.p.). Centro/Canto dão +20%, mas a maioria
vira não significativo.

### 4. Qualidade/dados estranhos (decisões tomadas)
- `star_rating == 0.0` ⇔ sem avaliação (sentinela, não é nota 0): 1540 anúncios, 100% alinhado.
- `bedrooms == 0` no VivaReal ⇒ não-residencial (terreno/comercial), não "0 quartos".
- Bairros: 26 grafias → ~15 canônicos (acentos/caixa e bairros duplicados).
- Duplicados VivaReal: só ~26–35 linhas repetidas + ~676 re-anúncios suspeitos
  (mesmo título+agência+IPTU ⇒ mesmo imóvel); a maioria das assinaturas são unidades distintas,
  então NÃO se deduplica por assinatura (removeria imóveis legítimos).

### 5. Rentabilidade (comprar para alugar por temporada)
Modelo de receita anual = diária sazonal × dias × ocupação (cenário). Só cenários.
Tabela gerada pelos perfis com **amostra mínima de 8 anúncios com preço** (`MIN_N = 8`).
O preço de venda considera a **faixa de área típica** de cada nº de quartos (abaixo) — metologia reproduzível no notebook.

**Origem das faixas de área** (relação quarto → área no VivaReal, script `morretes_area.py`):
- **2q:** área mediana 70 m² (p25 66, p75 74) → faixa 60–90 m²
- **3q:** área mediana 127 m² (p25 115, p75 140) → faixa 90–130 m²
- **4q+:** área mediana 188 m² (p25 169, p75 213) → faixa 130–200 m²

Usamos a faixa típica para **não misturar imóveis de portes muito diferentes** que tenham só o
mesmo nº de quartos (ex.: um 3q de 90 m² com um 3q de 300 m²). A conclusão central não muda
em relação a usar todos os imóveis, mas torna a comparação mais justa — sobretudo nos bairros
caros, que têm muitos imóveis grandes inflando a mediana de venda.

| Perfil (bairro × quartos) | Faixa de área | nAir | Diária | Receita base | Venda média | **Anos pagar (base)** | %ativos |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Morretes 3q (principal)** | 90–130 m² | 11 | 600 | 102,3k | 750k | **7,3** | 19% |
| Tabuleiro 2q *(indicação)* | 60–90 m² | 12 | 425 | 78,8k | 783k | **9,9** | 16% |
| **Centro 2q (compacto)** | 60–90 m² | 67 | 557 | 88,8k | 930k | **10,5** | 31% |
| Morretes 2q | 60–90 m² | 60 | 448 | 67,1k | 757k | **11,3** | 19% |
| Meia Praia 2q | 60–90 m² | 191 | 450 | 75,3k | 1,01M | **13,4** | 22% |
| Centro 3q | 90–130 m² | 47 | 790 | 114,6k | 1,85M | **16,1** | 31% |
| Meia Praia 3q | 90–130 m² | 332 | 650 | 103,0k | 1,72M | **16,7** | 22% |
| Meia Praia 4q+ | 130–200 m² | 68 | 1150 | 158,1k | 3,25M | **20,6** | 22% |

**Conclusões** (valores conforme metodologia reproduzível; amostra mínima de 8 anúncios):
- **Morretes 3q é o principal** (~7,3 anos no cenário base), mas **ainda é uma amostra pequena**
  (n=11 com preço + 306 vendas): usar como "aprox. 7–8 anos, com dispersão", não como número cravado.
- **Tabuleiro 3q foi excluído da tabela numérica** por ter **n=4 < 8** (amostra mínima). Deve ser
  tratado apenas como **indicação de apoio**, não como resultado confiável — aponta na *mesma direção*
  de Morretes, reforçando a tese de que o miolo barato rende bem.
- **Compacto do Centro (2q)** é o melhor perfil *dentro do Centro* (10,5 anos) — com a faixa de área
  típica ele melhora frente ao uso de todos os imóveis (12,6), pois elimina os imóveis grandes caros.
  A tese "compacto de centro é bom" fica mais forte, mas Morretes/Tabuleiro 2q seguem bem próximos (9,9–11,3).
- **Meia Praia/Centro 3q** (~16–17 anos) têm diária alta mas preço de compra desproporcional → não são o melhor yield.

### 6. Sazonalidade
| Período | Diária mediana | ratio vs baixa |
|---|---:|---:|
| Alta (jan-fev + carnaval) | 700–790 | ~1,46x |
| Média (março pós-carnaval) | 550 | 1,15x |
| Baixa (abril) | 450–480 | 1,00 |

- Verão/férias pagam ~1,46x mais que abril. Sem prêmio relevante de fim de semana.
- Mais forte em **apartamento** (1,46x) que em **casa** (1,11x).

## Premissas do modelo de receita (leia antes de usar)
1. **Ocupação NÃO é dado real** (não há reservas). Usamos 3 cenários:
   conservador (50/35/15% por período), base (65/45/25), otimista (80/60/35).
2. Alta/média/baixa projetadas como 4+4+4 meses do ano (aprox. da janela observada).
3. Airbnb **não tem área** → tamanho aproximado por nº de camas, não por m².
4. VivaReal filtrado (apto/casa, preço 150k–13M, área 15–1000 m², quartos>0).
5. Receita é **potencial**, não real: não contempla custos, impostos, manutenção nem taxas
   Airbnb. Só diária × ocupação.

## Limitações (para não superestimar)
- **A diária é a listada, não a cobrada** — pode haver desconto; não vemos.
- **block-ratio descartado como medida de ocupação** (r≈0 com reviews; bloqueios podem ser
  inatividade/manutenção, não reservas). Fica como contexto (% calendário bloqueado), nunca como receita.
- **Amostra pequena no miolo**: Morretes tem só 11 anúncios com preço (19% do estoque) — ainda é o
  perfil mais defensável, mas a estimativa é de baixa precisão. Tabuleiro tem só 4 (16%) → tratado
  apenas como indicação de apoio, não como resultado confiável. Ilhota compacto (4,2 anos) foi
  **descartado** (n~6 e preço anômalo de ~202–280k para 38 m²).
- **Orla e bairro medidos apenas no mercado ativo** (quem tem preço).
- **Sazonalidade observada só ~2,5 meses (jan-abr)**. O "ano" é projeção.
- **"Anos para pagar" é indicativo de ranking**, não previsão de ROI real.

## Perfis recomendados (com os matizes acima)
1. **Principal / mais defensável:** **Morretes, 3 quartos** (~7,3 anos no cenário base), com ressalva
   de amostra pequena (n=11 com preço) → tratar como indicação aproximada, não cifra fechada.
2. **Indicação de apoio:** Tabuleiro dos Oliveiras 3q (n=4, abaixo da amostra mínima de 8) —
   **excluído da tabela numérica**; serve apenas para corroborar a direção de Morretes (miolo barato rende bem).
3. **Boa opção compacta:** Morretes/Tabuleiro 2 quartos (9,9–11,3 anos) e **Centro 2q** (10,5 anos) —
   com a faixa de área típica, o compacto do Centro melhora e fica competitivo com o miolo.
4. **Compacto dentro do Centro:** melhor perfil do Centro (10,5 anos), útil para quem busca
   valor no centro; deixa de ser o pior caso quando se usa a faixa de área típica.
5. **Evitar como "yield":** Meia Praia 3q/4q+ e Centro 3q (16–21 anos): diária alta mas preço de
   compra desproporcional. Usar só se o objetivo for fluxo em alta temporada.
6. **Descartar do ranking:** Ilhota (amostra/preço anômalos) e bairros/perfis com n<8 (amostra mínima).

---
*Cada número veio de um script em Temp/opencode/ (métodos documentados). `consolidar.py`
regenera as tabelas finais em `analisis/output/` já com limpeza de outliers.*
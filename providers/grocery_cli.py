import json
import shutil
import subprocess
import re
import unicodedata

class ProviderError(RuntimeError):
    pass

STORES = {
    "mercadona": {"label":"Mercadona","key":"mercadona","aliases":["mercadona"]},
    "gadis": {"label":"Gadis","key":"gadis","aliases":["gadis"]},
    "dia": {"label":"DIA","key":"dia","aliases":["dia"]},
    "lidl": {"label":"Lidl","key":"lidl-es","aliases":["lidl-es"]},
    "carrefour": {"label":"Carrefour","key":None},
}

def norm(s):
    s=(s or "").lower()
    s="".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

CATEGORY_RULES = {
    "huevos": {
        "must_any": {"huevo","huevos"},
        "forbid": {"pasta","fideo","fideos","tallarines","espagueti","espaguetis","macarron","macarrones",
                   "mayonesa","salsa","galleta","galletas","tortilla","chocolate","chocolatina","golosina",
                   "golosinas","caramelo","caramelos","sorpresa","juguete","dulce","dulces","bombon","bombones"},
        "context_any": {"fresco","frescos","campero","camperos","ecologico","ecologicos","clase","calibre",
                        "docena","docenas","gallina","gallinas","xl","l","m","s"}
    },
    "leche": {
        "must_any": {"leche"},
        "forbid": {"chocolate","chocolatada","batido","postre","yogur","yogurt","galleta","helado","caramelo"},
        "context_any": {"entera","semidesnatada","desnatada","sin","lactosa","calcio","fresca","pasteurizada","uverizada"}
    },
    "aceite_oliva": {
        "must_all": {"aceite","oliva"},
        "forbid": {"atun","sardina","conserva","patatas","galletas","cosmetico","masaje"},
        "context_any": {"virgen","extra","suave","intenso","refinado"}
    },
    "cafe": {
        "must_any": {"cafe"},
        "forbid": {"helado","caramelo","galleta","chocolate","licor","ambientador","vela"},
        "context_any": {"molido","grano","natural","mezcla","descafeinado","capsula","capsulas","soluble"}
    },
    "yogur": {
        "must_any": {"yogur","yogurt"},
        "forbid": {"helado","salsa","bebida","batido","caramelo"},
        "context_any": {"natural","griego","fresa","limon","vainilla","azucarado","desnatado","proteina"}
    },
    "agua": {
        "must_any": {"agua"},
        "forbid": {"colonia","perfume","limpiador","oxigenada","micelar","lavavajillas","detergente"},
        "context_any": {"mineral","natural","gas","sin","botella","garrafa"}
    },
    "detergente": {
        "must_any": {"detergente"},
        "forbid": {"lavavajillas","limpiador","jabon","champu","gel","amoniaco","lejia","desengrasante"},
        "context_any": {"lavadora","ropa","lavados","dosis","capsulas","capsula","polvo","liquido"}
    },
    "lavavajillas": {
        "must_any": {"lavavajillas"},
        "forbid": {"detergente","ropa","lavadora"},
        "context_any": {"pastillas","capsulas","capsula","gel","todo","dosis","lavados"}
    },
    "papel_higienico": {
        "must_all": {"papel"},
        "must_prefix_any": {"higien"},
        "forbid": {"cocina","horno","aluminio","regalo","envolver","fotografico","humedo","toallita","toallitas"},
        "context_any": {"rollo","rollos","hojas","doble","triple","capa","capas"}
    },
}

def category(name):
    n=norm(name)
    toks=set(n.split())

    if "huevo" in toks or "huevos" in toks:
        return "huevos"
    if "leche" in toks:
        return "leche"
    if "aceite" in toks and "oliva" in toks:
        return "aceite_oliva"
    if "cafe" in toks:
        return "cafe"
    if "yogur" in toks or "yogurt" in toks:
        return "yogur"
    if "agua" in toks:
        return "agua"
    if "detergente" in toks:
        return "detergente"
    if "lavavajillas" in toks:
        return "lavavajillas"
    if "papel" in toks and any(t.startswith("higien") for t in toks):
        return "papel_higienico"

    # Generic fallback: use first meaningful token
    stop={"de","del","la","el","los","las","con","sin","para","y","al","en","un","una"}
    meaningful=[t for t in n.split() if t not in stop and not t.isdigit()]
    return meaningful[0] if meaningful else "otros"

def token_similarity(a,b):
    stop={"de","del","la","el","los","las","con","sin","para","y","al","en","un","una",
          "ud","uds","unidad","unidades","kg","g","l","ml","pack"}
    ta={t for t in norm(a).split() if t not in stop and not t.isdigit()}
    tb={t for t in norm(b).split() if t not in stop and not t.isdigit()}
    if not ta or not tb:
        return 0.0
    inter=len(ta & tb)
    return inter / max(1,len(ta))


def is_primary_egg_product(product_name):
    n=norm(product_name)
    toks=set(n.split())
    bad={"nido","nidos","pasta","fideo","fideos","tallarines","espagueti","espaguetis",
         "macarron","macarrones","noodles","mayonesa","salsa","galleta","galletas",
         "bizcocho","tarta","tortilla","rebozado","chocolate","chocolatina","golosina",
         "golosinas","caramelo","caramelos","sorpresa","juguete","dulce","dulces",
         "bombon","bombones"}
    if toks & bad or not ({"huevo","huevos"} & toks):
        return False
    return (
        bool(re.search(r"\b(6|10|12|18|24|30)\b",n))
        or any(k in toks for k in {"fresco","frescos","campero","camperos","ecologico",
                                   "ecologicos","docena","docenas","clase","calibre",
                                   "gallina","gallinas","xl","l","m","s"})
    )

def semantic_validate(query, product_name):
    qn=norm(query); pn=norm(product_name)
    qt=set(qn.split()); pt=set(pn.split())
    qcat=category(query); pcat=category(product_name)

    if qcat != pcat:
        return False, "categoría distinta", 0.0
    if qcat=="huevos" and not is_primary_egg_product(product_name):
        return False, "no es un producto principal de huevos", 0.0

    rules=CATEGORY_RULES.get(qcat)
    if rules:
        if rules.get("must_any") and not (pt & rules["must_any"]):
            return False,"falta palabra principal",0.0
        if rules.get("must_all") and not rules["must_all"].issubset(pt):
            return False,"faltan palabras principales",0.0
        if rules.get("must_prefix_any"):
            if not any(any(t.startswith(pref) for pref in rules["must_prefix_any"]) for t in pt):
                return False,"falta descriptor principal",0.0
        if rules.get("forbid") and (pt & rules["forbid"]):
            return False,"producto incompatible con la categoría",0.0

        # If the query itself has descriptive context, reward matching it.
        query_context=(qt & rules.get("context_any",set()))
        product_context=(pt & rules.get("context_any",set()))
        context_score=1.0
        if query_context:
            context_score=len(query_context & product_context)/len(query_context)
            if context_score == 0:
                return False,"variante/contexto distinto",0.0
    else:
        context_score=1.0

    sim=token_similarity(query,product_name)

    # Generic safety threshold. For short queries/category products, keep moderate threshold.
    threshold=0.34
    if len([t for t in qt if not t.isdigit()]) >= 3:
        threshold=0.45

    # Known structured categories can rely a little more on category rules.
    if rules:
        threshold=min(threshold,0.30)

    score=0.65*sim + 0.35*context_score
    if score < threshold:
        return False,"similitud semántica insuficiente",score

    return True,"equivalente",score

def _pack(mult,qty,unit,is_pack):
    if unit=="kg":
        return {"kind":"weight","base_amount":mult*qty*1000,"pack_count":mult,"is_pack":is_pack or mult>1,"unit":"kg"}
    if unit=="g":
        return {"kind":"weight","base_amount":mult*qty,"pack_count":mult,"is_pack":is_pack or mult>1,"unit":"g"}
    if unit=="l":
        return {"kind":"volume","base_amount":mult*qty*1000,"pack_count":mult,"is_pack":is_pack or mult>1,"unit":"l"}
    if unit=="ml":
        return {"kind":"volume","base_amount":mult*qty,"pack_count":mult,"is_pack":is_pack or mult>1,"unit":"ml"}
    return {"kind":"unit","base_amount":mult*qty,"pack_count":mult,"is_pack":is_pack or mult>1,"unit":"ud"}

def parse_pack(name):
    n=norm(name)
    m=re.search(r'(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml|ud|uds|unidad|unidades)\b', n)
    if m:
        return _pack(float(m.group(1).replace(",",".")),float(m.group(2).replace(",",".")),m.group(3),True)

    m=re.search(r'(?:pack\s*)?(\d+)\s*(?:botellas?|briks?|unidades?|uds?)\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml)\b', n)
    if m:
        return _pack(float(m.group(1)),float(m.group(2).replace(",",".")),m.group(3),True)

    m_pack=re.search(r'\bpack\s*(?:de\s*)?(\d+)\b',n)
    explicit_pack_count=int(m_pack.group(1)) if m_pack else None

    m=re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|g|l|ml|ud|uds|unidad|unidades)\b', n)
    if m:
        p=_pack(1,float(m.group(1).replace(",",".")),m.group(2),False)
        if explicit_pack_count and explicit_pack_count>1:
            p["is_pack"]=True
            p["pack_count"]=explicit_pack_count
        return p

    if any(k in n for k in ["pack","lote","multipack"]):
        return {"kind":None,"base_amount":None,"pack_count":None,"is_pack":True,"unit":None}
    return {"kind":None,"base_amount":None,"pack_count":1,"is_pack":False,"unit":None}

def parse_functional_unit(name):
    n=norm(name)
    cat=category(name)

    # Detergent / dishwasher: washes or doses
    if cat in ("detergente","lavavajillas"):
        pats=[
            r'(\d+)\s*(?:lavados?|dosis|capsulas?|pastillas?|usos?)\b',
            r'para\s*(\d+)\s*(?:lavados?|usos?)\b',
            r'(\d+)\s*(?:capsulas?|pastillas?)\b'
        ]
        for pat in pats:
            m=re.search(pat,n)
            if m:
                return {"kind":"wash","amount":float(m.group(1)),"unit_label":"€/lavado"}

    # Toilet paper: sheets preferred, otherwise rolls
    if cat=="papel_higienico":
        # 12 rollos x 200 hojas / 12 x 200 hojas
        m=re.search(r'(\d+)\s*(?:rollos?)?\s*x\s*(\d+)\s*(?:hojas?)\b',n)
        if m:
            return {"kind":"sheet","amount":float(m.group(1))*float(m.group(2)),"unit_label":"€/100 hojas","per":100}
        # "12 rollos", "pack 12 rollos", "12 uds"
        m=re.search(r'(?:pack\s*)?(\d+)\s*(?:rollos?|rollo|uds?|unidades?)\b',n)
        if m:
            return {"kind":"roll","amount":float(m.group(1)),"unit_label":"€/rollo"}
        # sheets only
        m=re.search(r'(\d+)\s*(?:hojas?)\b',n)
        if m:
            return {"kind":"sheet","amount":float(m.group(1)),"unit_label":"€/100 hojas","per":100}

    # Eggs: per egg
    if cat=="huevos":
        m=re.search(r'(\d+)\s*(?:huevos?|ud|uds|unidades?)\b',n)
        if m:
            return {"kind":"egg","amount":float(m.group(1)),"unit_label":"€/huevo"}

    # Yogurts: total weight if readable
    if cat=="yogur":
        p=parse_pack(name)
        if p.get("kind")=="weight" and p.get("base_amount"):
            return {"kind":"weight","amount":float(p["base_amount"])/1000,"unit_label":"€/kg"}

    # Generic physical dimensions
    p=parse_pack(name)
    if p.get("kind")=="weight" and p.get("base_amount"):
        return {"kind":"weight","amount":float(p["base_amount"])/1000,"unit_label":"€/kg"}
    if p.get("kind")=="volume" and p.get("base_amount"):
        return {"kind":"volume","amount":float(p["base_amount"])/1000,"unit_label":"€/l"}
    if p.get("kind")=="unit" and p.get("base_amount"):
        return {"kind":"unit","amount":float(p["base_amount"]),"unit_label":"€/ud"}

    return None

def normalized_price(price, f):
    if price is None or not f or not f.get("amount"):
        return None
    amount=float(f["amount"])
    per=float(f.get("per") or 1)
    return float(price)/(amount/per)

def comparable(query,product_name):
    ok,reason,semantic_score=semantic_validate(query,product_name)
    if not ok:
        return False,reason,semantic_score

    qp=parse_pack(query); pp=parse_pack(product_name)

    if not qp.get("is_pack") and pp.get("is_pack"):
        return False,"pack/lote no solicitado",semantic_score

    qf=parse_functional_unit(query); pf=parse_functional_unit(product_name)

    if qf and pf and qf["kind"]!=pf["kind"]:
        return False,"unidad funcional distinta",semantic_score

    if qf and pf and qf["kind"]==pf["kind"] and qf.get("amount") and pf.get("amount"):
        ratio=min(float(qf["amount"]),float(pf["amount"])) / max(float(qf["amount"]),float(pf["amount"]))
        min_ratio=.90 if qf["kind"] in ("egg","roll","wash","sheet") else .80
        if ratio < min_ratio:
            return False,"cantidad funcional distinta",semantic_score

    return True,"equivalente",semantic_score


def normalize_ean(v):
    if v is None:
        return None
    s=re.sub(r"\D","",str(v))
    return s if len(s) in (8,12,13,14) else None

def category_compatible(query, product):
    """Use retailer category when present as a strong filter."""
    real_cat=norm(product.get("category") or "")
    if not real_cat:
        return True, "sin categoría estructurada"

    qcat=category(query)
    mapping={
        "huevos": ["huevo","huevos"],
        "leche": ["leche","lacteo","lacteos"],
        "aceite_oliva": ["aceite","aceites"],
        "cafe": ["cafe","cafes"],
        "yogur": ["yogur","yogurt","lacteo","lacteos"],
        "agua": ["agua","bebidas"],
        "detergente": ["detergente","lavado","ropa","limpieza"],
        "lavavajillas": ["lavavajillas","limpieza"],
        "papel_higienico": ["papel higienico","higiene","papel"],
    }
    expected=mapping.get(qcat)
    if not expected:
        return True, "categoría genérica"

    ok=any(e in real_cat for e in expected)
    return (ok, "categoría real compatible" if ok else "categoría real incompatible")

def rank_candidate(query, requested_ean, p):
    exact_ean = bool(requested_ean and normalize_ean(p.get("ean") or p.get("gtin")) == requested_ean)
    cat_ok, cat_reason = category_compatible(query,p)
    sem_ok, sem_reason, sem_score = semantic_validate(query,p["name"])

    if exact_ean:
        return True, 1000.0, "EAN/GTIN exacto", 1.0, True, cat_ok, "alta"

    if not cat_ok:
        return False, -100.0, cat_reason, sem_score, False, False, "rechazada"

    qcat=category(query)
    qf=parse_functional_unit(query)
    pf=parse_functional_unit(p["name"])

    # High confidence: category + semantic + compatible format/quantity
    if sem_ok:
        qp=parse_pack(query); pp=parse_pack(p["name"])
        if not qp.get("is_pack") and pp.get("is_pack"):
            # For toilet paper and detergent, pack is intrinsic to the product category,
            # so don't reject just because the query lacks the literal word pack.
            if qcat not in ("papel_higienico","detergente","lavavajillas","huevos","yogur"):
                return False,-20.0,"pack/lote no solicitado",sem_score,False,True,"rechazada"

        if qf and pf and qf["kind"]!=pf["kind"]:
            # Paper may express rolls vs sheets. Treat as probable, not rejected.
            if qcat=="papel_higienico":
                score=70*sem_score+20
                return True,score,"categoría correcta; unidad funcional distinta",sem_score,False,True,"probable"
            return False,-20.0,"unidad funcional distinta",sem_score,False,True,"rechazada"

        qty_score=1.0
        if qf and pf and qf.get("amount") and pf.get("amount") and qf["kind"]==pf["kind"]:
            ratio=min(float(qf["amount"]),float(pf["amount"])) / max(float(qf["amount"]),float(pf["amount"]))
            min_ratio=.90 if qf["kind"] in ("egg","roll","wash","sheet") else .80
            if ratio < min_ratio:
                # Detergent and toilet paper often differ by pack size; keep as probable
                if qcat in ("detergente","lavavajillas","papel_higienico"):
                    score=72*sem_score + 18*ratio + 15
                    return True,score,"categoría correcta; cantidad distinta",sem_score,False,True,"probable"
                return False,-20.0,"cantidad funcional distinta",sem_score,False,True,"rechazada"
            qty_score=ratio

        score = 100*sem_score + 25*qty_score + 20
        return True,score,"categoría + semántica compatibles",sem_score,False,True,"alta"

    # Probable fallback for a few structured categories:
    # strong real-category match plus enough token overlap even if semantic rules are strict.
    fallback_categories={"detergente","lavavajillas","papel_higienico","yogur","leche","cafe"}
    if qcat in fallback_categories:
        sim=token_similarity(query,p["name"])
        if qf:
            if not pf:
                return False,-40.0,"falta unidad funcional del producto",sim,False,True,"rechazada"
            if qf["kind"] != pf["kind"]:
                if not (qcat=="papel_higienico" and {qf["kind"],pf["kind"]} <= {"roll","sheet"}):
                    return False,-40.0,"unidad funcional incompatible",sim,False,True,"rechazada"
        if sim >= 0.28:
            score=55*sim+20
            return True,score,"categoría correcta; coincidencia probable",sim,False,True,"probable"

    return False,-50.0,sem_reason,sem_score,False,True,"rechazada"


def units_needed_for_equivalence(query, product_name):
    """Return how many packs/units of candidate are needed to meet requested functional amount."""
    qf=parse_functional_unit(query)
    pf=parse_functional_unit(product_name)
    if not qf or not pf:
        return None
    if qf["kind"] != pf["kind"]:
        return None
    qa=float(qf.get("amount") or 0)
    pa=float(pf.get("amount") or 0)
    if qa <= 0 or pa <= 0:
        return None
    import math
    units=1 if pa >= qa * 0.90 else max(1, math.ceil(qa/pa))
    covered=units*pa
    ratio=covered/qa if qa else None
    return {
        "units_needed": units,
        "requested_amount": qa,
        "candidate_amount": pa,
        "covered_amount": covered,
        "coverage_ratio": ratio,
        "kind": qf["kind"],
        "unit_label": qf.get("unit_label")
    }


def quality_signature(name):
    """
    Returns (category, quality_tier, score).
    Brand is intentionally ignored.
    """
    n=norm(name)
    cat=category(name)

    if cat=="aceite_oliva":
        if "virgen extra" in n or "aove" in n:
            return (cat,"AOVE",3)
        if "virgen" in n:
            return (cat,"virgen",2)
        return (cat,"oliva",1)

    if cat=="huevos":
        if "ecologico" in n or "ecologicos" in n:
            return (cat,"ecologico",3)
        if "campero" in n or "camperos" in n:
            return (cat,"campero",2)
        return (cat,"convencional",1)

    if cat=="cafe":
        if "100 arabica" in n or "arabica" in n:
            return (cat,"arabica",3)
        return (cat,"general",1)

    if cat=="leche":
        # preserve fat/functional type
        if "sin lactosa" in n:
            return (cat,"sin_lactosa",2)
        if "desnatada" in n:
            return (cat,"desnatada",1)
        if "semidesnatada" in n:
            return (cat,"semidesnatada",1)
        if "entera" in n:
            return (cat,"entera",1)

    if cat=="yogur":
        if "griego" in n:
            return (cat,"griego",2)
        if "natural" in n:
            return (cat,"natural",1)

    return (cat,"general",1)

def same_quality(query, product_name):
    qcat, qtier, qscore = quality_signature(query)
    pcat, ptier, pscore = quality_signature(product_name)
    if qcat != pcat:
        return False, "categoría distinta"

    # User intent: cheapest basket at same quality, irrespective of brand.
    # For defined quality-sensitive categories, require same tier or better.
    if qcat in ("aceite_oliva","huevos","cafe","leche","yogur"):
        if pscore < qscore:
            return False, f"calidad inferior ({ptier})"
        # Avoid swapping to a materially different style at same numeric score.
        if qcat in ("leche","yogur") and qtier!="general" and ptier!=qtier:
            return False, f"variante distinta ({ptier})"
    return True, ptier

def offer_info(p):
    current=p.get("promo_price")
    regular=p.get("original_price") or p.get("price")
    if current is None:
        current=p.get("price")
    is_offer=bool(regular is not None and current is not None and current < regular)
    saving=(regular-current) if is_offer else 0.0
    return {
        "is_offer": is_offer,
        "effective_price": float(current) if current is not None else None,
        "regular_price": float(regular) if regular is not None else None,
        "saving_eur": round(float(saving),2) if saving else 0.0,
        "saving_pct": round(float(saving)/float(regular)*100,1) if is_offer and regular else 0.0,
        "text": p.get("promotion_text")
    }


def _effective_candidate_cost(candidate, requested_qty=1):
    offer=(candidate.get("offer") or {})
    base=offer.get("effective_price")
    if base is None:
        base=candidate.get("price") or 0.0
    eq=candidate.get("equivalent_units") or {}
    units=max(1,int(eq.get("units_needed") or 1))
    return float(base)*units*max(1,int(requested_qty or 1)), units

def _same_quality_mode_ok(query, product_name, quality_mode="exact"):
    """
    exact: same quality tier/variant where defined.
    minimum: allow same or better quality, never worse.
    """
    qcat, qtier, qscore = quality_signature(query)
    pcat, ptier, pscore = quality_signature(product_name)
    if qcat != pcat:
        return False

    if quality_mode=="minimum":
        return pscore >= qscore

    # exact mode
    if qcat in ("aceite_oliva","huevos","cafe","leche","yogur"):
        if qscore != pscore:
            return False
        if qcat in ("leche","yogur") and qtier!="general" and ptier!=qtier:
            return False
    return True

def optimize_basket_plan(store_rows, items, options=None):
    """
    store_rows: results returned by compare(), with per-line chosen candidates.
    Produces:
      - best_single_store
      - best_split_basket
      - recommendation after switching/transport thresholds
    """
    options=options or {}
    split_allowed=bool(options.get("split_allowed", True))
    min_switch_saving=float(options.get("min_switch_saving_eur", 3.0))
    travel_costs=options.get("travel_costs_eur") or {}
    delivery_costs=options.get("delivery_costs_eur") or {}
    max_stores=max(1,int(options.get("max_stores", 2)))
    mode=options.get("purchase_mode","physical")

    normalized=[]
    for r in store_rows:
        extra=float(delivery_costs.get(r["store"],0.0) if mode=="online" else travel_costs.get(r["store"],0.0))
        rr=dict(r)
        rr["extra_cost"]=round(extra,2)
        rr["real_total"]=round(float(r.get("total") or 0)+extra,2)
        normalized.append(rr)

    fully_resolved=[r for r in normalized if int(r.get("unresolved") or 0)==0]
    single_pool=fully_resolved or normalized
    single_pool=sorted(single_pool,key=lambda r:(int(r.get("unresolved") or 0),r["real_total"]))
    best_single=single_pool[0] if single_pool else None

    if not split_allowed or not normalized:
        return {
            "best_single_store":best_single,
            "best_split_basket":None,
            "recommended_plan":"single",
            "reason":"cesta dividida desactivada",
            "saving_vs_single":0.0
        }

    # Build cheapest valid line across stores.
    split_lines=[]
    stores_used=set()
    raw_products_total=0.0

    for idx,item in enumerate(items):
        q=(item.get("query") or "").strip()
        qty=max(1,int(float(item.get("qty",1) or 1)))
        candidates=[]
        for r in normalized:
            for line in r.get("items") or []:
                if (line.get("query") or "").strip()!=q:
                    continue
                m=line.get("matched")
                if not m:
                    continue
                # product already passed semantic/quality validation at search stage
                cost=float(line.get("line_total") or 0)
                candidates.append({
                    "store":r["store"],
                    "label":r["label"],
                    "query":q,
                    "matched":m,
                    "line_total":cost,
                    "units_needed":line.get("units_needed",1)
                })
        if not candidates:
            split_lines.append({"query":q,"matched":None,"line_total":0.0})
            continue
        candidates.sort(key=lambda x:x["line_total"])
        best=candidates[0]
        split_lines.append(best)
        raw_products_total += best["line_total"]
        stores_used.add(best["store"])

    # If too many stores, greedily consolidate into max_stores using total line savings.
    if len(stores_used) > max_stores:
        store_value={}
        for line in split_lines:
            s=line.get("store")
            if not s: continue
            store_value[s]=store_value.get(s,0.0)+float(line.get("line_total") or 0)
        keep=set(sorted(store_value,key=store_value.get,reverse=True)[:max_stores])

        new_lines=[]
        for line in split_lines:
            if not line.get("store") or line["store"] in keep:
                new_lines.append(line); continue
            q=line["query"]
            alternatives=[]
            for r in normalized:
                if r["store"] not in keep: continue
                for l2 in r.get("items") or []:
                    if (l2.get("query") or "").strip()==q and l2.get("matched"):
                        alternatives.append({
                            "store":r["store"],"label":r["label"],"query":q,
                            "matched":l2["matched"],"line_total":float(l2.get("line_total") or 0),
                            "units_needed":l2.get("units_needed",1)
                        })
            new_lines.append(sorted(alternatives,key=lambda x:x["line_total"])[0] if alternatives else line)
        split_lines=new_lines
        stores_used={l["store"] for l in split_lines if l.get("store")}
        raw_products_total=sum(float(l.get("line_total") or 0) for l in split_lines)

    extras=0.0
    for s in stores_used:
        extras += float(delivery_costs.get(s,0.0) if mode=="online" else travel_costs.get(s,0.0))

    unresolved=sum(1 for l in split_lines if not l.get("matched"))
    split_total=round(raw_products_total+extras,2)
    split_plan={
        "items":split_lines,
        "stores_used":sorted(stores_used),
        "product_total":round(raw_products_total,2),
        "extra_cost":round(extras,2),
        "real_total":split_total,
        "unresolved":unresolved
    }

    saving=round((best_single["real_total"]-split_total),2) if best_single else 0.0

    # Switching threshold: don't recommend extra stores unless saving is meaningful.
    if unresolved>0:
        recommended="single"
        reason="la cesta dividida deja productos sin resolver"
    elif len(stores_used)<=1:
        recommended="single"
        reason="la cesta óptima ya se concentra en una sola tienda"
    elif saving >= min_switch_saving:
        recommended="split"
        reason=f"ahorro adicional de {saving:.2f} € supera el umbral de {min_switch_saving:.2f} €"
    else:
        recommended="single"
        reason=f"el ahorro adicional de {saving:.2f} € no compensa cambiar de tienda"

    return {
        "best_single_store":best_single,
        "best_split_basket":split_plan,
        "recommended_plan":recommended,
        "reason":reason,
        "saving_vs_single":saving
    }


def expanded_queries(query):
    """
    Category-aware query expansion. This is intentionally conservative:
    it broadens vocabulary but keeps the same product category.
    """
    q=norm(query)
    cat=category(query)
    out=[query]

    if cat=="detergente":
        out += ["detergente lavadora", "detergente ropa", "detergente liquido lavadora", "detergente"]
    elif cat=="papel_higienico":
        out += ["papel higienico", "papel wc", "rollos papel higienico"]
    elif cat=="huevos":
        out += ["huevos frescos", "huevos", "huevos 12"]
    elif cat=="yogur":
        out += ["yogur natural", "yogur"]
    elif cat=="leche":
        out += ["leche entera", "leche"]
    elif cat=="aceite_oliva":
        if "virgen extra" in q or "aove" in q:
            out += ["aceite oliva virgen extra", "aove"]
        else:
            out += ["aceite oliva"]

    seen=set()
    clean=[]
    for x in out:
        k=norm(x)
        if k and k not in seen:
            clean.append(x)
            seen.add(k)
    return clean

def _is_hard_false_positive(query, product_name):
    qcat=category(query)
    n=norm(product_name)
    toks=set(n.split())

    if qcat=="huevos":
        bad={"nido","nidos","pasta","fideo","fideos","tallarines","espagueti","espaguetis",
             "macarron","macarrones","mayonesa","salsa","galleta","galletas","chocolate",
             "chocolatina","golosina","golosinas","caramelo","caramelos","sorpresa","juguete"}
        if toks & bad:
            return True
    if qcat=="detergente":
        if toks & {"amoniaco","lejia","desengrasante","lavavajillas"}:
            return True
    if qcat=="papel_higienico":
        if toks & {"humedo","humedos","toallita","toallitas","cocina"}:
            return True
    return False

def _functional_match_relaxed(query, product_name):
    qf=parse_functional_unit(query)
    pf=parse_functional_unit(product_name)
    if not qf:
        return True, 1.0, "sin unidad funcional solicitada"
    if not pf:
        # For detergents/paper, allow a candidate without readable count only as PROBABLE,
        # provided category/semantics are strong. This fixes catalogs that omit count in title.
        if category(query) in ("detergente","papel_higienico"):
            return True, 0.55, "cantidad no visible en nombre"
        return False, 0.0, "unidad funcional no legible"
    if qf["kind"] != pf["kind"]:
        if category(query)=="papel_higienico" and {qf["kind"],pf["kind"]} <= {"roll","sheet"}:
            return True, 0.65, "papel estructurado en otra unidad"
        return False, 0.0, "unidad funcional distinta"

    qa=float(qf.get("amount") or 0)
    pa=float(pf.get("amount") or 0)
    if qa<=0 or pa<=0:
        return False,0.0,"cantidad funcional inválida"
    ratio=min(qa,pa)/max(qa,pa)

    min_ratio={
        "wash":0.70,   # 40 can compare with roughly 28-57, normalized €/wash
        "roll":0.50,   # 12 can compare with 6/8/9/16/18 using equivalent units
        "sheet":0.50,
        "egg":0.65,
        "weight":0.80,
        "volume":0.80,
        "unit":0.70
    }.get(qf["kind"],0.70)

    return ratio>=min_ratio, ratio, "cantidad funcional compatible" if ratio>=min_ratio else "cantidad funcional demasiado distinta"

class GroceryCLI:
    _resolved_keys={}

    def _available_store_keys(self):
        keys=set()
        try:
            p=subprocess.run(["grocery","stores","--json"],text=True,capture_output=True,timeout=30)
            if p.returncode==0 and p.stdout.strip():
                try:
                    obj=json.loads(p.stdout)
                    def walk(x):
                        if isinstance(x,dict):
                            for k,v in x.items():
                                if k in ("key","id","store","name") and isinstance(v,str):
                                    keys.add(v.strip().lower())
                                walk(v)
                        elif isinstance(x,list):
                            for v in x: walk(v)
                    walk(obj)
                except Exception:
                    pass
        except Exception:
            pass
        if not keys:
            try:
                p=subprocess.run(["grocery","stores"],text=True,capture_output=True,timeout=30)
                if p.returncode==0:
                    for token in re.findall(r"[a-z0-9_-]+",(p.stdout or "").lower()):
                        keys.add(token)
            except Exception:
                pass
        return keys

    def _store_key(self,store):
        if store in self._resolved_keys:
            return self._resolved_keys[store]
        cfg=STORES.get(store) or {}
        aliases=cfg.get("aliases") or [cfg.get("key")]
        available=self._available_store_keys()
        for a in [x for x in aliases if x]:
            if not available or a.lower() in available:
                self._resolved_keys[store]=a
                return a
        self._resolved_keys[store]=cfg.get("key")
        return cfg.get("key")

    def available(self):
        return shutil.which("grocery") is not None

    def status(self):
        return {"available":self.available(),"mode":"REAL_BETA" if self.available() else "UNAVAILABLE","stores":STORES}

    def _run(self,args,stdin=None,timeout=120):
        if not self.available():
            raise ProviderError("grocery-cli no está disponible en PATH.")
        p=subprocess.run(["grocery"]+args,input=stdin,text=True,capture_output=True,timeout=timeout)
        if p.returncode!=0:
            raise ProviderError((p.stderr or p.stdout or "Error grocery-cli").strip())
        out=(p.stdout or "").strip()
        if not out:return None
        try:return json.loads(out)
        except:raise ProviderError("grocery-cli devolvió una respuesta no JSON.")

    @staticmethod
    def _price(v):
        if isinstance(v,(int,float)):return float(v)
        if isinstance(v,str):
            try:return float(v.replace("€","").replace(",",".").strip())
            except:return None
        return None

    @classmethod
    def _collect_products(cls,obj):
        found=[]
        def walk(x):
            if isinstance(x,dict):
                name=x.get("name") or x.get("product_name") or x.get("title") or x.get("display_name") or x.get("label") or x.get("productName")
                price=None
                for k in ("price","unit_price","price_eur","bulk_price","current_price","sale_price","final_price","amount"):
                    if k in x:
                        price=cls._price(x.get(k))
                        if price is not None:break
                if price is None and isinstance(x.get("price_instructions"),dict):
                    pi=x["price_instructions"]
                    price=cls._price(pi.get("unit_price") or pi.get("bulk_price"))
                if name and price is not None:
                    pid=x.get("id") or x.get("product_id") or x.get("pk") or x.get("sku") or x.get("code") or x.get("productId") or x.get("sku")
                    found.append({
                        "id":str(pid) if pid is not None else None,
                        "name":str(name),
                        "price":price,
                        "ean":x.get("ean") or x.get("gtin") or x.get("barcode"),
                        "gtin":x.get("gtin") or x.get("ean") or x.get("barcode"),
                        "brand":x.get("brand"),
                        "promo_price": (
                            cls._price(x.get("promo_price")) or
                            cls._price(x.get("offer_price")) or
                            cls._price(x.get("sale_price")) or
                            cls._price(x.get("discount_price"))
                        ),
                        "original_price": (
                            cls._price(x.get("original_price")) or
                            cls._price(x.get("regular_price")) or
                            cls._price(x.get("list_price")) or
                            cls._price(x.get("was_price"))
                        ),
                        "promotion_text": (
                            x.get("promotion") or x.get("promo_text") or
                            x.get("offer_text") or x.get("discount_label")
                        ),
                        "category": (
                            x.get("category_name") or x.get("category") or
                            x.get("subcategory_name") or x.get("aisle_name") or
                            x.get("section_name")
                        ),
                        "category_id": (
                            x.get("category_id") or x.get("subcategory_id") or
                            x.get("aisle_id") or x.get("section_id")
                        ),
                    })
                for v in x.values():walk(v)
            elif isinstance(x,list):
                for v in x:walk(v)
        walk(obj)
        uniq={}
        for p in found:uniq[(p["name"],p["price"])]=p
        return list(uniq.values())

    def diagnose_store(self,store):
        key="lidl-es" if store=="lidl" else (STORES.get(store) or {}).get("key")
        result={"store":store,"key":key}
        for mode in ("search","batch"):
            try:
                if mode=="search":
                    p=subprocess.run(
                        ["grocery","--store",key,"search","leche","--limit","5","--json"],
                        text=True,capture_output=True,timeout=60
                    )
                else:
                    p=subprocess.run(
                        ["grocery","--store",key,"batch","-f","-","--candidates","5","--json"],
                        input="leche\n",text=True,capture_output=True,timeout=60
                    )
                result[mode+"_ok"]=p.returncode==0
                result[mode+"_stdout"]=(p.stdout or "")[:2000]
                result[mode+"_stderr"]=(p.stderr or "")[:2000]
            except Exception as e:
                result[mode+"_ok"]=False
                result[mode+"_error"]=str(e)
        result["ok"]=bool(result.get("search_ok") or result.get("batch_ok"))
        return result


    def _raw_search(self,store,query,limit=40):
        cfg=STORES.get(store)
        if not cfg or not cfg.get("key"):
            return []
        key="lidl-es" if store=="lidl" else cfg.get("key")
        products=[]
        # Standard search
        try:
            data=self._run(["--store",key,"search",query,"--limit",str(limit),"--json"])
            products.extend(self._collect_products(data))
        except Exception:
            pass
        # Batch candidate fallback
        try:
            data2=self._run(
                ["--store",key,"batch","-f","-","--candidates","25","--json"],
                stdin=query.strip()+"\n",
                timeout=120
            )
            products.extend(self._collect_products(data2))
        except Exception:
            pass

        uniq={}
        for p in products:
            uniq[(p.get("id"),p.get("name"),p.get("price"))]=p
        return list(uniq.values())

    def _multiquery_products(self,store,query):
        products=[]
        for q2 in expanded_queries(query):
            products.extend(self._raw_search(store,q2,40))
        uniq={}
        for p in products:
            uniq[(p.get("id"),p.get("name"),p.get("price"))]=p
        return list(uniq.values())

    def search(self,store,query,limit=8,ean=None):
        cfg=STORES.get(store)
        if not cfg or not cfg["key"]:
            raise ProviderError(f"{store}: conector real no disponible.")

        requested_ean=normalize_ean(ean)
        search_term=query
        products=self._multiquery_products(store,query)

        valid=[]
        rejected=[]
        for p in products:
            ok,rank,reason,semantic_score,exact_ean,cat_ok,confidence=rank_candidate(query,requested_ean,p)
            p["semantic_score"]=round(float(semantic_score),3)
            p["exact_ean_match"]=exact_ean
            p["category_match"]=cat_ok
            p["match_reason"]=reason
            p["confidence"]=confidence
            if not ok:
                rejected.append({"name":p["name"],"reason":reason,"category":p.get("category")})
                continue

            quality_ok,quality_tier=same_quality(query,p["name"])
            if not quality_ok:
                rejected.append({"name":p["name"],"reason":quality_tier,"category":p.get("category")})
                continue

            p["quality_tier"]=quality_tier
            p["offer"]=offer_info(p)
            effective_price=p["offer"]["effective_price"] if p["offer"]["effective_price"] is not None else p["price"]

            fu=parse_functional_unit(p["name"])
            p["functional_unit"]=fu
            p["normalized_price"]=normalized_price(effective_price,fu)
            p["rank_score"]=round(rank,3)
            p["selection_policy"]="precio_mas_bajo_misma_calidad"
            p["brand_ignored_by_default"]=True

            eq=units_needed_for_equivalence(query,p["name"])
            p["equivalent_units"]=eq
            if eq:
                p["equivalent_cost"]=round(float((p.get("offer") or {}).get("effective_price") or p["price"])*int(eq["units_needed"]),2)
            else:
                p["equivalent_cost"]=None

            valid.append(p)

        # Brand is ignored. Among valid same-quality candidates, cheapest comparable cost wins.
        # CestaSmart core rule:
        # 1) exact EAN only when explicitly requested,
        # 2) otherwise cheapest valid same-quality comparable product wins.

        # RELAXED_CATEGORY_FALLBACK
        # If strict matching leaves nothing, use category-safe candidates from expanded queries.
        # Hard false positives remain excluded.
        if not valid:
            for p in products:
                pname=p.get("name") or ""
                if not pname or _is_hard_false_positive(query,pname):
                    continue
                if category(query) != category(pname):
                    continue

                sem=token_similarity(query,pname)
                # Broad query expansions can lower token overlap. Require enough relevance.
                if sem < 0.20:
                    continue

                fm_ok,fm_ratio,fm_reason=_functional_match_relaxed(query,pname)
                if not fm_ok:
                    continue

                # Respect same-quality logic when available.
                try:
                    quality_ok,quality_tier=same_quality(query,pname)
                    if not quality_ok:
                        continue
                    p["quality_tier"]=quality_tier
                except Exception:
                    pass

                fu=parse_functional_unit(pname)
                p["functional_unit"]=fu
                try:
                    p["offer"]=offer_info(p)
                    effective=(p["offer"].get("effective_price") or p.get("price"))
                except Exception:
                    effective=p.get("price")
                p["normalized_price"]=normalized_price(effective,fu)
                p["semantic_score"]=round(float(sem),3)
                p["confidence"]="probable" if fm_ratio < 0.85 else "alta"
                p["match_reason"]="equivalencia ampliada por categoría"
                p["exact_ean_match"]=False
                p["category_match"]=True
                p["rank_score"]=round(60*float(sem)+30*float(fm_ratio),3)
                p["selection_policy"]="precio_mas_bajo_misma_calidad"
                p["brand_ignored_by_default"]=True

                eq=units_needed_for_equivalence(query,pname)
                p["equivalent_units"]=eq
                if eq and effective is not None:
                    p["equivalent_cost"]=round(float(effective)*int(eq.get("units_needed") or 1),2)
                else:
                    p["equivalent_cost"]=effective
                valid.append(p)

        valid.sort(key=lambda p:(
            0 if p.get("exact_ean_match",False) else 1,
            p["normalized_price"] is None,
            p["normalized_price"] if p["normalized_price"] is not None else ((p.get("offer") or {}).get("effective_price") or p["price"]),
            0 if p.get("confidence")=="alta" else 1,
            -p.get("rank_score",0)
        ))

        return {
            "store":store,
            "label":cfg["label"],
            "query":query,
            "requested_ean":requested_ean,
            "products":valid[:limit],
            "rejected":rejected[:15],
            "data_mode":"REAL_BETA",
            "matching_priority":["EAN/GTIN exacto","categoría real","semántica","formato/cantidad"]
        }

    def compare(self,stores,items):
        rows=[]
        for store in stores:
            cfg=STORES.get(store)
            if not cfg or not cfg["key"]:
                continue
            total=0.0
            detail=[]
            unresolved=0
            for item in items:
                q=(item.get("query") or "").strip()
                qty=max(1,int(float(item.get("qty",1) or 1)))
                try:
                    s=self.search(store,q,limit=8,ean=item.get("ean") or item.get("gtin"))
                except ProviderError:
                    unresolved+=qty
                    continue
                candidates=s["products"]
                if not candidates:
                    unresolved+=qty
                    detail.append({"query":q,"matched":None})
                    continue
                high=[c for c in candidates if c.get("confidence")=="alta" or c.get("exact_ean_match")]
                probable=[c for c in candidates if c.get("confidence")=="probable"]
                best=(high or probable or candidates)[0]

                eq=best.get("equivalent_units")
                units_needed=1
                if eq and eq.get("units_needed"):
                    units_needed=max(1,int(eq["units_needed"]))

                base_price=((best.get("offer") or {}).get("effective_price")) or best["price"]
                line=base_price*units_needed*qty
                total+=line
                detail.append({
                    "query":q,
                    "qty":qty,
                    "matched":best,
                    "units_needed":units_needed,
                    "line_total":round(line,2),
                    "comparison_mode":"equivalent_units" if units_needed>1 else "direct"
                })
            rows.append({
                "store":store,
                "label":cfg["label"],
                "total":round(total,2),
                "unresolved":unresolved,
                "items":detail
            })
        rows.sort(key=lambda r:(r["unresolved"]>0,r["unresolved"],r["total"]))
        return {
            "results":rows,
            "best":rows[0] if rows else None,
            "data_mode":"REAL_BETA",
            "selection_policy":"precio_mas_bajo_misma_calidad",
            "brand_policy":"ignorar_marca_salvo_restriccion_explicita"
        }

    def optimize(self,stores,items,options=None):
        comparison=self.compare(stores,items)
        plan=optimize_basket_plan(comparison.get("results") or [],items,options or {})
        return {
            "comparison":comparison,
            "optimizer":plan,
            "selection_policy":"precio_primero_misma_calidad",
            "variables":{
                "quality_mode":(options or {}).get("quality_mode","exact"),
                "split_allowed":bool((options or {}).get("split_allowed",True)),
                "max_stores":int((options or {}).get("max_stores",2)),
                "min_switch_saving_eur":float((options or {}).get("min_switch_saving_eur",3.0)),
                "purchase_mode":(options or {}).get("purchase_mode","physical")
            }
        }

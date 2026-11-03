#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harvest_multi.py — Amplia el funnel mas alla de Greenhouse: Lever + Ashby.

APIs publicas (sin auth), verificadas en vivo 2026-11-03:
  Lever: GET https://api.lever.co/v0/postings/{org}?mode=json
  Ashby: GET https://api.ashbyhq.com/posting-api/job-board/{org}

Salida: gh/data/multi_queue.json (mismo schema de plan que queue.json, con
'ats' y apply_url directo). El gh_commander v4 los procesa con generic_fill.

Uso:
  python3 scripts/gh/harvest_multi.py            # cosechar todas las orgs
  python3 scripts/gh/harvest_multi.py --cats design,ai
  python3 scripts/gh/harvest_multi.py --orgs linear,leverdemo
"""
import json, os, re, subprocess, time, argparse

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'data', 'multi_queue.json')
SEEN = os.path.join(BASE, 'data', 'multi_seen.json')

# Organizaciones a vigilar (job board slug = el de jobs.lever.co / jobs.ashbyhq.com).
# Agregar las que convenga; las muertas (404) se saltan solas y se cachean.
LEVER_ORGS = [
    'leverdemo', 'soundcloud', 'quizlet', 'postman', 'stay22', 'plaidnetwork',
    'asknfully', 'mixbook', 'affinity', 'brickstreet', 'petalcard', 'sourcegraph-lever',
]
ASHBY_ORGS = [
    'linear', 'posthog', 'watershed', 'deel', 'canny', 'browserbase', 'langchain',
    'supabase', 'e2b', 'sardine', 'neon', 'railway', 'spiral', 'crewai', 'tryretool',
]

# filtros de categoria (mismas familias que el harvest Greenhouse)
INCLUDE = [
    (r'graphic|visual|motion|brand|design|illustrat|layout|creative|video|editor', 'design'),
    (r'web (design|producer|content)|wordpress|shopify|front.?end(?! engineer)|webmaster|site', 'web'),
    (r'ai|artificial|machine learning|chatbot|agent|automation|llm|prompt', 'ai'),
    (r'crm|email marketing|klaviyo|braze|hubspot|mailchimp|lifecycle|retention|newsletter', 'crm'),
]
EXCLUDE = re.compile(
    r'engineer|developer|backend|front.?end engineer|devops|data (scientist|engineer)|'
    r'research (scientist|engineer)|applied ai|'
    r'staff|principal (engineer|architect)|sre|mobile|android|ios|quant|security engineer', re.I)
EXCLUDE_SENIOR = re.compile(r'director|vp |head of|chief|principal|staff|lead engineer|senior manager', re.I)


def fetch(url):
    try:
        r = subprocess.run(['curl', '-s', '--max-time', '25', url],
                           capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout or '""')
    except Exception:
        return None


def categorize(title):
    t = title.lower()
    if EXCLUDE.search(t) or EXCLUDE_SENIOR.search(t):
        return None
    for pat, cat in INCLUDE:
        if re.search(pat, t):
            return cat
    return None


def score(cat, location, workplace):
    s = 100.0
    loc = (location or '').lower()
    if workplace and 'remote' in workplace.lower():
        s += 40
    if 'remote' in loc or 'anywhere' in loc or 'worldwide' in loc:
        s += 30
    if any(x in loc for x in ('ecuador', 'latin', 'south america', 'latam')):
        s += 50
    if any(x in loc for x in ('united states', 'usa', 'new york', 'san francisco', 'california')):
        s -= 10
    return s


def harvest_lever(org, seen):
    d = fetch(f'https://api.lever.co/v0/postings/{org}?mode=json')
    if not isinstance(d, list):
        return []
    out = []
    for j in d:
        title = j.get('text') or ''
        cat = categorize(title)
        if not cat:
            continue
        loc = (j.get('categories') or {}).get('location') or ''
        wp = j.get('workplaceType') or ''
        key = f"lever/{org}/{j.get('id')}"
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'ats': 'lever', 'key': key, 'slug': org, 'id': j.get('id'),
            'company': org, 'title': title, 'category': cat,
            'location': loc, 'score': round(score(cat, loc, wp), 1),
            'apply_url': (j.get('applyUrl') or (j.get('hostedUrl') or '') + '/apply'),
            'harvested': time.strftime('%Y-%m-%d'),
        })
    return out


def harvest_ashby(org, seen):
    d = fetch(f'https://api.ashbyhq.com/posting-api/job-board/{org}')
    if not isinstance(d, dict) or not d.get('jobs'):
        return []
    out = []
    for j in d['jobs']:
        if not j.get('isListed', True):
            continue
        title = j.get('title') or ''
        cat = categorize(title)
        if not cat:
            continue
        loc = j.get('location') or ''
        wp = j.get('workplaceType') or ''
        key = f"ashby/{org}/{j.get('id')}"
        if key in seen:
            continue
        seen.add(key)
        out.append({
            'ats': 'ashby', 'key': key, 'slug': org, 'id': j.get('id'),
            'company': org, 'title': title, 'category': cat,
            'location': loc, 'score': round(score(cat, loc, wp), 1),
            'apply_url': j.get('applyUrl') or (j.get('jobUrl') or ''),
            'harvested': time.strftime('%Y-%m-%d'),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cats', type=str, default='design,web,ai,crm')
    ap.add_argument('--orgs', type=str, default='', help='solo estas orgs (slug)')
    ap.add_argument('--fresh', action='store_true', help='ignorar vistas anteriores')
    args = ap.parse_args()
    cats = set(args.cats.split(','))

    seen = set()
    if not args.fresh:
        try:
            seen = set(json.load(open(SEEN)))
        except Exception:
            seen = set()

    rows = []
    dead = []
    for org in LEVER_ORGS:
        if args.orgs and org not in args.orgs.split(','):
            continue
        try:
            got = harvest_lever(org, seen)
            rows += got
            print(f"lever/{org}: {len(got)} nuevas candidatas")
        except Exception as e:
            dead.append(f'lever/{org}: {repr(e)[:60]}')
        time.sleep(1)
    for org in ASHBY_ORGS:
        if args.orgs and org not in args.orgs.split(','):
            continue
        try:
            got = harvest_ashby(org, seen)
            rows += got
            print(f"ashby/{org}: {len(got)} nuevas candidatas")
        except Exception as e:
            dead.append(f'ashby/{org}: {repr(e)[:60]}')
        time.sleep(1)

    rows = [r for r in rows if r['category'] in cats]
    # dedupe por (org, titulo): no aplicar 2 veces al mismo puesto con distinta locacion
    best = {}
    for r in rows:
        k = (r['slug'], r['title'].split('(')[0].strip().lower())
        if k not in best or r['score'] > best[k]['score']:
            best[k] = r
    rows = list(best.values())
    rows.sort(key=lambda x: -x['score'])

    old = []
    if not args.fresh:  # --fresh reconstruye la cola (aplica dedupe/filtros nuevos)
        try:
            old = json.load(open(OUT))
        except Exception:
            old = []
    merged = {r['key']: r for r in old}
    for r in rows:
        merged[r['key']] = r
    final = sorted(merged.values(), key=lambda x: -x['score'])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(final, open(OUT, 'w'), ensure_ascii=False, indent=1)
    json.dump(sorted(seen), open(SEEN, 'w'))

    print(f"\n=== multi_queue.json: {len(final)} total ({len(rows)} nuevas) ===")
    from collections import Counter
    print('por ats:', dict(Counter(r['ats'] for r in final)))
    print('por categoria:', dict(Counter(r['category'] for r in final)))
    if dead:
        print('orgs con error (se reintentan la proxima):', len(dead))


if __name__ == '__main__':
    main()

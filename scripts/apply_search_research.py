"""Apply reviewed official-source research without pretending native features are SDK support."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / 'docs/tools/search_matrix'
RESEARCH = MATRIX / 'research.json'

def cell(value, url, comment=''):
    return {'value': value, 'source_url': url, 'comment': comment}

def apply_research():
    audit = json.loads(RESEARCH.read_text())
    existing = {p.stem: json.loads(p.read_text()) for p in (MATRIX/'data').glob('*.json')}
    for slug, review in audit['providers'].items():
        if slug not in existing and 'name' not in review:
            continue  # shared research, e.g. SerpApi engine family
        if slug not in existing:
            url = review['source_url']
            out = {'name': review['name'], 'links': {'slug': slug, 'docs': url, 'website': review['website']},
                   'env_keys': cell('Not integrated', url, 'Comparison only; anysearch does not read a key for this provider.'),
                   'python_extra': cell('Not integrated', url), 'mode': {'values': [], 'source_url': url, 'comment': 'No unified SDK mode mapping.'},
                   'p50_latency': cell('No current comparable measurement verified',url),
                   'notes': 'Comparison only; no anysearch SDK adapter is claimed.', 'comparison_only': True}
            for key in ['requires_key','snippet','domains','country','language','date','safe_search','answer','content','summary','highlights','news']:
                out[key]={'support':'unknown','source_url':url,'comment':'No anysearch adapter; see native API overview. Unknown is not unsupported.'}
            existing[slug]=out
    for slug,out in existing.items():
        base = 'serpapi' if slug.startswith('serpapi_') else slug
        review = audit['providers'].get(base)
        if not review:
            raise ValueError(f'Missing reviewed research for {slug}')
        url=review['source_url']
        caveat=review.get('caveat','')
        out['api_category']=cell(review['category'],url)
        out['api_status']=cell(review['status'],url,caveat)
        out['native_api']=cell(review['overview'],url,caveat)
        out['rate_limits']=cell(review['limits'],url,caveat)
        out['checked_at']=cell(review['checked_at'],url,'Official public documentation reviewed; no paid API or benchmark run. '+caveat)
        out['sdk_support']=cell('Comparison only — no adapter' if out.get('comparison_only') else 'Python + TypeScript adapters',out['links'].get('github','https://github.com/dhruv-anand-aintech/anysearch'),'Feature flags below describe unified SDK mappings, not every native API feature.')
        out['pricing_per_1k']=cell(review['pricing'],url,'Units and commitments differ; do not rank these as equivalent flat per-query prices. '+caveat)
        out['free_tier_limits']=cell(review['free'],url,'Trial, monthly credits and model-tool promotions are distinct. '+caveat)
        for field in ['api_status','native_api','rate_limits','checked_at','pricing_per_1k','free_tier_limits']:
            out[field]['links']={f'Official source {i+1}': u for i,u in enumerate(review.get('sources',[]))}
        out['evidence']={'checked_at': review['checked_at'], 'source_urls': list(dict.fromkeys([url]+review.get('sources',[]))), 'effective_date':review.get('effective_date'), 'method':'official documentation; no new benchmarks'}
        if base=='google_pse' or base=='bing_legacy': out['deprecated']=True
        # Keep historical benchmarks explicitly dated; a source review does not rerun them.
        if not out.get('comparison_only'):
            old=out['p50_latency']
            old['value']='Historical July 2026: '+old['value']
            old['comment']='Historical evidence retained from July 2026; not remeasured or claimed current. '+old.get('comment','')
        (MATRIX/'data'/f'{slug}.json').write_text(json.dumps(out,indent=2)+'\n')
    return audit

if __name__=='__main__': apply_research()

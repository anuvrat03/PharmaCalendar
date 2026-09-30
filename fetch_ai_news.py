import os
import json
import urllib.request
import xml.etree.ElementTree as ET

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

RSS_FEEDS = [
    {"name": "FDA Regulatory", "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"},
    {"name": "ET Pharma", "url": "https://health.economictimes.indiatimes.com/rss/pharma"},
    {"name": "FiercePharma", "url": "https://www.fiercepharma.com/rss/xml"},
    {"name": "Pharma news", "url": "https://pmn.feedify.net/rss"}
]

def fetch_rss_items():
    items = []
    # Custom Headers to bypass RSS scraping blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for source in RSS_FEEDS:
        try:
            req = urllib.request.Request(source['url'], headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_data = response.read()
                tree = ET.fromstring(xml_data)
                
                # Support standard RSS channel/item and Atom feeds
                channel = tree.find('channel')
                raw_items = channel.findall('item') if channel is not None else tree.findall('{http://www.w3.org/2005/Atom}entry')
                
                count = 0
                for item in raw_items:
                    if count >= 8: # Grab up to 8 items per source
                        break
                        
                    title = item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or ''
                    link = item.findtext('link') or ''
                    if not link:
                        link_elem = item.find('{http://www.w3.org/2005/Atom}link')
                        if link_elem is not None:
                            link = link_elem.attrib.get('href', '')
                            
                    desc = item.findtext('description') or item.findtext('summary') or ''
                    
                    # Clean title & link
                    title = title.strip()
                    link = link.strip()
                    
                    if title and link:
                        items.append({
                            'title': title,
                            'link': link,
                            'raw_desc': desc[:180].replace('<p>', '').replace('</p>', '').strip(),
                            'source': source['name']
                        })
                        count += 1
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
            
    return items

def process_with_ai(articles):
    processed = []
    for art in articles:
        # Default smart category based on keywords
        t_lower = art['title'].lower()
        if any(w in t_lower for w in ['fda', 'approval', 'approve', 'clearance']):
            cat = "FDA & APPROVALS"
        elif any(w in t_lower for w in ['buy', 'deal', 'acquire', 'acquisition', 'billion', 'million', 'stake', 'investment']):
            cat = "M&A & FINANCIALS"
        elif any(w in t_lower for w in ['cancer', 'drug', 'trial', 'study', 'vaccine', 'chemo', 'clinical']):
            cat = "CLINICAL & DRUGS"
        else:
            cat = "INDUSTRY GENERAL"

        if OPENROUTER_API_KEY:
            prompt = f"Summarize this pharma news title in 1 concise executive bullet point sentence: '{art['title']}'"
            payload = {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=6) as resp:
                    res = json.loads(resp.read().decode('utf-8'))
                    art['ai_summary'] = res['choices'][0]['message']['content'].strip()
            except Exception as e:
                print(f"AI API bypass for '{art['title'][:20]}...': {e}")
                art['ai_summary'] = art['raw_desc'] or art['title']
        else:
            art['ai_summary'] = art['raw_desc'] or art['title']
            
        art['category'] = cat
        processed.append(art)
        
    return processed

if __name__ == "__main__":
    articles = fetch_rss_items()
    final_data = process_with_ai(articles)
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)
    print(f"Saved {len(final_data)} total news items to data.json")

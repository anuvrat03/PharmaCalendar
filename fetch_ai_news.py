import os
import json
import urllib.request
import xml.etree.ElementTree as ET

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

RSS_FEEDS = [
    {"name": "FDA Press Releases", "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"},
    {"name": "ET Pharma", "url": "https://health.economictimes.indiatimes.com/rss/pharma"},
    {"name": "FiercePharma", "url": "https://www.fiercepharma.com/rss/xml"}
]

def fetch_rss_items():
    items = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for source in RSS_FEEDS:
        try:
            req = urllib.request.Request(source['url'], headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                tree = ET.fromstring(response.read())
                channel = tree.find('channel')
                if channel is not None:
                    # Fetch top 6 items from EACH feed to get ~18 total articles
                    for item in channel.findall('item')[:6]:
                        title = item.findtext('title', default='').strip()
                        link = item.findtext('link', default='').strip()
                        desc = item.findtext('description', default='').strip()
                        
                        if title and link:
                            items.append({
                                'title': title,
                                'link': link,
                                'raw_desc': desc[:200],
                                'source': source['name']
                            })
        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")
            
    return items

def process_with_ai(articles):
    if not OPENROUTER_API_KEY:
        print("No OpenRouter API key found. Saving raw feed.")
        return articles

    processed = []
    for art in articles:
        prompt = f"Summarize this pharma news title into 1 short key takeaway sentence and categorize it as one of [LAUNCH/APPROVAL, ALERT/RECALL, M&A, GENERAL]: '{art['title']}'"
        
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
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                ai_text = result['choices'][0]['message']['content'].strip()
                
                category = "GENERAL"
                for cat in ["LAUNCH/APPROVAL", "ALERT/RECALL", "M&A"]:
                    if cat in ai_text.upper():
                        category = cat
                        break
                        
                art['ai_summary'] = ai_text.replace("Category:", "").replace("Summary:", "").strip()
                art['category'] = category
        except Exception as e:
            print(f"AI summary error: {e}")
            art['ai_summary'] = art['raw_desc']
            art['category'] = "GENERAL"
            
        processed.append(art)
    return processed

if __name__ == "__main__":
    raw_articles = fetch_rss_items()
    final_data = process_with_ai(raw_articles)
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=2)
    print(f"Successfully processed {len(final_data)} articles!")

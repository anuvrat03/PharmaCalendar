import os
import json
import urllib.request
import xml.etree.ElementTree as ET

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

FEEDS = [
    {"url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", "source": "FDA Press Releases"},
    {"url": "https://www.fiercepharma.com/rss/xml", "source": "FiercePharma"},
    {"url": "https://pharma.economictimes.indiatimes.com/rss/topstories", "source": "ET Pharma"}
]

def fetch_rss_items():
    raw_articles = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for feed in FEEDS:
        try:
            req = urllib.request.Request(feed['url'], headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                for item in root.findall('.//item')[:3]:
                    title = item.find('title').text if item.find('title') is not None else ''
                    link = item.find('link').text if item.find('link') is not None else '#'
                    desc = item.find('description').text if item.find('description') is not None else ''
                    
                    if title:
                        raw_articles.append({
                            'title': title.strip(),
                            'link': link.strip(),
                            'source': feed['source'],
                            'raw_desc': desc[:200]
                        })
        except Exception as e:
            print(f"Error fetching {feed['source']}: {e}")
            
    return raw_articles[:8]

def summarize_with_openrouter(articles):
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY missing!")
        return articles

    prompt = f"""
    You are a Senior Regulatory & Pharma Analyst. Process these news items:
    {json.dumps(articles, indent=2)}

    Return a JSON array where each object has:
    - "title": (cleaned title)
    - "link": (original link)
    - "source": (original source)
    - "category": ("WARNING LETTER", "RECALL", "LAUNCH", "M&A", or "GENERAL")
    - "ai_summary": (1 short key takeaway sentence)

    Return ONLY raw valid JSON array, no markdown formatting.
    """

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data['choices'][0]['message']['content']
            clean_json = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
    except Exception as e:
        print(f"OpenRouter API call failed: {e}")
        return articles

if __name__ == "__main__":
    print("Fetching raw feeds...")
    items = fetch_rss_items()
    print("Processing items through OpenRouter...")
    processed = summarize_with_openrouter(items)
    
    with open("data.json", "w") as f:
        json.dump(processed, f, indent=2)
    print("data.json updated successfully!")

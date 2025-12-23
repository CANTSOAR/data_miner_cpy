import requests
from bs4 import BeautifulSoup
import csv

# check out "https://biopharmguy.com/biotech-company-directory.php" for more urls
SCRAPE_URL = "https://biopharmguy.com/links/company-by-location-northern-california.php"

def scrape_biotech_companies():
    url = SCRAPE_URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    print(f"Fetching data from {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    companies = []
    
    # The rows usually have these classes
    rows = soup.find_all('tr', class_=['sponsor', 'even', 'odd'])

    print(f"Found {len(rows)} potential rows. Parsing...")

    for row in rows:
        company_cell = row.find('td', class_='company')
        if not company_cell:
            continue

        name = "N/A"
        website = "N/A"
        
        # Get ALL links in this cell (sometimes there are 2: one for location icon, one for company)
        links = company_cell.find_all('a')
        
        target_link = None
        
        # Strategy: Find the "Best" Link
        # Priority 1: A link that has visible text (e.g. "Abbott")
        for link in links:
            if link.get_text(strip=True):
                target_link = link
                name = link.get_text(strip=True)
                break
        
        # Priority 2: If no text, look for an image (Sponsor logos), but IGNORE "Add'l Locations"
        if not target_link:
            for link in links:
                img = link.find('img')
                if img and img.get('alt'):
                    alt_text = img.get('alt')
                    # Skip the "Add'l Locations" icon
                    if "Add'l Locations" not in alt_text:
                        target_link = link
                        name = alt_text
                        break
        
        # If we found a valid link, extract the URL
        if target_link:
            raw_href = target_link.get('href', '')
            if raw_href:
                # If it's a relative link (starts with /), it's internal (skip or fix)
                # Usually the real company link is absolute (http...)
                if raw_href.startswith("http"):
                    website = raw_href.split('?')[0].split('#')[0]
                else:
                    website = "https://biopharmguy.com" + raw_href

        # 2. Extract Location
        location_cell = row.find('td', class_='location')
        location = location_cell.get_text(strip=True) if location_cell else "N/A"

        # 3. Extract Description
        desc_cell = row.find('td', class_='description')
        description = desc_cell.get_text(strip=True) if desc_cell else "N/A"

        # Only save if we found a name and it's not the "Add'l Locations" placeholder
        if name != "N/A" and "Add'l Locations" not in name:
            companies.append([name, website, location, description])

    # Save to CSV
    filename = "./data/companies.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Company", "Website", "Location", "Description"])
        writer.writerows(companies)

    print(f"✅ Successfully saved {len(companies)} companies to '{filename}'.")

if __name__ == "__main__":
    scrape_biotech_companies()
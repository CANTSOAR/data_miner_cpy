import pandas as pd
import tldextract
import time
import re
import random
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration ---
COMPANIES_PATH = 'data/companies.csv'
LEADS_PATH = 'data/master_leads_list.csv'
OUTPUT_PATH = 'data/master_leads_list_updated.csv'

def setup_driver():
    """
    Connects to an existing Chrome instance open on port 9222.
    """
    print("   Connecting to existing Chrome instance on port 9222...")
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print("\nCRITICAL ERROR: Could not connect to Chrome.")
        print("Make sure you ran: chrome.exe --remote-debugging-port=9222 --user-data-dir=\"C:/selenium/ChromeProfile\"")
        print(f"Details: {e}")
        exit()

def get_clean_domain(url):
    try:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"
    except:
        return ""

def construct_email(fmt_type, first, last, domain):
    first = first.lower().strip()
    last = last.lower().strip()
    f = first[0] if first else ""
    l = last[0] if last else ""
    
    if fmt_type == 'first.last': return f"{first}.{last}@{domain}"
    elif fmt_type == 'first': return f"{first}@{domain}"
    elif fmt_type == 'first_last': return f"{first}_{last}@{domain}"
    elif fmt_type == 'flast': return f"{f}{last}@{domain}"
    elif fmt_type == 'f.last': return f"{f}.{last}@{domain}"
    elif fmt_type == 'firstlast': return f"{first}{last}@{domain}"
    elif fmt_type == 'lastf': return f"{last}{f}@{domain}"
    elif fmt_type == 'firstl': return f"{first}{l}@{domain}"
    elif fmt_type == 'last': return f"{last}@{domain}"
    else: return f"{first}.{last}@{domain}"

def parse_rocketreach_formats(driver):
    found_formats = []
    rr_map = {
        '[first_initial][last]': 'flast', '[first].[last]': 'first.last',
        '[first]_[last]': 'first_last', '[first][last]': 'firstlast',
        '[first]': 'first', '[last]': 'last', '[first_initial].[last]': 'f.last',
        '[last][first_initial]': 'lastf', '[first][last_initial]': 'firstl'
    }

    try:
        # Wait for table
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table")))
        rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
        
        for row in rows[:2]:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                if cols:
                    format_text = cols[0].text.strip().lower()
                    if format_text in rr_map:
                        found_formats.append(rr_map[format_text])
            except: continue
    except:
        # Regex Fallback
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            matches = re.findall(r'(\[[a-z_]+\](?:[\._]\[[a-z_]+\])?).*?(\d+\.?\d*)%', body_text, re.IGNORECASE)
            sorted_matches = sorted(matches, key=lambda x: float(x[1]), reverse=True)
            for fmt_str, pct in sorted_matches:
                clean_fmt = fmt_str.lower().strip()
                if clean_fmt in rr_map:
                    found_formats.append(rr_map[clean_fmt])
        except: pass

    return list(dict.fromkeys(found_formats))

def find_rocketreach_url_via_google(driver, company_name):
    """
    Uses Google Search via Selenium.
    Warning: May trigger CAPTCHA. If it does, solve it manually in the window.
    """
    clean_search_name = company_name.replace(',', '').split('(')[0].strip()
    
    # 1. Construct Google Query
    query = f'site:rocketreach.co "{clean_search_name}" "email format"'
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://www.google.com/search?q={encoded_query}"
    
    print(f"   Searching Google: {query}")
    
    try:
        driver.get(search_url)
        
        # 2. Check for CAPTCHA
        if "google.com/sorry" in driver.current_url or "recaptcha" in driver.page_source.lower():
            print("   ⚠️  CAPTCHA DETECTED! Please solve it manually in the browser...")
            # Wait until user solves it (checks URL change)
            WebDriverWait(driver, 60).until(
                lambda d: "google.com/sorry" not in d.current_url
            )
            print("   ✅ CAPTCHA Solved. Resuming...")

        # 3. Extract Links (Google specific selectors)
        # Google standard results are usually in div.g a or just #search a
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "search")))
            links = driver.find_elements(By.CSS_SELECTOR, "#search a")
        except:
            print("   Error finding results container.")
            return None

        # 4. Prepare Validation Tokens
        clean_company = ''.join(c for c in company_name.lower() if c.isalnum() or c.isspace())
        stop_words = {'inc', 'llc', 'ltd', 'corp', 'corporation', 'co', 'limited', 'group', 'trading', 'technologies', 'holdings'}
        company_tokens = [word for word in clean_company.split() if word not in stop_words]
        if not company_tokens: company_tokens = [clean_company.split()[0]] if clean_company else []

        # 5. Filter Results
        for link in links:
            try:
                href = link.get_attribute('href')
                if not href: continue
                href = href.lower()

                # Google sometimes wraps links (e.g., /url?q=...), we need to handle that or standard links
                if 'rocketreach.co' not in href: continue
                if 'email-format' not in href: continue
                
                # Verify company match
                if any(token in href for token in company_tokens):
                    print(f"   -> ✅ Found Verified URL: {href}")
                    return href
            except:
                continue
                
    except Exception as e:
        print(f"   Search error: {e}")
        return None
        
    print("   No verified RocketReach link found.")
    return None

def get_email_formats_for_company(driver, company_name, website_url):
    domain = get_clean_domain(website_url)
    if not domain: return ['fail', 'fail'] 
    
    # Use Google Search Function
    url = find_rocketreach_url_via_google(driver, company_name)
    
    found_formats = []
    
    if url:
        try:
            driver.get(url)
            time.sleep(random.uniform(2, 4)) 
            found_formats = parse_rocketreach_formats(driver)
        except Exception as e:
            print(f"   Error parsing page {company_name}: {e}")

    if not found_formats: found_formats = ['fail', 'fail'] 
        
    if len(found_formats) < 2:
        if 'first.last' not in found_formats: found_formats.append('first.last')
        else: found_formats.append('first')
            
    return found_formats[:2]

def main():
    print("--- Starting Email Format Discovery (Google Mode) ---")
    
    try:
        df_companies = pd.read_csv(COMPANIES_PATH)
        df_leads = pd.read_csv(LEADS_PATH, delimiter=";")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    driver = setup_driver()

    company_format_map = {}
    total_companies = len(df_companies)
    
    for idx, row in df_companies.iterrows():
        company = row['Company']
        website = row['Website']
        
        print(f"[{idx+1}/{total_companies}] Processing {company}...")
        
        formats = get_email_formats_for_company(driver, company, website)
        
        clean_domain = get_clean_domain(website)
        company_format_map[company] = {'domain': clean_domain, 'formats': formats}
        print(f"   -> Top Formats: {formats}")
        
        # Be slightly nicer to Google to avoid immediate blocks
        time.sleep(random.uniform(2, 4))

    print("\n--- Generating Emails for Leads ---")

    for index, row in df_leads.iterrows():
        company = row['Company']
        first = str(row['First Name']) if pd.notna(row['First Name']) else ""
        last = str(row['Last Name']) if pd.notna(row['Last Name']) else ""
        
        if company in company_format_map:
            data = company_format_map[company]
            fmt_list = data['formats']
            domain = data['domain']
            
            if len(fmt_list) > 0: df_leads.at[index, 'Email 1'] = construct_email(fmt_list[0], first, last, domain)
            if len(fmt_list) > 1: df_leads.at[index, 'Email 2'] = construct_email(fmt_list[1], first, last, domain)

    df_leads.to_csv(OUTPUT_PATH, index=False, sep=";")
    print(f"\nSuccess! Updated leads list saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
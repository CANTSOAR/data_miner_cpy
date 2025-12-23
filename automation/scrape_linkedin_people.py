import csv
import time
import random
import string
import smtplib
import dns.resolver
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# --- CONFIGURATION ---
INPUT_FILE = "./data/temp.csv"
OUTPUT_FILE = "./data/master_leads_list.csv"
SCROLL_PAUSE_TIME = 2.5
NUMBER_OF_SCROLLS = 5 
SENDER_EMAIL = "verify@example.com"

# --- HELPER FUNCTIONS ---

def get_domain_candidates(url):
    try:
        if not url or "http" not in url: return []
        raw_domain = urlparse(url).netloc.replace("www.", "")
        candidates = [raw_domain]
        
        parts = raw_domain.split('.')
        if len(parts) >= 3 and len(parts[-1]) == 2:
            if parts[-2] in ['com', 'co']:
                global_domain = f"{parts[-3]}.com"
                candidates.insert(0, global_domain)
        return candidates
    except:
        return []

def get_mx_record(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        records = sorted(records, key=lambda r: r.preference)
        return str(records[0].exchange)
    except:
        return None

def verify_email_smtp(email):
    domain = email.split('@')[-1]
    mx_record = get_mx_record(domain)
    if not mx_record: return None

    try:
        server = smtplib.SMTP(timeout=5)
        server.set_debuglevel(0)
        server.connect(mx_record)
        server.helo(server.local_hostname or 'localhost') 
        server.mail(SENDER_EMAIL)
        code, message = server.rcpt(email)
        server.quit()

        if code == 250: return True
        if code == 550: return False
        return None 
    except Exception:
        return None

def find_company_email_format(driver, website_url):
    domains_to_test = get_domain_candidates(website_url)
    if not domains_to_test: return "format_1", "", "Low"

    print(f"   🔎 Pathfinder: Candidates {domains_to_test}...")

    # --- STEP 1: FIND A CLEAN CANDIDATE ---
    full_name = None
    cards = driver.find_elements(By.CSS_SELECTOR, '.org-people-profile-card__profile-info')
    
    # Check first 10 cards to find ONE good one
    for card in cards[:10]:
        try:
            name_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__title')
            raw_name = name_el.text.strip().split('\n')[0]
            
            # FILTER 1: Skip Private Profiles
            if "LinkedIn Member" in raw_name or "User" in raw_name: continue
            
            # FILTER 2: Skip Titles/degrees (Ph.D., Dr., Mr., Jr.)
            # If the name has a dot, it's likely risky for pattern detection.
            if "." in raw_name: 
                # print(f"      Skipping '{raw_name}' (Contains dot/title)")
                continue
            if "," in raw_name: 
                # print(f"      Skipping '{raw_name}' (Contains comma)")
                continue

            # Valid Length Check
            if len(raw_name.split()) == 2:
                full_name = raw_name
                break # Found a clean name!
        except: continue
            
    if not full_name:
        print("   ⚠️ No clean candidate found (all had dots or were private). Defaulting.")
        return "format_1", domains_to_test[0], "Low"

    print(f"   🧪 Testing with clean user: {full_name}")

    # --- STEP 2: TEST DOMAINS ---
    for domain in domains_to_test:
        print(f"      Testing @{domain}...")
        
        # Check Catch-all
        random_user = ''.join(random.choices(string.ascii_lowercase, k=10))
        fake_email = f"{random_user}@{domain}"
        is_valid = verify_email_smtp(fake_email)
        
        if is_valid is True:
            print(f"      ⚠️ @{domain} is Catch-All. Using as default.")
            return "format_1", domain, "Medium"
        
        if is_valid is None:
            print(f"      ⚠️ Connection blocked for @{domain}.")
            continue 

        # Format Check
        clean_name = ''.join(e for e in full_name if e.isalnum() or e.isspace()).lower()
        parts = clean_name.split()
        first, last = parts[0], parts[-1]
        f = first[0]

        candidates = [
            (f"{first}.{last}@{domain}", "format_1"),
            (f"{f}{last}@{domain}",       "format_2"),
            (f"{first}@{domain}",         "format_3")
        ]

        for email, fmt_code in candidates:
            if verify_email_smtp(email) is True:
                print(f"      🎉 SUCCESS! Verified Pattern: {email}")
                return fmt_code, domain, "High"
            
    print("   ⚠️ All tests failed. Defaulting to First.Last.")
    return "format_1", domains_to_test[0], "Low"

# --- MAIN LOGIC ---

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except:
        print("❌ Connect error. Run Chrome in debug mode first!")
        exit()

def construct_email(fmt_code, first, last, f, domain):
    if fmt_code == "format_1": return f"{first}.{last}@{domain}"
    if fmt_code == "format_2": return f"{f}{last}@{domain}"
    if fmt_code == "format_3": return f"{first}@{domain}"
    return ""

def main():
    driver = setup_driver()
    
    headers = ["Full Name", "First Name", "Last Name", "Position", "Company", "LinkedIn", "Email 1", "Email 2", "Confidence", "Reason"]

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(headers)

    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        
        for row in reader:
            company = row.get("Company")
            target_url = row.get("LinkedIn_People_URL")
            website = row.get("Website")
            
            if not target_url or "http" not in target_url: continue

            print(f"Processing: {company}...")
            driver.get(target_url)
            time.sleep(3)

            # 1. PATHFINDER (Now filters out "Ph.D." names)
            winning_format, winning_domain, confidence = find_company_email_format(driver, website)
            
            fallback_format = "format_2" if winning_format == "format_1" else "format_1"

            # 2. SCROLL
            print(f"   Scrolling...")
            for i in range(NUMBER_OF_SCROLLS):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(SCROLL_PAUSE_TIME)
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, ".scaffold-finite-scroll__load-button")
                    if btn.is_displayed(): driver.execute_script("arguments[0].click();", btn)
                except: pass

            # 3. PARSE
            cards = driver.find_elements(By.CSS_SELECTOR, '.org-people-profile-card__profile-info')
            batch_data = []

            for card in cards:
                try:
                    # Name extraction
                    try:
                        name_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__title')
                        full_name = name_el.text.strip().split('\n')[0]
                    except: continue
                    
                    if "LinkedIn Member" in full_name: continue

                    # Name Cleaning & Parsing
                    # This logic handles names in the FINAL LIST.
                    # We strip non-alphanumeric chars here so "John L." becomes "John L"
                    clean = ''.join(e for e in full_name if e.isalnum() or e.isspace()).lower()
                    parts = clean.split()
                    
                    if len(parts) < 2: continue
                    
                    first_name = parts[0].capitalize()
                    # If name is "John L Smith", parts[-1] is "Smith".
                    # If name is "Jane Doe PhD", parts[-1] is "PhD" (unavoidable without complex NLP, but acceptable for bulk)
                    last_name = parts[-1].capitalize()
                    
                    # Position
                    try:
                        role_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__subtitle')
                        position = role_el.text.strip()
                    except: position = "N/A"

                    # URL
                    try:
                        link_el = name_el.find_element(By.TAG_NAME, 'a')
                        lnk_url = link_el.get_attribute('href').split('?')[0]
                    except: lnk_url = "N/A"

                    # Emails
                    f_init = first_name[0].lower()
                    l_clean = last_name.lower()
                    f_clean = first_name.lower()

                    email_1 = construct_email(winning_format, f_clean, l_clean, f_init, winning_domain)
                    email_2 = "" 
                    if confidence != "High":
                        email_2 = construct_email(fallback_format, f_clean, l_clean, f_init, winning_domain)

                    reason = f"Impressed by your work as {position} at {company}."

                    batch_data.append([
                        full_name, first_name, last_name, position, company, lnk_url, email_1, email_2, confidence, reason
                    ])
                except: continue

            with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f_app:
                w = csv.writer(f_app)
                w.writerows(batch_data)
            
            print(f"   ✅ Saved {len(batch_data)} leads (Confidence: {confidence}).")
            time.sleep(random.uniform(5, 10))

    print("\nDONE!")

if __name__ == "__main__":
    main()
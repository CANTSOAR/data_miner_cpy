import csv
import time
import random
import string
import smtplib
import dns.resolver
import socket
from typing import Tuple, Optional
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

# --- CONFIGURATION ---
INPUT_FILE = "./data/linkedin_urls.csv"
OUTPUT_FILE = "./data/master_leads_list.csv"
SCROLL_PAUSE_TIME = 1.5
NUMBER_OF_SCROLLS = 10 

# IMPORTANT: Set up Gmail App Password at https://myaccount.google.com/apppasswords
GMAIL_ADDRESS = "needmoneyneedcar@gmail.com"
GMAIL_APP_PASSWORD = "ijotdurrxyouubsf"  # Replace with your app password!

# Rate limiting settings
VERIFICATION_DELAY = 3  # Seconds between each email verification
DOMAIN_SWITCH_DELAY = 5  # Extra delay when switching domains
MAX_VERIFICATIONS_PER_DOMAIN = 1  # Limit checks per domain to avoid Gmail limits

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


def verify_email_smtp_authenticated(email: str, gmail_user: str, gmail_password: str, timeout: int = 15) -> Optional[bool]:
    """
    Verify email using authenticated Gmail SMTP connection.
    More reliable than anonymous verification.
    
    Returns:
    - True: Email exists
    - False: Email doesn't exist
    - None: Unable to verify
    """
    try:
        # Connect through Gmail's SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=timeout)
        server.set_debuglevel(0)
        server.starttls()
        server.login(gmail_user, gmail_password)
        
        # Set sender
        server.mail(gmail_user)
        
        # Test recipient - this fails immediately if invalid
        code, message = server.rcpt(email)
        server.quit()
        
        # 250 = accepted, 550 = rejected
        if code == 250:
            return True
        elif code in [550, 551, 553]:
            return False
        else:
            return None
            
    except smtplib.SMTPRecipientsRefused:
        return False
    except (socket.timeout, smtplib.SMTPServerDisconnected):
        return None
    except smtplib.SMTPAuthenticationError:
        print("         ❌ Gmail authentication failed! Check your app password.")
        return None
    except Exception as e:
        print(f"         Error verifying {email}: {str(e)}")
        return None


def detect_catch_all(domain: str, gmail_user: str, gmail_password: str, num_tests: int = 2) -> bool:
    """
    Test random emails to detect catch-all domains.
    Returns True if domain accepts all emails (catch-all).
    """
    results = []
    
    for i in range(num_tests):
        random_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=18))
        fake_email = f"{random_user}@{domain}"
        
        result = verify_email_smtp_authenticated(fake_email, gmail_user, gmail_password)
        results.append(result)
        
        # If we get a definite False, it's not catch-all
        if result is False:
            return False
        
        # Rate limiting between catch-all tests
        if i < num_tests - 1:
            time.sleep(VERIFICATION_DELAY)
    
    # If all random emails return True, it's catch-all
    return True in results


def find_company_email_format(driver, website_url, gmail_user: str, gmail_password: str) -> Tuple[str, str, str]:
    """
    Find email format using authenticated SMTP verification.
    """
    domains_to_test = get_domain_candidates(website_url)
    if not domains_to_test:
        return "format_1", "", "Low"

    print(f"   🔎 Pathfinder: Testing domains {domains_to_test}...")

    # --- STEP 1: FIND MULTIPLE CLEAN CANDIDATES ---
    clean_names = []
    cards = driver.find_elements(By.CSS_SELECTOR, '.org-people-profile-card__profile-info')
    
    for card in cards[:25]:
        try:
            name_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__title')
            raw_name = name_el.text.strip().split('\n')[0]
            
            # Skip invalid names
            if any(x in raw_name for x in ["LinkedIn Member", "User", ".", ","]):
                continue
            
            # Must be exactly 2 parts (First Last)
            parts = raw_name.split()
            if len(parts) == 2 and all(len(p) >= 2 for p in parts):
                clean_names.append(raw_name)
                if len(clean_names) >= 3:
                    break
        except:
            continue
    
    if not clean_names:
        print("   ⚠️ No clean candidates found. Defaulting to format_1.")
        return "format_1", domains_to_test[0] if domains_to_test else "", "Low"

    print(f"   🧪 Testing with {len(clean_names)} candidates: {clean_names}")

    # --- STEP 2: TEST DOMAINS ---
    for domain_idx, domain in enumerate(domains_to_test):
        print(f"      Testing @{domain}...")
        
        # Extra delay when switching domains
        if domain_idx > 0:
            print(f"      ⏳ Cooling down before next domain...")
            time.sleep(DOMAIN_SWITCH_DELAY)
        
        # Check if catch-all
        print(f"      Checking for catch-all behavior...")
        if detect_catch_all(domain, gmail_user, gmail_password):
            print(f"      ⚠️ @{domain} is Catch-All. Skipping.")
            continue

        # Test format patterns with verification limit
        format_results = {}
        verifications_count = 0
        
        for name_idx, full_name in enumerate(clean_names):
            if verifications_count >= MAX_VERIFICATIONS_PER_DOMAIN:
                print(f"      ⚠️ Reached verification limit for {domain}. Moving on.")
                break
                
            clean_name = ''.join(e for e in full_name if e.isalnum() or e.isspace()).lower()
            parts = clean_name.split()
            first, last = parts[0], parts[-1]
            f, l = first[0], last[0]

            # Test most common formats first
            test_formats = [
                (f"{first}.{last}@{domain}", "format_1"),      # john.doe
                (f"{f}{last}@{domain}", "format_2"),            # jdoe
                (f"{first}{last}@{domain}", "format_4"),        # johndoe
                (f"{first}_{last}@{domain}", "format_5"),       # john_doe
            ]

            for email, fmt_code in test_formats:
                if verifications_count >= MAX_VERIFICATIONS_PER_DOMAIN:
                    break
                    
                print(f"         Testing {email}...")
                
                result = verify_email_smtp_authenticated(email, gmail_user, gmail_password)
                verifications_count += 1
                
                if result is True:
                    format_results[fmt_code] = format_results.get(fmt_code, 0) + 1
                    print(f"         ✓ Valid!")
                    
                    # If we found 2+ matches with same format, we're confident
                    if format_results[fmt_code] >= 2:
                        print(f"      🎉 HIGH CONFIDENCE! Pattern: {fmt_code} (verified {format_results[fmt_code]} times)")
                        return fmt_code, domain, "High"
                        
                elif result is False:
                    print(f"         ✗ Bounced")
                else:
                    print(f"         ? Indeterminate")
                
                # Rate limiting between checks
                time.sleep(VERIFICATION_DELAY)

        # Check results after testing all candidates
        if format_results:
            best_format = max(format_results, key=format_results.get)
            confidence = "Medium" if format_results[best_format] == 1 else "High"
            print(f"      ✓ Found pattern: {best_format} (verified {format_results[best_format]} times)")
            return best_format, domain, confidence
    
    print("   ⚠️ All tests failed or catch-all. Defaulting to format_1.")
    return "format_1", domains_to_test[0] if domains_to_test else "", "Low"


# --- MAIN LOGIC ---

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except:
        print("❌ Connection error. Run Chrome in debug mode first!")
        print("   Command: chrome.exe --remote-debugging-port=9222 --user-data-dir=\"C:/selenium/ChromeProfile\"")
        exit()


def construct_email(fmt_code, first, last, f, domain):
    """Construct email based on format code."""
    if fmt_code == "format_1": return f"{first}.{last}@{domain}"
    if fmt_code == "format_2": return f"{f}{last}@{domain}"
    if fmt_code == "format_3": return f"{first}@{domain}"
    if fmt_code == "format_4": return f"{first}{last}@{domain}"
    if fmt_code == "format_5": return f"{first}_{last}@{domain}"
    return f"{first}.{last}@{domain}"  # Default fallback


def main():
    # Check Gmail credentials
    if "YOUR_16_CHAR_APP_PASSWORD_HERE" in GMAIL_APP_PASSWORD:
        print("❌ ERROR: You must set your Gmail App Password!")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Generate an app password for 'Mail'")
        print("   3. Replace GMAIL_APP_PASSWORD in the code")
        return
    
    driver = setup_driver()
    
    headers = ["Full Name", "First Name", "Last Name", "Position", "Company", "LinkedIn", "Email 1", "Email 2", "Reason"]

    # Create output file with headers
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(headers)

    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        
        for row in reader:
            company = row.get("Company", "")
            target_url = row.get("LinkedIn_People_URL", "")
            website = row.get("Website", "")
            
            if not target_url or "http" not in target_url:
                continue

            print(f"\n{'='*60}")
            print(f"Processing: {company}")
            print(f"{'='*60}")
            
            driver.get(target_url)
            time.sleep(random.uniform(1, 2))

            # 1. PATHFINDER - Find email format with authenticated SMTP
            print(f"\n📧 Phase 1: Email Format Detection")
            #winning_format, winning_domain, confidence = find_company_email_format(
            #    driver, website, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
            #)
            
            #print(f"\n   Result: {winning_format} @ {winning_domain}")
            #print(f"   Confidence: {confidence}")
            
            # Set fallback format
            #fallback_format = "format_2" if winning_format == "format_1" else "format_1"

            # 2. SCROLL & LOAD MORE PROFILES
            print(f"\n📜 Phase 2: Loading profiles...")
            for i in range(NUMBER_OF_SCROLLS):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1, 2))
                
                # Click "Show more" button if present
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, ".scaffold-finite-scroll__load-button")
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(random.uniform(1, 2))
                except:
                    pass

            # 3. PARSE PROFILES
            print(f"\n👥 Phase 3: Extracting leads...")
            cards = driver.find_elements(By.CSS_SELECTOR, '.org-people-profile-card__profile-info')
            batch_data = []

            for card in cards:
                try:
                    # Extract name
                    try:
                        name_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__title')
                        full_name = name_el.text.strip().split('\n')[0]
                    except:
                        continue
                    
                    if "LinkedIn Member" in full_name:
                        continue

                    if "." in full_name:
                        continue

                    if "," in full_name:
                        continue

                    if len(full_name.split()[-1]) == 1:
                        continue
                    
                    if len(full_name.split()) != 2:
                        continue

                    # Clean and parse name
                    clean = ''.join(e for e in full_name if e.isalnum() or e.isspace()).lower()
                    parts = clean.split()
                    
                    first_name = parts[0].capitalize()
                    last_name = parts[-1].capitalize()
                    
                    # Extract position
                    try:
                        role_el = card.find_element(By.CSS_SELECTOR, '.artdeco-entity-lockup__subtitle')
                        position = role_el.text.strip()
                    except:
                        position = "N/A"

                    # Extract LinkedIn URL
                    try:
                        link_el = name_el.find_element(By.TAG_NAME, 'a')
                        lnk_url = link_el.get_attribute('href').split('?')[0]
                    except:
                        lnk_url = "N/A"

                    # Construct emails
                    f_init = first_name[0].lower()
                    l_clean = last_name.lower()
                    f_clean = first_name.lower()

                    #email_1 = construct_email(winning_format, f_clean, l_clean, f_init, winning_domain)
                    #email_2 = "" 
                    
                    # Only add fallback if confidence isn't high
                    #if confidence != "High":
                    #    email_2 = construct_email(fallback_format, f_clean, l_clean, f_init, winning_domain)

                    reason = f"Impressed by your work as {position} at {company}."

                    batch_data.append([
                        full_name, first_name, last_name, position, company, 
                        lnk_url, "", "", reason
                    ])
                    
                except Exception as e:
                    continue

            # Save batch to CSV
            with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f_app:
                w = csv.writer(f_app, delimiter=";")
                w.writerows(batch_data)
            
            print(f"\n   ✅ Saved {len(batch_data)} leads")
            #print(f"   📊 Email Confidence: {confidence}")
            #print(f"   📧 Format: {winning_format} @ {winning_domain}")
            
            # Delay between companies to respect rate limits
            delay = random.uniform(1, 2)
            print(f"\n   ⏳ Cooling down for {delay:.1f} seconds before next company...")
            time.sleep(delay)

    print("\n" + "="*60)
    print("✅ DONE! All leads saved to", OUTPUT_FILE)
    print("="*60)


if __name__ == "__main__":
    main()
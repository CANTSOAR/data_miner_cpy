# Biotech Lead Scraper & Automation Toolkit

This toolkit is designed to automate the generation of high-quality leads for biotech companies. It consists of two main components:
1. **Chrome Extension:** For manual, quick scraping of any LinkedIn People tab you are viewing.
2. **Python Automation:** A "Master Workflow" that finds companies, gets their LinkedIn pages, verifies email formats via SMTP, and scrapes leads automatically.

---

## 📂 Project Structure

```text
├── automation/
│   ├── scrape_company_list.py      # Step 1: Scrapes BioPharmGuy for company names/websites
│   ├── make_linkedin_urls.py       # Step 2: Finds the official LinkedIn "People" tab for each company
│   └── scrape_linkedin_people.py   # Step 3: The "Master" script (Selenium + Email Verification)
├── extension/
│   ├── manifest.json
│   ├── content.js
│   ├── background.js
│   └── ...
├── data/
│   ├── biotech_companies_norcal.csv # Output of Step 1
│   ├── temp.csv                     # Output of Step 2 (Targets for the master script)
│   └── master_leads_list.csv        # FINAL Output (Ready for outreach)
└── .venv/                           # Python Virtual Environment
```

## 🛠️ Part 1: The Chrome Extension

Use this when you want to manually navigate to a specific company and scrape the data instantly.

### Installation

1. Open Chrome/Arc and go to `chrome://extensions`.
2. Toggle **Developer mode** (top right corner).
3. Click **Load unpacked**.
4. Select the `extension` folder from this project.

### How to Use

1. Navigate to any Company's **People** tab on LinkedIn (e.g., `linkedin.com/company/eli-lilly-and-company/people/`).
2. **Scroll down** to load a few profiles.
3. Press **`Cmd + Shift + E`** (Mac) or `Ctrl + Shift + E` (Windows).
4. **Success:** A green banner will appear, and the data (Name, Role, URL, Email Permutations) is copied to your clipboard.
5. Paste directly into Google Sheets/Excel.

> **Note:** If the shortcut doesn't work, go to `chrome://extensions/shortcuts` and manually set it to `Cmd + Shift + E`.

---

## 🤖 Part 2: The Automation Workflow

This is the fully automated pipeline. It goes from "Raw Company List" to "Verified Leads" without you needing to click anything.

### 1. Environment Setup

Always make sure your virtual environment is active before running scripts.

```bash
# In your terminal
source .venv/bin/activate
```

*(If you haven't installed dependencies yet: `pip install -r requirements.txt`)*

### 2. The Workflow

Run these scripts in order.

#### **Step 1: Get the Companies**

Scrapes company names and websites from directories.

* **Script:** `automation/scrape_company_list.py`
* **Input:** URL inside the script (currently set to BioPharmGuy NorCal).
* **Output:** `data/companies.csv`
* **Source:** For more regions/lists, check [BioPharmGuy Directory](https://biopharmguy.com/biotech-company-directory.php) and update the URL in the script.

```bash
python automation/scrape_company_list.py
```

#### **Step 2: Find LinkedIn URLs**

Uses DuckDuckGo to find the exact "People" tab for every company in Step 1.

* **Script:** `automation/make_linkedin_urls.py`
* **Input:** `data/companies.csv`
* **Output:** `data/linkedin_urls.csv` (This creates the target list).

```bash
python automation/make_linkedin_urls.py
```

#### **Step 3: The Master Scraper (Selenium)**

This script takes control of your browser, scrolls through each company, finds the correct email format (by pinging the server), and saves the leads.

**⚠️ CRITICAL: Launch Chrome in Debug Mode First**
You must launch Chrome specifically so Python can control your logged-in session.

1. **Quit Chrome** completely (`Cmd + Q`).
2. Run this command in your terminal:
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_debug_profile"
```


3. A new Chrome window will open. **Log in to LinkedIn** in this window.
4. Run the script:
```bash
python automation/scrape_linkedin_people.py
```



* **Input:** `data/linkedin_urls.csv`
* **Output:** `data/master_leads_list.csv`

---

## 📊 Data Output Logic

The final `master_leads_list.csv` includes a **Confidence** column:

* **High:** We pinged the mail server and it returned "250 OK". This email is real.
* **Medium:** The server is a "Catch-All" (accepts everything). We used the most common format (First.Last) but couldn't verify it 100%.
* **Low:** Verification failed or bounced. **Action:** Check these manually on RocketReach.

---

## ⚠️ Safety & Limits

* **Rate Limiting:** The scripts have built-in `time.sleep()` delays to mimic human behavior. Do not remove them, or LinkedIn will log you out.
* **Email Verification:** The script limits server pings to ~3-4 per company to avoid getting your IP blacklisted by corporate firewalls.
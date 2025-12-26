import csv
import time
import random
from ddgs import DDGS

INPUT_FILE = "./data/temp.csv"
OUTPUT_FILE = "./data/linkedin_urls.csv"

def get_linkedin_people_url(company_name):
    # DuckDuckGo query
    query = f'site:linkedin.com/company "{company_name}"'
    
    try:
        # DDGS().text() returns a generator of results
        # max_results=3 grabs the top 3
        results = DDGS().text(query, max_results=3)
        
        for r in results:
            url = r['href']  # DuckDuckGo returns a dictionary with 'href'
            print(f"   (Checking: {url})") # Debug print
            
            # Check if it's a valid Company page
            if "linkedin.com/company/" in url:
                # Clean the URL
                base_url = url.split("?")[0].split("#")[0]
                base_url = base_url.rstrip("/")
                
                # Success!
                return base_url + "/people/?keywords=Business%20Development"
                
    except Exception as e:
        print(f"  Error searching for {company_name}: {e}")
        return None
    
    return None

def main():
    input_file = INPUT_FILE
    output_file = OUTPUT_FILE
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f_in, \
             open(output_file, 'w', newline='', encoding='utf-8') as f_out:
            
            reader = csv.reader(f_in)
            writer = csv.writer(f_out)
            
            # Read header
            header = next(reader, None)
            if header:
                # Add the new column header
                writer.writerow(header + ["LinkedIn_People_URL"])
            
            rows = list(reader)
            total = len(rows)
            
            print(f"🚀 Processing {total} companies using DuckDuckGo...")

            for i, row in enumerate(rows):
                company_name = row[0]
                
                print(f"[{i+1}/{total}] Searching: 'site:linkedin.com/company '{company_name}''...")
                
                people_url = get_linkedin_people_url(company_name)
                
                if people_url:
                    print(f"  -> ✅ Found: {people_url}")
                    row.append(people_url)
                else:
                    print("  -> ❌ Not found")
                    row.append("Not Found")
                
                writer.writerow(row)
                
                # DuckDuckGo is nicer, but we still sleep a little to be polite
                time.sleep(random.uniform(2, 4))

        print(f"\n🎉 Done! Results saved to '{output_file}'.")
        
    except FileNotFoundError:
        print(f"Error: Could not find '{input_file}'. Check your file path!")

if __name__ == "__main__":
    main()
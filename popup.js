// --- BUTTON LISTENERS ---

document.getElementById("startBtn").addEventListener("click", async () => {
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  // Inject the scroller function
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    function: startScrolling
  });
  
  document.getElementById("results").placeholder = "Scrolling... Watch the page load rows.";
});

document.getElementById("stopBtn").addEventListener("click", async () => {
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Inject the stopper and scraper function
  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    function: stopAndScrape
  }, (results) => {
    // Handle the data returned from the page
    if (results && results[0] && results[0].result) {
      document.getElementById("results").value = results[0].result;
      document.getElementById("results").select();
      document.execCommand('copy');
      alert("Stopped scrolling. Data copied to clipboard!");
    }
  });
});

// --- INJECTED FUNCTIONS (These run inside the LinkedIn page) ---

function startScrolling() {
  // Check if already scrolling to prevent double timers
  if (window.linkedInScraperInterval) return;

  alert("Auto-scroll started. I will scroll every 2 seconds. Open the extension again and click 'Stop' when you have enough data.");

  // Scroll to bottom every 2 seconds
  window.linkedInScraperInterval = setInterval(() => {
    window.scrollTo(0, document.body.scrollHeight);
  }, 2000);
}

function stopAndScrape() {
  // 1. Stop the scrolling
  if (window.linkedInScraperInterval) {
    clearInterval(window.linkedInScraperInterval);
    window.linkedInScraperInterval = null;
  }

  // 2. Perform the Scrape
  const cards = document.querySelectorAll('.org-people-profile-card__profile-info');
  let output = "Name\tRole\tUrl\n"; 

  cards.forEach(card => {
    try {
      // Name
      const nameNode = card.querySelector('.artdeco-entity-lockup__title');
      let name = nameNode ? nameNode.innerText.trim() : "N/A";

      // Role
      const roleNode = card.querySelector('.artdeco-entity-lockup__subtitle');
      let role = roleNode ? roleNode.innerText.trim() : "N/A";

      // URL
      const anchor = card.querySelector('.artdeco-entity-lockup__title a');
      let rawUrl = anchor ? anchor.href : "";
      let cleanUrl = rawUrl.split('?')[0]; // Remove tracking ID

      output += `${name}\t${role}\t${cleanUrl}\n`;
    } catch (e) {
      console.error("Error parsing card", e);
    }
  });

  return output;
}
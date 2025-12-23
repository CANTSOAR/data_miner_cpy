// Listen for the keyboard shortcut or the popup button
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "scrape") {
    const data = scrapePeopleTabOnly();
    
    if (data) {
      // Use the robust copy function
      copyToClipboard(data);
      sendResponse({result: "success"});
    } else {
      showErrorPopup("❌ No data found. Scroll down first!");
      sendResponse({result: "error"});
    }
  }
});

/**
 * Robust Copy Function
 */
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showSuccessPopup("✅ Copied " + (text.split('\n').length - 2) + " profiles!");
  }).catch(err => {
    console.warn("Modern copy failed, trying fallback...", err);
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-9999px";
      textArea.style.top = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      
      if (successful) {
        showSuccessPopup("✅ Copied " + (text.split('\n').length - 2) + " profiles!");
      } else {
        showErrorPopup("❌ Clipboard blocked. Click the page and try again.");
      }
    } catch (fallbackErr) {
      showErrorPopup("❌ Could not copy text.");
    }
  });
}

function scrapePeopleTabOnly() {
  const cards = document.querySelectorAll('.org-people-profile-card__profile-info');
  if (cards.length === 0) return null;

  let output = "Name\tRole\tUrl\n"; 
  let count = 0;

  cards.forEach(card => {
    try {
      // 1. Exclusion: Skip "People you may know"
      const parentCard = card.closest('.artdeco-card');
      if (parentCard) {
        const header = parentCard.querySelector('h2');
        if (header && header.innerText.toLowerCase().includes('people you may know')) {
          return; 
        }
      }

      // 2. Name
      const nameNode = card.querySelector('.artdeco-entity-lockup__title');
      if (!nameNode) return;
      let name = nameNode.innerText.trim().split('\n')[0];

      // --- NEW FILTER: Skip "LinkedIn Member" ---
      if (name.toLowerCase() === "linkedin member") return;

      // 3. URL (Get this early to check validity)
      const anchor = card.querySelector('a');
      let cleanUrl = anchor && anchor.href ? anchor.href.split('?')[0] : "N/A";

      // --- NEW FILTER: Skip if no valid URL found ---
      if (cleanUrl === "N/A" || cleanUrl === "") return;

      // 4. Role
      const roleNode = card.querySelector('.artdeco-entity-lockup__subtitle');
      let role = roleNode ? roleNode.innerText.trim() : "N/A";

      output += `${name}\t${role}\t${cleanUrl}\n`;
      count++;
    } catch (e) { }
  });

  if (count === 0) return null; // Return null if we filtered everyone out
  return output;
}

// --- VISUAL POPUP FUNCTIONS ---

function showSuccessPopup(message) {
  createPopup(message, "#057642"); // LinkedIn Green
}

function showErrorPopup(message) {
  createPopup(message, "#cc1016"); // Red
}

function createPopup(text, color) {
  const existing = document.getElementById("linkedin-scraper-popup");
  if (existing) existing.remove();

  const popup = document.createElement("div");
  popup.id = "linkedin-scraper-popup";
  popup.innerText = text;
  
  popup.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background-color: ${color};
    color: white;
    padding: 15px 30px;
    border-radius: 50px;
    font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
    font-weight: bold;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    z-index: 10000;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s ease-in-out, top 0.3s ease-in-out;
  `;

  document.body.appendChild(popup);

  requestAnimationFrame(() => {
    popup.style.opacity = "1";
    popup.style.top = "40px";
  });

  setTimeout(() => {
    popup.style.opacity = "0";
    popup.style.top = "20px";
    setTimeout(() => popup.remove(), 300);
  }, 3000);
}
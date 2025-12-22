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
 * Tries the modern API first. If that fails (due to focus), falls back to the old method.
 */
function copyToClipboard(text) {
  // Method 1: Modern API
  navigator.clipboard.writeText(text).then(() => {
    // Success
    showSuccessPopup("✅ Copied " + (text.split('\n').length - 2) + " profiles!");
  }).catch(err => {
    // Method 2: Fallback for "Document is not focused" errors
    console.warn("Modern copy failed, trying fallback...", err);
    try {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      
      // Ensure it's not visible but part of the DOM
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
      console.error("Fallback failed", fallbackErr);
      showErrorPopup("❌ Could not copy text.");
    }
  });
}

function scrapePeopleTabOnly() {
  const cards = document.querySelectorAll('.org-people-profile-card__profile-info');
  if (cards.length === 0) return null;

  let output = "Name\tRole\tUrl\n"; 

  cards.forEach(card => {
    try {
      // Exclusion: Skip "People you may know"
      const parentCard = card.closest('.artdeco-card');
      if (parentCard) {
        const header = parentCard.querySelector('h2');
        if (header && header.innerText.toLowerCase().includes('people you may know')) {
          return; 
        }
      }

      // Name
      const nameNode = card.querySelector('.artdeco-entity-lockup__title');
      if (!nameNode) return;
      let name = nameNode.innerText.trim().split('\n')[0];

      // Role
      const roleNode = card.querySelector('.artdeco-entity-lockup__subtitle');
      let role = roleNode ? roleNode.innerText.trim() : "N/A";

      // URL
      const anchor = card.querySelector('a');
      let cleanUrl = anchor && anchor.href ? anchor.href.split('?')[0] : "N/A";

      output += `${name}\t${role}\t${cleanUrl}\n`;
    } catch (e) { }
  });

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
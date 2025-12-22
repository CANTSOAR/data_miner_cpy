document.getElementById("scrapeBtn").addEventListener("click", async () => {
  let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  // Send message to content.js instead of injecting code
  chrome.tabs.sendMessage(tab.id, {action: "scrape"});
  window.close(); // Close the popup automatically
});
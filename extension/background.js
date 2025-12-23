chrome.commands.onCommand.addListener((command) => {
  console.log("Command received:", command); // Debug log

  if (command === "run-scrape") {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      if (tabs.length === 0) {
        console.log("No active tab found.");
        return;
      }
      
      console.log("Sending message to tab:", tabs[0].id);
      
      // Send the message to the content script
      chrome.tabs.sendMessage(tabs[0].id, {action: "scrape"}, (response) => {
        // Check for connection errors (e.g., if content script isn't loaded)
        if (chrome.runtime.lastError) {
          console.error("Connection error:", chrome.runtime.lastError.message);
          console.log("Did you refresh the LinkedIn page?");
        } else {
          console.log("Response from content script:", response);
        }
      });
    });
  }
});
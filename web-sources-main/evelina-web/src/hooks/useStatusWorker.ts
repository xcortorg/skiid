let isRunning = false;
let intervalId: number | null = null;

async function fetchAndStoreData() {
  if (isRunning) return;
  
  try {
    isRunning = true;
    
    const response = await fetch('/api/history');
    if (!response.ok) throw new Error('Failed to fetch history data');
    
    const historyData = await response.json();
    if (!Array.isArray(historyData) || historyData.length === 0) {
      throw new Error('Invalid history data format');
    }

    // Get the latest data point
    const latestData = historyData[historyData.length - 1];

    // Store in database
  } catch (error) {
    console.error('Error in status worker:', error);
    self.postMessage({ 
      type: 'dataUpdated', 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error' 
    });
  } finally {
    isRunning = false;
  }
}

// Handle messages from main thread
self.addEventListener('message', (event) => {
  if (event.data === 'start') {
    // Initial fetch
    fetchAndStoreData();
    
    // Set up hourly interval
    if (!intervalId) {
      intervalId = self.setInterval(fetchAndStoreData, 60 * 60 * 1000); // Every hour
    }
    
    // Store interval ID
    self.postMessage({ type: 'intervalStarted', intervalId });
  } else if (event.data === 'stop' && intervalId) {
    self.clearInterval(intervalId);
    intervalId = null;
  }
});
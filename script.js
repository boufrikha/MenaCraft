function runVerification() {
    const file = document.getElementById('fileInput').value;
    const claim = document.getElementById('claimInput').value;
    const scoreThreshold = parseInt(document.getElementById('scoreInput').value) || 50;
    const resultBox = document.getElementById('resultBox');

    // Basic check: did they provide input?
    if (!file || !claim) {
        alert("Please upload a file and provide a claim first!");
        return;
    }

    // Show the result box
    resultBox.classList.remove('hidden');

    // Simulate AI verification (in real app, this would call an API)
    const confidence = Math.floor(Math.random() * 100) + 1; // Random score for demo
    const status = confidence >= scoreThreshold ? "Verified" : "Suspicious";
    const reasoning = status === "Verified" 
        ? "Content authenticity and claim context match within acceptable parameters."
        : "Potential discrepancies detected in content authenticity or contextual claims.";

    // Update the HTML with results
    document.getElementById('statusBadge').innerText = "Status: " + status;
    document.getElementById('statusBadge').style.color = status === "Verified" ? "#4CAF50" : "#d9534f";
    document.getElementById('confidenceScore').innerText = confidence + "% Confidence";
    document.getElementById('reasoningText').innerText = reasoning;
    
    // Add the CSS class for styling
    resultBox.className = "result-card " + (status === "Verified" ? "verified" : "suspicious");
}
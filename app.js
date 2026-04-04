async function runVerification() {
    const fileInput = document.getElementById('fileInput');
    const claim = document.getElementById('claimInput').value;
    const url = document.getElementById('urlInput').value;
    const resultBox = document.getElementById('resultBox');

    // Basic check: did they provide any input?
    if (!fileInput.files.length && !claim.trim() && !url.trim()) {
        alert("Please provide at least one input: file, claim, or URL!");
        return;
    }

    // Show the result box
    resultBox.classList.remove('hidden');

    // Prepare form data
    const formData = new FormData();
    for (let i = 0; i < fileInput.files.length; i++) {
        formData.append('files', fileInput.files[i]);
    }
    formData.append('claim', claim);
    formData.append('url', url);

    try {
        // Send request to the backend
        const response = await fetch('/verify', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();

        // Update the HTML with results
        document.getElementById('statusBadge').innerText = "Status: " + data.status;
        const statusColor = data.status === "Publié" ? "#4CAF50" : data.status === "IA généré" ? "#ff4d4d" : data.status === "Suspect" ? "#f0ad4e" : "#ffffff";
        document.getElementById('statusBadge').style.color = statusColor;
        document.getElementById('contentNature').innerText = data.nature || 'Inconnue';
        document.getElementById('internetExists').innerText = data.exists_on_internet ? 'Oui' : 'Non';
        document.getElementById('reasoningText').innerText = data.message || 'Aucun message fourni.';

        if (data.source_url) {
            const sourceLink = document.getElementById('sourceLink');
            sourceLink.innerText = data.source_url;
            sourceLink.href = data.source_url.startsWith('http') ? data.source_url : '#';
        } else {
            const sourceLink = document.getElementById('sourceLink');
            sourceLink.innerText = 'Aucune source trouvée';
            sourceLink.href = '#';
        }

        resultBox.className = "result-card " + (data.status === "Publié" || data.status === "Vérifié" ? "verified" : "suspicious");

    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while verifying the content. Please try again.');
        resultBox.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const verifyButton = document.getElementById('verifyButton');
    if (verifyButton) {
        verifyButton.addEventListener('click', runVerification);
    }
});
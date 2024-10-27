function shareChart(chartType, fileId) {
    fetch(`/analytics/share_chart/${fileId}/${chartType}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken // Ensure this is correctly defined
        },
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const shareUrl = `http://127.0.0.1:8000/analytics/shared_charts/${fileId}/${chartType}/`; // Constructed link
            alert(`Share link: ${shareUrl}`);
        } else {
            alert('Error generating share link: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        alert('An error occurred while sharing the chart: ' + error.message);
    });
}
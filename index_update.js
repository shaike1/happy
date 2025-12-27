// Add after loadPushTokens function

// Load network connections with IPs
async function loadConnections() {
    const container = document.getElementById("connections-content");
    if (!container) {
        // Add the section if it doesnt exist
        const overview = document.getElementById("overview");
        const section = document.createElement("div");
        section.className = "section";
        section.innerHTML = `
            <div class="section-title">🌐 Network Connections (Live IPs)</div>
            <div id="connections-content" class="loading">Loading...</div>
        `;
        overview.appendChild(section);
    }

    const connContainer = document.getElementById("connections-content");
    
    try {
        const response = await fetch("/api/connections");
        const data = await response.json();

        if (data.connections && data.connections.length === 0) {
            connContainer.innerHTML = "<div class=\"empty-state\">No active connections</div>";
            return;
        }

        let html = "<table><thead><tr><th>Remote IP</th><th>Remote Port</th><th>Local Port</th><th>Status</th><th>Location</th></tr></thead><tbody>";

        for (const conn of data.connections) {
            html += `<tr>
                <td><code>${conn.remote_ip}</code></td>
                <td>${conn.remote_port}</td>
                <td>${conn.local_port}</td>
                <td><span class="badge active">${conn.status}</span></td>
                <td class="timestamp" id="loc-${conn.remote_ip.replace(/\./g, "-")}">Loading...</td>
            </tr>`;
        }

        html += "</tbody></table>";
        connContainer.innerHTML = html;

        // Fetch location for each unique IP
        for (const ip of data.unique_ips) {
            fetchIPLocation(ip);
        }
    } catch (error) {
        connContainer.innerHTML = "<div class=\"error\">Error loading connections: " + error.message + "</div>";
    }
}

async function fetchIPLocation(ip) {
    try {
        const response = await fetch(`/api/ip-info/${ip}`);
        const data = await response.json();
        
        const elementId = "loc-" + ip.replace(/\./g, "-");
        const element = document.getElementById(elementId);
        
        if (element && data.city) {
            const location = `${data.city}, ${data.country} (${data.org || "Unknown"})`;
            element.textContent = location;
        } else if (element) {
            element.textContent = ip;
        }
    } catch (error) {
        console.error("Error fetching location for", ip, error);
    }
}

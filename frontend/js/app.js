const API_BASE = "";
let ws = null;
let autoRefreshTimer = null;
let countdownTimer = null;
let countdownValue = 0;
let previousPrices = {};

function toggleMobileMenu() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    const toggle = document.getElementById("mobile-menu-toggle");
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
    toggle.classList.toggle("active");
}

function closeMobileMenu() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    const toggle = document.getElementById("mobile-menu-toggle");
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    toggle.classList.remove("active");
}

function showSection(section) {
    closeMobileMenu();
    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

    const sectionEl = document.getElementById(`${section}-section`);
    if (sectionEl) sectionEl.classList.add("active");

    const navItem = document.querySelector(`[onclick="showSection('${section}')"]`);
    if (navItem) navItem.classList.add("active");

    document.getElementById("page-title").textContent = {
        dashboard: "Dashboard",
        watchlist: "Kelola Watchlist",
        analysis: "Analisis Saham",
        financial: "Financial Data",
        backtest: "Backtesting",
        alerts: "Alert System",
        monitor: "Live Monitor",
        notifications: "Notifications",
        horizon: "Horizon Analysis",
        reports: "Reports"
    }[section];

    if (section === "monitor") refreshMonitorStatus();
    if (section === "notifications") loadNotificationStatus();
    if (section === "watchlist") loadWatchlistManager();
    if (section === "financial") loadAllFinancialData();
}

async function fetchJSON(url) {
    const res = await fetch(API_BASE + url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

function formatRupiah(num) {
    if (!num) return "N/A";
    return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

function formatNumber(num) {
    if (!num) return "N/A";
    return new Intl.NumberFormat("id-ID").format(num);
}

function formatLargeNumber(num) {
    if (num == null) return "N/A";
    const abs = Math.abs(num);
    const sign = num < 0 ? "-" : "";
    if (abs >= 1e12) return sign + "Rp " + (abs / 1e12).toFixed(2) + " T";
    if (abs >= 1e9) return sign + "Rp " + (abs / 1e9).toFixed(2) + " M";
    if (abs >= 1e6) return sign + "Rp " + (abs / 1e6).toFixed(0) + " Jt";
    if (abs >= 1e3) return sign + "Rp " + (abs / 1e3).toFixed(0) + " Rb";
    return sign + "Rp " + abs.toFixed(0);
}

function signalClass(signal) {
    if (!signal) return "signal-hold";
    if (signal.includes("BUY")) return "signal-buy";
    if (signal.includes("SELL")) return "signal-sell";
    return "signal-hold";
}

function showToast(title, message, isAlert = false) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${isAlert ? "alert-toast" : ""}`;
    toast.innerHTML = `
        <div class="toast-title">${title}</div>
        <div class="toast-msg">${message}</div>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

function addLog(msg, isAlert = false) {
    const log = document.getElementById("monitor-log");
    if (!log) return;
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement("div");
    entry.className = `log-entry ${isAlert ? "alert" : ""}`;
    entry.innerHTML = `<span class="time">[${time}]</span> <span class="msg">${msg}</span>`;
    log.prepend(entry);
    if (log.children.length > 50) log.lastChild.remove();
}

// WebSocket
function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        updateWSStatus(true);
        ws.send(JSON.stringify({ type: "ping" }));
        getWatchlistSymbols().then(symbols => {
            ws.send(JSON.stringify({ type: "subscribe", symbols }));
        });
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
    };

    ws.onclose = () => {
        updateWSStatus(false);
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = () => {
        updateWSStatus(false);
    };
}

function updateWSStatus(connected) {
    const el = document.getElementById("ws-status");
    if (connected) {
        el.className = "ws-status ws-connected";
        el.innerHTML = '<span class="dot"></span> Connected';
    } else {
        el.className = "ws-status ws-disconnected";
        el.innerHTML = '<span class="dot"></span> Disconnected';
    }
}

function handleWSMessage(msg) {
    switch (msg.type) {
        case "price_update":
            updateLivePrices(msg.data);
            break;
        case "alert_triggered":
            msg.data.forEach(alert => {
                showToast(
                    `Alert: ${alert.symbol}`,
                    `${alert.alert_type} | Target: ${formatRupiah(alert.target_value)} | Current: ${formatRupiah(alert.current_price)}`,
                    true
                );
                addLog(`ALERT TRIGGERED: ${alert.symbol} ${alert.alert_type} Target:${alert.target_value} Current:${alert.current_price}`, true);
            });
            break;
        case "initial_prices":
            updateLivePrices(msg.data);
            break;
        case "pong":
            break;
    }
}

function getWatchlistSymbols() {
    return fetch(API_BASE + "/api/watchlist")
        .then(r => r.json())
        .then(data => data.watchlist.map(i => i.symbol))
        .catch(() => ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"]);
}

function updateLivePrices(prices) {
    Object.entries(prices).forEach(([symbol, price]) => {
        const cards = document.querySelectorAll(`[data-symbol="${symbol}"]`);
        cards.forEach(card => {
            const priceEl = card.querySelector(".price");
            if (priceEl) {
                const oldPrice = previousPrices[symbol] || price;
                priceEl.textContent = formatRupiah(price);

                card.classList.remove("price-flash-up", "price-flash-down");
                if (price > oldPrice) {
                    card.classList.add("price-flash-up");
                } else if (price < oldPrice) {
                    card.classList.add("price-flash-down");
                }
            }
        });
        previousPrices[symbol] = price;
    });

    const liveContainer = document.getElementById("live-prices");
    if (liveContainer && Object.keys(prices).length > 0) {
        let html = "";
        Object.entries(prices).forEach(([symbol, price]) => {
            html += `
                <div class="stock-card" data-symbol="${symbol}" onclick="showStockDetail('${symbol}')">
                    <h3>${symbol}</h3>
                    <p class="price">${formatRupiah(price)}</p>
                </div>
            `;
        });
        liveContainer.innerHTML = html;
    }
}

// Auto-refresh
function setAutoRefresh() {
    clearInterval(autoRefreshTimer);
    clearInterval(countdownTimer);

    const interval = parseInt(document.getElementById("refresh-interval").value);
    const countdownEl = document.getElementById("refresh-countdown");

    if (interval === 0) {
        countdownEl.textContent = "";
        return;
    }

    countdownValue = interval;
    countdownEl.textContent = `${countdownValue}s`;

    countdownTimer = setInterval(() => {
        countdownValue--;
        countdownEl.textContent = `${countdownValue}s`;
        if (countdownValue <= 0) countdownValue = interval;
    }, 1000);

    autoRefreshTimer = setInterval(() => {
        refreshDashboard();
        countdownValue = interval;
    }, interval * 1000);
}

async function refreshDashboard() {
    try {
        const data = await fetchJSON("/api/market");
        document.getElementById("ihsg-value").textContent = formatNumber(data.ihsg);
        const changeEl = document.getElementById("ihsg-change");
        changeEl.textContent = `${data.change >= 0 ? "+" : ""}${data.change} (${data.change_pct}%)`;
        changeEl.className = `value ${data.change >= 0 ? "value-positive" : "value-negative"}`;
    } catch (e) {
        console.error("Refresh error:", e);
    }
}

// Monitor
async function startMonitor() {
    const interval = document.getElementById("monitor-interval").value;
    try {
        await fetch(API_BASE + "/api/monitor/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ interval: parseInt(interval) }),
        });
        document.getElementById("monitor-status").textContent = "RUNNING";
        document.getElementById("monitor-status").className = "status-badge status-on";
        addLog(`Monitor started with ${interval}s interval`);
    } catch (e) {
        addLog(`Error starting monitor: ${e.message}`, true);
    }
}

async function stopMonitor() {
    try {
        await fetch(API_BASE + "/api/monitor/stop", { method: "POST" });
        document.getElementById("monitor-status").textContent = "STOPPED";
        document.getElementById("monitor-status").className = "status-badge status-off";
        addLog("Monitor stopped");
    } catch (e) {
        addLog(`Error stopping monitor: ${e.message}`, true);
    }
}

async function refreshMonitorStatus() {
    try {
        const data = await fetchJSON("/api/monitor/status");
        document.getElementById("monitor-status").textContent = data.running ? "RUNNING" : "STOPPED";
        document.getElementById("monitor-status").className = `status-badge ${data.running ? "status-on" : "status-off"}`;
        document.getElementById("monitor-interval").value = data.interval;
    } catch (e) {
        console.error("Error:", e);
    }
}

// Notifications
async function loadNotificationStatus() {
    try {
        const data = await fetchJSON("/api/notifications/status");
        document.getElementById("email-status").innerHTML = data.email.enabled
            ? '<span class="value-positive">Enabled</span>'
            : '<span class="value-negative">Disabled</span>';
        document.getElementById("telegram-status").innerHTML = data.telegram.enabled
            ? '<span class="value-positive">Enabled</span>'
            : '<span class="value-negative">Disabled</span>';
    } catch (e) {
        console.error("Error:", e);
    }
}

async function testEmail() {
    const email = document.getElementById("email-address").value;
    if (!email) return alert("Masukkan email");
    try {
        const res = await fetch(API_BASE + "/api/notifications/test-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email }),
        });
        const data = await res.json();
        alert(data.status === "sent" ? "Email terkirim!" : `Error: ${data.message || data.reason}`);
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function testTelegram() {
    try {
        const res = await fetch(API_BASE + "/api/notifications/test-telegram", { method: "POST" });
        const data = await res.json();
        alert(data.status === "sent" ? "Telegram terkirim!" : `Error: ${data.message || data.reason}`);
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// Stock Analysis
async function analyzeStock() {
    const symbol = document.getElementById("global-search").value.trim().toUpperCase();
    if (!symbol) return;

    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    document.getElementById("analysis-section").classList.add("active");

    document.getElementById("page-title").textContent = "Analisis Saham";

    const container = document.getElementById("analysis-result");
    container.innerHTML = "<p class='placeholder'>Loading analysis...</p>";

    try {
        const data = await fetchJSON(`/api/stock/${symbol}`);
        renderAnalysis(data);
    } catch (e) {
        container.innerHTML = `<p class="placeholder">Error: ${e.message}</p>`;
    }
}

function renderAnalysis(data) {
    const tech = data.technical;
    const fund = data.fundamental;
    const sent = data.sentiment;

    const container = document.getElementById("analysis-result");
    container.innerHTML = `
        <div class="analysis-card full-width">
            <h3>${data.symbol} - ${fund?.name || data.symbol}</h3>
            <div style="display:flex;gap:20px;align-items:center">
                <span class="price" style="font-size:2rem">${formatRupiah(tech.current_price)}</span>
                <span class="signal ${signalClass(tech.overall_signal)}" style="font-size:1.2rem">${tech.overall_signal}</span>
            </div>
            <p style="margin-top:10px;color:#888">Sektor: ${fund?.sector || "N/A"} | Market Cap: ${fund?.market_cap_category || "N/A"}</p>
        </div>

        <div class="analysis-card">
            <h3>Technical Analysis</h3>
            <div class="indicator-row">
                <span class="indicator-label">RSI (14)</span>
                <span class="indicator-value ${tech.rsi < 30 ? 'value-positive' : tech.rsi > 70 ? 'value-negative' : 'value-neutral'}">${tech.rsi}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">MACD</span>
                <span class="indicator-value">${tech.macd?.macd}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Signal Line</span>
                <span class="indicator-value">${tech.macd?.signal}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Bollinger Upper</span>
                <span class="indicator-value">${tech.bollinger?.upper}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Bollinger Middle</span>
                <span class="indicator-value">${tech.bollinger?.middle}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Bollinger Lower</span>
                <span class="indicator-value">${tech.bollinger?.lower}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">MA 7</span>
                <span class="indicator-value">${tech.moving_averages?.ma7 || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">MA 20</span>
                <span class="indicator-value">${tech.moving_averages?.ma20 || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">MA 50</span>
                <span class="indicator-value">${tech.moving_averages?.ma50 || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">ATR</span>
                <span class="indicator-value">${tech.atr || "N/A"}</span>
            </div>
            <h4 style="margin-top:20px;color:#4ecca3">Trading Signals</h4>
            <ul class="signal-list">
                ${tech.signals?.map(s => `
                    <li>
                        <span>${s.indicator}: ${s.signal}</span>
                        <span class="signal ${signalClass(s.recommendation)}">${s.recommendation}</span>
                    </li>
                `).join("") || ""}
            </ul>
        </div>

        <div class="analysis-card">
            <h3>Fundamental Analysis</h3>
            ${fund?.report_info?.period ? `
                <div style="margin-bottom:15px;padding:8px 12px;background:#0f3460;border-left:3px solid #4ecca3;border-radius:4px;font-size:0.85rem">
                    <span style="color:#4ecca3;font-weight:bold">${fund.report_info.period}</span>
                    <span style="color:#888"> — ${fund.report_info.type || "Laporan Keuangan"}</span>
                    ${fund.report_info.updated_at ? `<span style="color:#555;display:block;margin-top:3px;font-size:0.8rem">Updated: ${fund.report_info.updated_at}</span>` : ""}
                    ${fund.report_info.available_periods?.length > 1 ? `
                        <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">
                            ${fund.report_info.available_periods.map(p => `
                                <span style="padding:2px 8px;background:#16213e;border-radius:3px;font-size:0.75rem;color:#aaa">${p.period} <span style="color:#666">(${p.type?.split(" ")[0] || ""})</span></span>
                            `).join("")}
                        </div>
                    ` : ""}
                </div>
            ` : ""}
            ${fund?.revenue != null ? `
            <div class="indicator-row">
                <span class="indicator-label">Revenue</span>
                <span class="indicator-value">${formatLargeNumber(fund.revenue)}</span>
            </div>
            ` : ""}
            ${fund?.net_profit != null ? `
            <div class="indicator-row">
                <span class="indicator-label">Net Profit</span>
                <span class="indicator-value ${fund.net_profit < 0 ? 'value-negative' : 'value-positive'}">${formatLargeNumber(fund.net_profit)}</span>
            </div>
            ` : ""}
            ${fund?.gross_margin != null ? `
            <div class="indicator-row">
                <span class="indicator-label">Gross Margin</span>
                <span class="indicator-value">${fund.gross_margin}%</span>
            </div>
            ` : ""}
            <div class="indicator-row">
                <span class="indicator-label">PE Ratio</span>
                <span class="indicator-value">${fund?.valuation?.details?.[0]?.value || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">PB Ratio</span>
                <span class="indicator-value">${fund?.valuation?.details?.[1]?.value || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">ROE</span>
                <span class="indicator-value">${fund?.quality?.details?.[0]?.value || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Profit Margin</span>
                <span class="indicator-value">${fund?.quality?.details?.[1]?.value || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Debt/Equity</span>
                <span class="indicator-value">${fund?.financial_health?.details?.[0]?.value || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Dividend</span>
                <span class="indicator-value">${fund?.dividend?.value || "N/A"} ${fund?.dividend?.status || ""}</span>
            </div>
            <p style="margin-top:15px;padding:10px;background:#16213e;border-radius:5px">
                <strong>Score:</strong> ${fund?.total_score} | <strong>Rekomendasi:</strong> ${fund?.recommendation}
            </p>
        </div>

        <div class="analysis-card">
            <h3>Sentiment Analysis</h3>
            <div class="indicator-row">
                <span class="indicator-label">Overall Sentiment</span>
                <span class="indicator-value ${sent?.overall_sentiment?.includes('BULLISH') ? 'value-positive' : sent?.overall_sentiment?.includes('BEARISH') ? 'value-neutral' : ''}">${sent?.overall_sentiment || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Score</span>
                <span class="indicator-value">${sent?.sentiment_score || "N/A"}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">News Analyzed</span>
                <span class="indicator-value">${sent?.news_count || 0}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Positive</span>
                <span class="indicator-value value-positive">${sent?.positive_count || 0}</span>
            </div>
            <div class="indicator-row">
                <span class="indicator-label">Negative</span>
                <span class="indicator-value value-negative">${sent?.negative_count || 0}</span>
            </div>
            ${sent?.news?.length > 0 ? `
                <h4 style="margin-top:15px;color:#4ecca3">Berita Terbaru</h4>
                ${sent.news.map(n => `
                    <div style="padding:10px;margin:5px 0;background:#16213e;border-radius:5px">
                        <p style="font-weight:bold">${n.title}</p>
                        <p style="font-size:0.85rem;color:#888">${n.snippet?.substring(0, 100)}...</p>
                        <span class="signal ${signalClass(n.sentiment_label === 'POSITIVE' ? 'BUY' : n.sentiment_label === 'NEGATIVE' ? 'SELL' : 'HOLD')}" style="font-size:0.75rem">${n.sentiment_label}</span>
                    </div>
                `).join("")}
            ` : ""}
        </div>

        <div class="analysis-card full-width">
            <h3>Price Chart</h3>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
    `;

    if (tech.chart_data && tech.chart_data.length > 0) {
        renderChart(tech.chart_data);
    }
}

function renderChart(chartData) {
    const ctx = document.getElementById("priceChart").getContext("2d");
    const labels = chartData.map(d => d.date);
    const prices = chartData.map(d => d.close);
    const ma20 = chartData.map(d => d.ma20);
    const upperBB = chartData.map(d => d.upper_bb);
    const lowerBB = chartData.map(d => d.lower_bb);

    new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "Price", data: prices, borderColor: "#4ecca3", borderWidth: 2, fill: false, pointRadius: 0 },
                { label: "MA 20", data: ma20, borderColor: "#e94560", borderWidth: 1, fill: false, pointRadius: 0 },
                { label: "BB Upper", data: upperBB, borderColor: "#666", borderWidth: 1, borderDash: [5, 5], fill: false, pointRadius: 0 },
                { label: "BB Lower", data: lowerBB, borderColor: "#666", borderWidth: 1, borderDash: [5, 5], fill: false, pointRadius: 0 },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: "#ccc" } } },
            scales: {
                x: { ticks: { color: "#888", maxTicksLimit: 10 }, grid: { color: "#222" } },
                y: { ticks: { color: "#888" }, grid: { color: "#222" } },
            },
        },
    });
}

function showStockDetail(symbol) {
    document.getElementById("global-search").value = symbol;
    analyzeStock();
}

// Backtest
async function runBacktest() {
    const symbol = document.getElementById("bt-symbol").value.trim().toUpperCase();
    const strategy = document.getElementById("bt-strategy").value;
    const capital = document.getElementById("bt-capital").value;
    if (!symbol) return;

    const container = document.getElementById("backtest-result");
    container.innerHTML = "<p>Running backtest...</p>";

    try {
        const data = await fetchJSON(`/api/backtest/${symbol}?strategy=${strategy}&capital=${capital}`);
        renderBacktest(data);
    } catch (e) {
        container.innerHTML = `<p>Error: ${e.message}</p>`;
    }
}

function renderBacktest(data) {
    const container = document.getElementById("backtest-result");
    let html = `
        <div class="backtest-result">
            <h3>Backtest Results: ${data.symbol}</h3>
            <p style="color:#4ecca3;margin-bottom:20px">Best Strategy: ${data.best_strategy} | Return: ${data.best_return}%</p>
            ${data.strategies.map(s => `
                <div class="strategy-card">
                    <h4>${s.strategy}</h4>
                    <div class="stat-grid">
                        <div class="stat-box"><div class="label">Modal Awal</div><div class="value">${formatRupiah(s.initial_capital)}</div></div>
                        <div class="stat-box"><div class="label">Modal Akhir</div><div class="value">${formatRupiah(s.final_equity)}</div></div>
                        <div class="stat-box"><div class="label">Return</div><div class="value ${s.total_return_pct >= 0 ? 'value-positive' : 'value-negative'}">${s.total_return_pct}%</div></div>
                        <div class="stat-box"><div class="label">Win Rate</div><div class="value">${s.win_rate}%</div></div>
                    </div>
                    <div class="chart-container" style="height:200px;margin-top:15px">
                        <canvas id="eq-${s.strategy.replace(/\s/g, '')}"></canvas>
                    </div>
                </div>
            `).join("")}
        </div>
    `;
    container.innerHTML = html;

    data.strategies.forEach(s => {
        if (s.equity_curve && s.equity_curve.length > 0) {
            const ctx = document.getElementById(`eq-${s.strategy.replace(/\s/g, "")}`);
            if (ctx) {
                new Chart(ctx.getContext("2d"), {
                    type: "line",
                    data: {
                        labels: s.equity_curve.map(d => d.date),
                        datasets: [{
                            label: "Equity", data: s.equity_curve.map(d => d.equity),
                            borderColor: "#4ecca3", borderWidth: 2, fill: true,
                            backgroundColor: "rgba(78, 204, 163, 0.1)", pointRadius: 0,
                        }],
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { display: false },
                            y: { ticks: { color: "#888" }, grid: { color: "#222" } },
                        },
                    },
                });
            }
        }
    });
}

// Alerts
async function createAlert() {
    const symbol = document.getElementById("alert-symbol").value.trim().toUpperCase();
    const alertType = document.getElementById("alert-type").value;
    const value = parseFloat(document.getElementById("alert-value").value);
    if (!symbol || !value) return;

    try {
        await fetch(API_BASE + "/api/alerts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, alert_type: alertType, target_value: value }),
        });
        showToast("Alert Created", `${symbol} ${alertType} at ${formatRupiah(value)}`);
        loadAlerts();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function loadAlerts() {
    try {
        const active = await fetchJSON("/api/alerts");
        const triggered = await fetchJSON("/api/alerts/triggered");

        document.getElementById("active-alerts").innerHTML = active.length === 0
            ? "<p style='color:#888'>Tidak ada alert aktif</p>"
            : active.map(a => `
                <div class="alert-item">
                    <span>${a.symbol} - ${a.alert_type} - Target: ${formatRupiah(a.target_value)}</span>
                    <button class="btn" style="background:#e94560;color:white" onclick="deleteAlert(${a.id})">Hapus</button>
                </div>
            `).join("");

        document.getElementById("triggered-alerts").innerHTML = triggered.length === 0
            ? "<p style='color:#888'>Belum ada alert yang ter-trigger</p>"
            : triggered.map(a => `
                <div class="alert-item triggered">
                    <span>${a.symbol} - ${a.alert_type} - Target: ${formatRupiah(a.target_value)}</span>
                    <span style="color:#e94560">Triggered at ${a.triggered_at}</span>
                </div>
            `).join("");
    } catch (e) {
        console.error("Error loading alerts:", e);
    }
}

async function deleteAlert(id) {
    try {
        await fetch(API_BASE + `/api/alerts/${id}`, { method: "DELETE" });
        loadAlerts();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

// Reports
async function generateReport() {
    const symbols = document.getElementById("report-symbols").value.trim();
    if (!symbols) return;

    const container = document.getElementById("report-result");
    container.innerHTML = "<p>Generating report...</p>";

    try {
        const data = await fetchJSON(`/api/report?symbols=${symbols}`);
        container.innerHTML = `
            <div class="report-card">
                <h3>Report Generated</h3>
                <p>Report berhasil dibuat pada ${data.report.report_date}</p>
                <p><strong>HTML Report:</strong> ${data.report.html_report}</p>
                <p><strong>JSON Report:</strong> ${data.report.json_report}</p>
                <h4 style="margin-top:15px;color:#4ecca3">Summary</h4>
                ${data.summary.map(s => `
                    <div class="indicator-row">
                        <span>${s.symbol} - ${formatRupiah(s.price)}</span>
                        <span class="signal ${signalClass(s.signal)}">${s.signal}</span>
                    </div>
                `).join("")}
            </div>
        `;
    } catch (e) {
        container.innerHTML = `<p>Error: ${e.message}</p>`;
    }
}

// Financial Data Manager
function showAddFinancialForm() {
    document.getElementById("add-financial-form").style.display = "block";
}

function hideAddFinancialForm() {
    document.getElementById("add-financial-form").style.display = "none";
    document.getElementById("fin-symbol").value = "";
}

async function saveFinancialData() {
    const symbol = document.getElementById("fin-symbol").value.trim().toUpperCase();
    if (!symbol) return alert("Masukkan kode saham!");

    const data = {
        symbol: symbol,
        period: document.getElementById("fin-period").value || null,
        revenue: parseFloat(document.getElementById("fin-revenue").value) || null,
        net_profit: parseFloat(document.getElementById("fin-net-profit").value) || null,
        total_assets: parseFloat(document.getElementById("fin-total-assets").value) || null,
        total_equity: parseFloat(document.getElementById("fin-total-equity").value) || null,
        total_debt: parseFloat(document.getElementById("fin-total-debt").value) || null,
        pe_ratio: parseFloat(document.getElementById("fin-pe").value) || null,
        pb_ratio: parseFloat(document.getElementById("fin-pb").value) || null,
        roe: parseFloat(document.getElementById("fin-roe").value) / 100 || null,
        roa: parseFloat(document.getElementById("fin-roa").value) / 100 || null,
        gross_margin: parseFloat(document.getElementById("fin-gross-margin").value) / 100 || null,
        net_margin: parseFloat(document.getElementById("fin-net-margin").value) / 100 || null,
        debt_to_equity: parseFloat(document.getElementById("fin-de").value) || null,
        dividend_yield: parseFloat(document.getElementById("fin-div").value) / 100 || null,
    };

    try {
        const res = await fetch(API_BASE + "/api/financial/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const result = await res.json();
        showToast("Berhasil", `Data keuangan ${symbol} berhasil disimpan`);
        hideAddFinancialForm();
        loadAllFinancialData();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function quickFetchFinancial() {
    const symbol = document.getElementById("quick-fetch-symbol").value.trim().toUpperCase();
    if (!symbol) return alert("Masukkan kode emiten!");

    const source = document.getElementById("fetch-source").value;
    const resultContainer = document.getElementById("quick-fetch-result");
    resultContainer.innerHTML = `<div class="quick-fetch-loading">Fetching data untuk ${symbol} dari ${source === "auto" ? "sumber terbaik" : source}...</div>`;

    try {
        const res = await fetch(API_BASE + "/api/financial/fetch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, source }),
        });

        const data = await res.json();

        if (!res.ok || !data || data.status === "error") {
            throw new Error(data.detail || data.message || "Gagal mengambil data");
        }

        const d = data.data || {};
        const fmt = (v) => (v != null ? v : "N/A");
        const fmtRp = (v) => (v ? formatRupiah(v) : "N/A");
        const fmtPct = (v) => (v != null ? (v * 100).toFixed(1) + "%" : "N/A");

        const sourceLabel = data.source_label || "Yahoo Finance";
        const sourcesUsed = data.sources_used && data.sources_used.length > 0
            ? data.sources_used.join(", ")
            : sourceLabel;

        resultContainer.innerHTML = `
            <div class="quick-fetch-success">
                <h4 style="color:#4ecca3">Berhasil! Data ${symbol} tersimpan</h4>
                <div style="color:#888;font-size:0.8rem;margin-bottom:10px">Sumber: ${sourcesUsed}</div>
                <div class="quick-fetch-grid">
                    <div class="qf-item"><span class="label">Nama</span><span class="value">${fmt(d.company_name) || symbol}</span></div>
                    <div class="qf-item"><span class="label">Harga</span><span class="value">${fmtRp(d.current_price)}</span></div>
                    <div class="qf-item"><span class="label">Market Cap</span><span class="value">${fmtRp(d.market_cap)}</span></div>
                    <div class="qf-item"><span class="label">PE Ratio</span><span class="value">${fmt(d.pe_ratio)}</span></div>
                    <div class="qf-item"><span class="label">PB Ratio</span><span class="value">${fmt(d.pb_ratio)}</span></div>
                    <div class="qf-item"><span class="label">ROE</span><span class="value">${fmtPct(d.roe)}</span></div>
                    <div class="qf-item"><span class="label">ROA</span><span class="value">${fmtPct(d.roa)}</span></div>
                    <div class="qf-item"><span class="label">Revenue</span><span class="value">${fmtRp(d.revenue)}</span></div>
                    <div class="qf-item"><span class="label">Dividend Yield</span><span class="value">${fmtPct(d.dividend_yield)}</span></div>
                    <div class="qf-item"><span class="label">Debt/Equity</span><span class="value">${fmt(d.debt_to_equity)}</span></div>
                    <div class="qf-item"><span class="label">Target Price</span><span class="value">${fmtRp(d.target_price)}</span></div>
                    <div class="qf-item"><span class="label">Rekomendasi</span><span class="value">${fmt(d.recommendation)}</span></div>
                    <div class="qf-item"><span class="label">52W High</span><span class="value">${fmtRp(d.fifty_two_week_high)}</span></div>
                    <div class="qf-item"><span class="label">52W Low</span><span class="value">${fmtRp(d.fifty_two_week_low)}</span></div>
                    <div class="qf-item"><span class="label">Beta</span><span class="value">${fmt(d.beta)}</span></div>
                </div>
            </div>
        `;
        showToast("Berhasil", `Data keuangan ${symbol} berhasil di-fetch dan disimpan`);
        loadAllFinancialData();
    } catch (e) {
        resultContainer.innerHTML = `<div class="quick-fetch-error">Error: ${e.message}</div>`;
    }
}

async function fetchMultiSource() {
    const symbol = document.getElementById("quick-fetch-symbol").value.trim().toUpperCase();
    if (!symbol) return alert("Masukkan kode emiten!");

    const resultContainer = document.getElementById("quick-fetch-result");
    resultContainer.innerHTML = `<div class="quick-fetch-loading">Fetching data ${symbol} dari SEMUA sumber sekaligus...</div>`;

    try {
        const res = await fetch(API_BASE + "/api/financial/fetch-multi", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol }),
        });

        const data = await res.json();

        if (!res.ok || data.error) {
            throw new Error(data.detail || data.error || "Gagal mengambil data multi-source");
        }

        const bySource = data.by_source || {};
        const sourcesUsed = data.sources_used || [];
        const merged = data.merged_data || {};

        const fmt = (v) => (v != null ? (typeof v === 'number' ? v.toFixed(2) : v) : "N/A");
        const fmtPct = (v) => (v != null ? (v * 100).toFixed(1) + "%" : "N/A");

        let sourceCards = Object.entries(bySource).map(([name, info]) => {
            const metrics = [
                { label: "PE", value: fmt(info.pe_ratio) },
                { label: "PB", value: fmt(info.pb_ratio) },
                { label: "ROE", value: fmtPct(info.roe) },
                { label: "Margin", value: fmtPct(info.net_margin) },
                { label: "D/E", value: fmt(info.debt_to_equity) },
                { label: "Div", value: fmtPct(info.dividend_yield) },
            ];
            const metricsHtml = metrics.map(m =>
                `<span style="margin-right:8px"><b>${m.label}:</b> ${m.value}</span>`
            ).join("");
            return `<div style="background:#16213e;padding:8px 12px;border-radius:6px;margin:4px 0;font-size:0.85rem">
                <b style="color:#4ecca3">${info.source_label || name}</b><br>
                <span style="color:#ccc">${metricsHtml}</span>
            </div>`;
        }).join("");

        resultContainer.innerHTML = `
            <div class="quick-fetch-success">
                <h4 style="color:#4ecca3">Multi-Source Fetch: ${symbol}</h4>
                <div style="color:#888;font-size:0.8rem;margin-bottom:10px">Dari ${sourcesUsed.length} sumber: ${data.source_label}</div>
                <div style="margin-bottom:12px">
                    <b style="color:#eee">Data per Sumber:</b>
                    ${sourceCards || "<p style='color:#888'>Tidak ada data ditemukan</p>"}
                </div>
                <div style="border-top:1px solid #333;padding-top:10px">
                    <b style="color:#eee">Merged Data (Gabungan Terbaik):</b>
                    <div class="quick-fetch-grid">
                        <div class="qf-item"><span class="label">Nama</span><span class="value">${merged.company_name || symbol}</span></div>
                        <div class="qf-item"><span class="label">Harga</span><span class="value">${merged.current_price ? formatRupiah(merged.current_price) : "N/A"}</span></div>
                        <div class="qf-item"><span class="label">PE Ratio</span><span class="value">${fmt(merged.pe_ratio)}</span></div>
                        <div class="qf-item"><span class="label">PB Ratio</span><span class="value">${fmt(merged.pb_ratio)}</span></div>
                        <div class="qf-item"><span class="label">ROE</span><span class="value">${fmtPct(merged.roe)}</span></div>
                        <div class="qf-item"><span class="label">Net Margin</span><span class="value">${fmtPct(merged.net_margin)}</span></div>
                        <div class="qf-item"><span class="label">Debt/Equity</span><span class="value">${fmt(merged.debt_to_equity)}</span></div>
                        <div class="qf-item"><span class="label">Dividend Yield</span><span class="value">${fmtPct(merged.dividend_yield)}</span></div>
                    </div>
                </div>
            </div>
        `;

        showToast("Berhasil", `Multi-source fetch ${symbol} selesai - ${sourcesUsed.length} sumber ditemukan`);
        loadAllFinancialData();
    } catch (e) {
        resultContainer.innerHTML = `<div class="quick-fetch-error">Error: ${e.message}</div>`;
    }
}

async function loadAllFinancialData() {
    const container = document.getElementById("financial-list");
    const historyContainer = document.getElementById("financial-history");

    container.innerHTML = "<p style='color:#888'>Loading financial data...</p>";

    try {
        const data = await fetchJSON("/api/financial");
        const stocks = data.stocks || [];

        if (stocks.length === 0) {
            container.innerHTML = `
                <div class="wl-empty">
                    <h3>Belum Ada Data Keuangan</h3>
                    <p>Klik "+ Tambah Manual" untuk menambahkan data keuangan emiten</p>
                </div>
            `;
        } else {
            container.innerHTML = stocks.map(s => `
                <div class="fin-item">
                    <div class="fin-header">
                        <span class="fin-symbol">${s.symbol}</span>
                        <span class="fin-period">${s.period || "N/A"}</span>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Revenue</div>
                        <div class="value">${s.revenue ? formatRupiah(s.revenue * 1000000000) : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Net Profit</div>
                        <div class="value">${s.net_profit ? formatRupiah(s.net_profit * 1000000000) : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">PE Ratio</div>
                        <div class="value">${s.pe_ratio || "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">PB Ratio</div>
                        <div class="value">${s.pb_ratio || "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">ROE</div>
                        <div class="value">${s.roe ? (s.roe * 100).toFixed(1) + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">ROA</div>
                        <div class="value">${s.roa ? (s.roa * 100).toFixed(1) + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Gross Margin</div>
                        <div class="value">${s.gross_margin ? (s.gross_margin * 100).toFixed(1) + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Net Margin</div>
                        <div class="value">${s.net_margin ? (s.net_margin * 100).toFixed(1) + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Debt/Equity</div>
                        <div class="value">${s.debt_to_equity ? s.debt_to_equity + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Dividend Yield</div>
                        <div class="value">${s.dividend_yield ? (s.dividend_yield * 100).toFixed(1) + "%" : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Updated</div>
                        <div class="value" style="font-size:0.75rem">${s.updated_at ? new Date(s.updated_at).toLocaleDateString() : "N/A"}</div>
                    </div>
                    <div class="fin-metric">
                        <div class="label">Source</div>
                        <div class="value" style="font-size:0.75rem;color:#4ecca3">${s.source || "N/A"}</div>
                    </div>
                </div>
            `).join("");
        }

        const history = await fetchJSON("/api/financial/history?limit=20");
        const histList = history.history || [];
        if (histList.length === 0) {
            historyContainer.innerHTML = "<p style='color:#888'>Belum ada riwayat update</p>";
        } else {
            historyContainer.innerHTML = histList.map(h => `
                <div class="fin-history-item">
                    <span><strong>${h.symbol}</strong> - ${h.message}</span>
                    <span style="color:#888">${new Date(h.updated_at).toLocaleString()}</span>
                    <span class="status ${h.status}">${h.status.toUpperCase()}</span>
                </div>
            `).join("");
        }
    } catch (e) {
        container.innerHTML = `<p style="color:#f44336">Error: ${e.message}</p>`;
    }
}

// Dashboard Watchlist
async function loadDashboardWatchlist() {
    const container = document.getElementById("watchlist");
    container.innerHTML = "<p style='color:#888'>Loading watchlist...</p>";

    try {
        const wlData = await fetchJSON("/api/watchlist");
        const items = wlData.watchlist;

        if (items.length === 0) {
            container.innerHTML = `
                <div class="wl-empty">
                    <h3>Watchlist Kosong</h3>
                    <p>Tambahkan saham di menu "Kelola Watchlist"</p>
                </div>
            `;
            return;
        }

        let html = "";
        for (const item of items) {
            try {
                const data = await fetchJSON(`/api/stock/${item.symbol}`);
                const tech = data.technical;
                html += `
                    <div class="stock-card" data-symbol="${item.symbol}" onclick="showStockDetail('${item.symbol}')">
                        <h3>${item.symbol}</h3>
                        <p style="color:#888">${item.name || data.fundamental?.name || item.symbol}</p>
                        <p class="price">${formatRupiah(tech.current_price)}</p>
                        <span class="signal ${signalClass(tech.overall_signal)}">${tech.overall_signal}</span>
                        <p style="margin-top:8px;font-size:0.85rem;color:#888">RSI: ${tech.rsi}</p>
                    </div>
                `;
            } catch (e) {
                html += `<div class="stock-card"><h3>${item.symbol}</h3><p style="color:#888">Error loading</p></div>`;
            }
        }
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = "<p style='color:#888'>Error loading watchlist</p>";
    }
}

// Watchlist Manager
async function loadWatchlistManager() {
    try {
        const data = await fetchJSON("/api/watchlist");
        const items = data.watchlist;
        document.getElementById("wl-count").textContent = items.length;

        const container = document.getElementById("watchlist-list");
        if (items.length === 0) {
            container.innerHTML = `
                <div class="wl-empty">
                    <h3>Watchlist Kosong</h3>
                    <p>Tambahkan saham pertama Anda di atas!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = items.map(item => `
            <div class="wl-item" data-symbol="${item.symbol}">
                <div class="wl-info">
                    <div class="wl-symbol">${item.symbol}</div>
                    <div class="wl-name">${item.name || ""}</div>
                    ${item.notes ? `<div class="wl-notes">${item.notes}</div>` : ""}
                </div>
                <div class="wl-actions">
                    <button class="btn btn-analyze" onclick="analyzeWatchlistItem('${item.symbol}')">Analisis</button>
                    <button class="btn btn-remove" onclick="removeFromWatchlist('${item.symbol}')">Hapus</button>
                </div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Error loading watchlist:", e);
    }
}

async function addToWatchlist() {
    const symbol = document.getElementById("wl-symbol").value.trim().toUpperCase();
    const name = document.getElementById("wl-name").value.trim();
    const notes = document.getElementById("wl-notes").value.trim();

    if (!symbol) return alert("Masukkan kode saham!");

    try {
        const res = await fetch(API_BASE + "/api/watchlist", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, name: name || null, notes: notes || null }),
        });
        const data = await res.json();

        if (data.status === "exists") {
            showToast("Info", `${symbol} sudah ada di watchlist`);
        } else {
            showToast("Berhasil", `${symbol} ditambahkan ke watchlist`);
            document.getElementById("wl-symbol").value = "";
            document.getElementById("wl-name").value = "";
            document.getElementById("wl-notes").value = "";
        }

        loadWatchlistManager();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function removeFromWatchlist(symbol) {
    if (!confirm(`Hapus ${symbol} dari watchlist?`)) return;

    try {
        await fetch(API_BASE + `/api/watchlist/${symbol}`, { method: "DELETE" });
        showToast("Dihapus", `${symbol} dihapus dari watchlist`);
        loadWatchlistManager();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

async function clearWatchlist() {
    if (!confirm("Hapus SEMUA saham dari watchlist?")) return;

    try {
        await fetch(API_BASE + "/api/watchlist", { method: "DELETE" });
        showToast("Dihapus", "Semua watchlist dihapus");
        loadWatchlistManager();
    } catch (e) {
        alert("Error: " + e.message);
    }
}

function analyzeWatchlistItem(symbol) {
    document.getElementById("global-search").value = symbol;
    analyzeStock();
}

async function analyzeFullWatchlist() {
    const container = document.getElementById("watchlist-analysis");
    container.innerHTML = "<p style='color:#888'>Loading analisis watchlist...</p>";

    try {
        const data = await fetchJSON("/api/watchlist/analyze");
        const stocks = data.stocks;

        if (stocks.length === 0) {
            container.innerHTML = "<p style='color:#888'>Watchlist kosong. Tambahkan saham terlebih dahulu.</p>";
            return;
        }

        container.innerHTML = stocks.map(s => {
            if (s.error) {
                return `
                    <div class="stock-card">
                        <h3>${s.symbol}</h3>
                        <p style="color:#f44336">${s.error}</p>
                    </div>
                `;
            }

            const tech = s.technical || {};
            const fund = s.fundamental || {};

            return `
                <div class="stock-card" onclick="showStockDetail('${s.symbol}')">
                    <h3>${s.symbol}</h3>
                    <p style="color:#888;font-size:0.9rem">${s.name || ""}</p>
                    <p class="price">${formatRupiah(tech.current_price)}</p>
                    <span class="signal ${signalClass(tech.overall_signal)}">${tech.overall_signal || "N/A"}</span>
                    <div style="margin-top:10px;font-size:0.8rem;color:#888">
                        <p>RSI: ${tech.rsi || "N/A"} | PE: ${fund.valuation?.details?.[0]?.value || "N/A"}</p>
                        <p>${fund.recommendation || ""}</p>
                    </div>
                    ${s.notes ? `<p style="margin-top:5px;font-size:0.75rem;color:#666;font-style:italic">"${s.notes}"</p>` : ""}
                </div>
            `;
        }).join("");
    } catch (e) {
        container.innerHTML = `<p style="color:#f44336">Error: ${e.message}</p>`;
    }
}

// ===== HORIZON ANALYSIS =====

async function analyzeHorizon() {
    const symbol = document.getElementById("hz-symbol").value.trim().toUpperCase();
    const months = document.getElementById("hz-months").value;
    const container = document.getElementById("horizon-result");

    if (!symbol) {
        container.innerHTML = '<p style="color:#f44336">Masukkan kode saham</p>';
        return;
    }

    container.innerHTML = '<p style="color:#4ecca3">Menganalisis...</p>';

    try {
        const data = await fetchJSON(`/api/stock/${symbol}/horizon?months=${months}`);
        container.innerHTML = renderHorizonResult(data);
    } catch (e) {
        container.innerHTML = `<p style="color:#f44336">Error: ${e.message}</p>`;
    }
}

async function analyzeAllHorizons() {
    const symbol = document.getElementById("hz-symbol").value.trim().toUpperCase();
    const container = document.getElementById("horizon-result");

    if (!symbol) {
        container.innerHTML = '<p style="color:#f44336">Masukkan kode saham</p>';
        return;
    }

    container.innerHTML = '<p style="color:#4ecca3">Menganalisis semua horizon...</p>';

    try {
        const data = await fetchJSON(`/api/stock/${symbol}/horizons`);
        container.innerHTML = renderAllHorizonsResult(data);
    } catch (e) {
        container.innerHTML = `<p style="color:#f44336">Error: ${e.message}</p>`;
    }
}

function renderHorizonResult(data) {
    const h = data.horizon;
    if (!h || h.error) {
        return `<p style="color:#f44336">${h?.error || "No data"}</p>`;
    }

    const recClass = getRecommendationClass(h.recommendation);
    const trend = h.technical?.trend || {};
    const targets = h.price_targets || {};
    const holding = h.holding_period_estimate || {};
    const sr = h.support_resistance || {};
    const risk = h.risk_metrics || {};

    return `
        <div class="horizon-result">
            <div class="horizon-header">
                <h3>${h.symbol} - ${h.company_name || ""}</h3>
                <div class="horizon-recommendation ${recClass}">
                    <span class="rec-label">${h.recommendation}</span>
                    <span class="rec-score">Score: ${h.score}</span>
                </div>
            </div>

            <div class="horizon-info">
                <span class="horizon-badge">Horizon: ${h.horizon?.label || h.horizon?.months + " Bulan"}</span>
                <span class="horizon-price">Harga Sekarang: ${formatRupiah(h.current_price)}</span>
            </div>

            <div class="horizon-grid">
                <div class="horizon-card">
                    <h4>Price Targets</h4>
                    <div class="target-row">
                        <span class="target-label">Entry Zone</span>
                        <span class="target-value">${formatRupiah(targets.entry_zone?.low)} - ${formatRupiah(targets.entry_zone?.high)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Take Profit</span>
                        <span class="target-value target-profit">${formatRupiah(targets.take_profit)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Stop Loss</span>
                        <span class="target-value target-loss">${formatRupiah(targets.stop_loss)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Risk/Reward</span>
                        <span class="target-value ${targets.risk_reward_ratio >= 1.5 ? 'target-profit' : 'target-loss'}">${targets.risk_reward_ratio}x</span>
                    </div>
                </div>

                <div class="horizon-card">
                    <h4>Trend & Momentum</h4>
                    <div class="target-row">
                        <span class="target-label">Trend</span>
                        <span class="target-value">${trend.trend || "N/A"}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">MA20</span>
                        <span class="target-value">${formatRupiah(trend.ma20)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">MA50</span>
                        <span class="target-value">${formatRupiah(trend.ma50)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Volatility</span>
                        <span class="target-value">${risk.volatility_annualized ? risk.volatility_annualized + "%" : "N/A"}</span>
                    </div>
                </div>

                <div class="horizon-card">
                    <h4>Support & Resistance</h4>
                    <div class="target-row">
                        <span class="target-label">Resistance</span>
                        <span class="target-value target-profit">${(sr.resistance || []).map(r => formatRupiah(r)).join(", ") || "N/A"}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Current</span>
                        <span class="target-value">${formatRupiah(h.current_price)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Support</span>
                        <span class="target-value target-loss">${(sr.support || []).map(s => formatRupiah(s)).join(", ") || "N/A"}</span>
                    </div>
                </div>

                <div class="horizon-card">
                    <h4>Holding Period Estimate</h4>
                    <div class="target-row">
                        <span class="target-label">Expected Return</span>
                        <span class="target-value ${holding.expected_return_pct >= 0 ? 'target-profit' : 'target-loss'}">${holding.expected_return_pct}%</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Target Price</span>
                        <span class="target-value">${formatRupiah(holding.expected_price)}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Sentiment</span>
                        <span class="target-value">${h.sentiment?.label || "N/A"}</span>
                    </div>
                    <div class="target-row">
                        <span class="target-label">Fundamental</span>
                        <span class="target-value">Score: ${h.fundamental_score || 0}</span>
                    </div>
                </div>
            </div>

            <div class="horizon-signals">
                <h4>Score Breakdown</h4>
                <div class="signal-list">
                    ${(h.score_details || []).map(d => `
                        <div class="signal-item ${d.impact > 0 ? 'signal-positive' : d.impact < 0 ? 'signal-negative' : 'signal-neutral'}">
                            <span class="signal-factor">${d.factor}</span>
                            <span class="signal-value">${d.value}</span>
                            <span class="signal-impact">${d.impact > 0 ? '+' : ''}${d.impact}</span>
                        </div>
                    `).join("")}
                </div>
            </div>

            <div class="horizon-rationale">
                <h4>Rekomendasi: ${h.recommendation}</h4>
                <p>${h.rationale}</p>
            </div>

            ${renderDetailedAnalysis(h.detailed_analysis, h.horizon)}
        </div>
    `;
}

function renderDetailedAnalysis(da, horizon) {
    if (!da) return "";

    const renderList = (items, icon, cssClass) => {
        if (!items || items.length === 0) return "";
        return `
            <div class="detailed-section ${cssClass}">
                <h5>${icon} ${cssClass.replace("da-", "").replace(/-/g, " ").toUpperCase()}</h5>
                <ul>
                    ${items.map(item => `<li>${item}</li>`).join("")}
                </ul>
            </div>
        `;
    };

    return `
        <div class="detailed-analysis">
            <h4>Analisis Detail - ${horizon?.label || horizon?.months + " Bulan"}</h4>

            ${renderList(da.strengths, "Kekuatan", "da-strengths")}
            ${renderList(da.weaknesses, "Kelemahan", "da-weaknesses")}
            ${renderList(da.opportunities, "Peluang", "da-opportunities")}
            ${renderList(da.risks, "Risiko", "da-risks")}

            ${da.key_factors && da.key_factors.length > 0 ? `
                <div class="detailed-section da-key-factors">
                    <h5>Faktor Kunci</h5>
                    <ul>
                        ${da.key_factors.map(item => `<li>${item}</li>`).join("")}
                    </ul>
                </div>
            ` : ""}

            ${da.action_plan && da.action_plan.length > 0 ? `
                <div class="detailed-section da-action-plan">
                    <h5>Rencana Aksi</h5>
                    <ul>
                        ${da.action_plan.map(item => `<li>${item}</li>`).join("")}
                    </ul>
                </div>
            ` : ""}

            ${da.volatility_ann ? `
                <div class="detailed-section da-volatility">
                    <h5>Volatilitas</h5>
                    <p>Volatilitas tahunan: ${da.volatility_ann}%</p>
                </div>
            ` : ""}
        </div>
    `;
}

function renderAllHorizonsResult(data) {
    const horizons = data.horizons || {};
    const fundamental = data.fundamental || {};
    const sentiment = data.sentiment || {};

    let html = `
        <div class="horizon-all-header">
            <h3>${data.symbol} - Multi-Horizon Analysis</h3>
        </div>

        <div class="horizon-summary-grid">
    `;

    const horizonOrder = ["1m", "3m", "6m", "12m"];
    const horizonLabels = {"1m": "1 Bulan", "3m": "3 Bulan", "6m": "6 Bulan", "12m": "12 Bulan"};

    for (const key of horizonOrder) {
        const h = horizons[key];
        if (!h) continue;
        const recClass = getRecommendationClass(h.recommendation);
        const holding = h.holding_period_estimate || {};
        const targets = h.price_targets || {};

        html += `
            <div class="horizon-summary-card ${recClass}">
                <div class="hz-card-header">
                    <h4>${horizonLabels[key]}</h4>
                    <span class="hz-rec">${h.recommendation}</span>
                </div>
                <div class="hz-card-score">Score: ${h.score}</div>
                <div class="hz-card-details">
                    <div class="hz-detail">
                        <span>Expected Return</span>
                        <span class="${holding.expected_return_pct >= 0 ? 'target-profit' : 'target-loss'}">${holding.expected_return_pct}%</span>
                    </div>
                    <div class="hz-detail">
                        <span>Target Price</span>
                        <span>${formatRupiah(holding.expected_price)}</span>
                    </div>
                    <div class="hz-detail">
                        <span>Take Profit</span>
                        <span class="target-profit">${formatRupiah(targets.take_profit)}</span>
                    </div>
                    <div class="hz-detail">
                        <span>Stop Loss</span>
                        <span class="target-loss">${formatRupiah(targets.stop_loss)}</span>
                    </div>
                    <div class="hz-detail">
                        <span>Risk/Reward</span>
                        <span>${targets.risk_reward_ratio}x</span>
                    </div>
                    <div class="hz-detail">
                        <span>Trend</span>
                        <span>${h.technical?.trend?.trend || "N/A"}</span>
                    </div>
                </div>
                ${h.detailed_analysis ? `
                    <div class="hz-card-analysis" style="margin-top:15px;border-top:1px solid #333;padding-top:12px">
                        ${h.detailed_analysis.strengths?.length > 0 ? `
                            <div style="margin-bottom:8px">
                                <span style="color:#4CAF50;font-size:0.8rem;font-weight:bold">KEKUATAN</span>
                                ${h.detailed_analysis.strengths.map(s => `<p style="font-size:0.8rem;color:#ccc;margin:4px 0">+ ${s}</p>`).join("")}
                            </div>
                        ` : ""}
                        ${h.detailed_analysis.weaknesses?.length > 0 ? `
                            <div style="margin-bottom:8px">
                                <span style="color:#EF5350;font-size:0.8rem;font-weight:bold">KELEMAHAN</span>
                                ${h.detailed_analysis.weaknesses.map(w => `<p style="font-size:0.8rem;color:#ccc;margin:4px 0">- ${w}</p>`).join("")}
                            </div>
                        ` : ""}
                        ${h.detailed_analysis.opportunities?.length > 0 ? `
                            <div style="margin-bottom:8px">
                                <span style="color:#2196F3;font-size:0.8rem;font-weight:bold">PELUANG</span>
                                ${h.detailed_analysis.opportunities.map(o => `<p style="font-size:0.8rem;color:#ccc;margin:4px 0">! ${o}</p>`).join("")}
                            </div>
                        ` : ""}
                        ${h.detailed_analysis.risks?.length > 0 ? `
                            <div style="margin-bottom:8px">
                                <span style="color:#FF9800;font-size:0.8rem;font-weight:bold">RISIKO</span>
                                ${h.detailed_analysis.risks.map(r => `<p style="font-size:0.8rem;color:#ccc;margin:4px 0">! ${r}</p>`).join("")}
                            </div>
                        ` : ""}
                        ${h.detailed_analysis.action_plan?.length > 0 ? `
                            <div style="margin-bottom:8px">
                                <span style="color:#4ecca3;font-size:0.8rem;font-weight:bold">RENCANA AKSI</span>
                                ${h.detailed_analysis.action_plan.map(a => `<p style="font-size:0.8rem;color:#ccc;margin:4px 0">> ${a}</p>`).join("")}
                            </div>
                        ` : ""}
                    </div>
                ` : ""}
            </div>
        `;
    }

    html += `</div>`;

    html += `
        <div class="horizon-fundamental-summary">
            <h4>Fundamental Summary</h4>
            ${fundamental.report_info?.period ? `
                <div style="margin-bottom:10px;padding:6px 10px;background:#0f3460;border-left:3px solid #4ecca3;border-radius:4px;font-size:0.8rem">
                    <span style="color:#4ecca3;font-weight:bold">${fundamental.report_info.period}</span>
                    <span style="color:#888"> — ${fundamental.report_info.type || "Laporan Keuangan"}</span>
                    ${fundamental.report_info.available_periods?.length > 1 ? `
                        <div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">
                            ${fundamental.report_info.available_periods.map(p => `
                                <span style="padding:1px 6px;background:#16213e;border-radius:3px;font-size:0.7rem;color:#aaa">${p.period}</span>
                            `).join("")}
                        </div>
                    ` : ""}
                </div>
            ` : ""}
            <div class="fund-summary-grid">
                <div class="fund-item"><span>Valuation Score</span><span>${fundamental.valuation?.score || 0}</span></div>
                <div class="fund-item"><span>Quality Score</span><span>${fundamental.quality?.score || 0}</span></div>
                <div class="fund-item"><span>Health Score</span><span>${fundamental.financial_health?.score || 0}</span></div>
                <div class="fund-item"><span>Total Score</span><span>${fundamental.total_score || 0}</span></div>
                <div class="fund-item"><span>Recommendation</span><span>${fundamental.recommendation || "N/A"}</span></div>
                <div class="fund-item"><span>Sentiment</span><span>${sentiment.overall_sentiment || "N/A"}</span></div>
            </div>
        </div>
    `;

    return html;
}

function getRecommendationClass(recommendation) {
    if (!recommendation) return "";
    const rec = recommendation.toUpperCase();
    if (rec.includes("STRONG BUY")) return "rec-strong-buy";
    if (rec.includes("BUY") || rec.includes("LEAN BUY")) return "rec-buy";
    if (rec.includes("HOLD")) return "rec-hold";
    if (rec.includes("SELL") || rec.includes("LEAN SELL")) return "rec-sell";
    if (rec.includes("STRONG SELL")) return "rec-strong-sell";
    return "";
}

// Init
document.addEventListener("DOMContentLoaded", () => {
    refreshDashboard();
    loadDashboardWatchlist();
    loadAlerts();
    connectWebSocket();
    setAutoRefresh();
});

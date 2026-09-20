import os
import json
from datetime import datetime, timedelta
from jinja2 import Template


REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Stock Analysis Report - {{ report_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }
        h2 { color: #16213e; margin-top: 30px; }
        .stock-card { background: #f8f9fa; border-left: 4px solid #e94560; padding: 15px; margin: 10px 0; border-radius: 4px; }
        .signal-buy { color: #28a745; font-weight: bold; }
        .signal-sell { color: #dc3545; font-weight: bold; }
        .signal-hold { color: #ffc107; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #1a1a2e; color: white; }
        .summary-box { display: inline-block; background: #e8f5e9; padding: 10px 20px; border-radius: 5px; margin: 5px; }
        .disclaimer { font-size: 12px; color: #888; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Stock Analysis Report</h1>
        <p><strong>Report Date:</strong> {{ report_date }}</p>
        <p><strong>Period:</strong> {{ period }}</p>

        <h2>Market Overview</h2>
        <div class="summary-box">
            <strong>IHSG:</strong> {{ market.ihsg }}
        </div>
        <div class="summary-box">
            <strong>Change:</strong> {{ market.change }} ({{ market.change_pct }}%)
        </div>

        <h2>Portfolio Analysis</h2>
        {% for stock in stocks %}
        <div class="stock-card">
            <h3>{{ stock.symbol }} - {{ stock.name }}</h3>
            <p><strong>Price:</strong> Rp {{ stock.technical.current_price }}</p>
            <p><strong>Signal:</strong> 
                <span class="signal-{{ stock.technical.overall_signal|lower|replace(' ', '') }}">
                    {{ stock.technical.overall_signal }}
                </span>
            </p>
            <p><strong>RSI:</strong> {{ stock.technical.rsi }}</p>
            <p><strong>Fundamental:</strong> {{ stock.fundamental.recommendation }}</p>
            <p><strong>Sentiment:</strong> {{ stock.sentiment.overall_sentiment }} (Score: {{ stock.sentiment.sentiment_score }})</p>
        </div>
        {% endfor %}

        <h2>Backtesting Results</h2>
        {% for result in backtest_results %}
        <div class="stock-card">
            <h3>{{ result.symbol }}</h3>
            <p><strong>Best Strategy:</strong> {{ result.best_strategy }}</p>
            <p><strong>Return:</strong> {{ result.best_return }}%</p>
            <table>
                <tr><th>Strategy</th><th>Return %</th><th>Win Rate</th><th>Trades</th></tr>
                {% for s in result.strategies %}
                <tr>
                    <td>{{ s.strategy }}</td>
                    <td>{{ s.total_return_pct }}%</td>
                    <td>{{ s.win_rate }}%</td>
                    <td>{{ s.total_trades }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endfor %}

        <div class="disclaimer">
            <p>⚠️ <strong>Disclaimer:</strong> This report is for educational purposes only. 
            Stock analysis tools provide data-driven insights but do NOT guarantee future performance. 
            Always do your own research and consult a licensed financial advisor before making investment decisions.</p>
        </div>
    </div>
</body>
</html>
"""


def generate_report(stocks_data, backtest_results, market_data):
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    period = "Last 1 Year"

    template = Template(REPORT_TEMPLATE)
    html_content = template.render(
        report_date=report_date,
        period=period,
        market=market_data,
        stocks=stocks_data,
        backtest_results=backtest_results,
    )

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    json_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_filepath = os.path.join(reports_dir, json_filename)

    report_data = {
        "report_date": report_date,
        "market": market_data,
        "stocks": stocks_data,
        "backtest_results": backtest_results,
    }

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, default=str)

    return {"html_report": filepath, "json_report": json_filepath, "report_date": report_date}


def generate_quick_summary(stocks_data):
    summary = []
    for stock in stocks_data:
        summary.append({
            "symbol": stock.get("symbol"),
            "price": stock.get("technical", {}).get("current_price", 0),
            "signal": stock.get("technical", {}).get("overall_signal", "N/A"),
            "rsi": stock.get("technical", {}).get("rsi", 0),
            "fundamental": stock.get("fundamental", {}).get("recommendation", "N/A"),
            "sentiment": stock.get("sentiment", {}).get("overall_sentiment", "N/A"),
        })
    return summary

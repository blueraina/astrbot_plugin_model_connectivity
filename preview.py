import sys
import os
import json
from jinja2 import Template

STATUS_TEMPLATE = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&display=swap');
    
    * { box-sizing: border-box; }

    body {
      margin: 0;
      width: 1500px;
      min-height: 860px;
      color: #f5f7fb;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: 
        radial-gradient(circle at 15% 50%, rgba(20, 255, 140, 0.08), transparent 30%),
        radial-gradient(circle at 85% 30%, rgba(255, 77, 94, 0.08), transparent 30%),
        radial-gradient(circle at 50% 80%, rgba(26, 177, 255, 0.08), transparent 30%),
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        #0a0b0c;
      background-size: 100% 100%, 100% 100%, 100% 100%, 38px 38px, 38px 38px;
    }

    .page { padding: 48px; }

    .topline {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 40px;
    }

    .eyebrow {
      display: flex;
      align-items: center;
      gap: 12px;
      color: #9499a3;
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    .pulse-icon {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border-radius: 10px;
      color: #000;
      background: linear-gradient(135deg, #fff, #e0e5ec);
      box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15);
      font-size: 16px;
    }

    h1 {
      margin: 16px 0 16px;
      font-size: 64px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: -1px;
      background: linear-gradient(135deg, #ffffff, #a0a5b0);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .summary {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      color: #a7abb2;
      font-size: 14px;
      font-weight: 700;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 14px;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(20px) saturate(150%);
      -webkit-backdrop-filter: blur(20px) saturate(150%);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
      color: #d9dde5;
    }

    .pill.ok { color: #18e78d; background: linear-gradient(135deg, rgba(11, 159, 93, 0.2), rgba(11, 159, 93, 0.05)); border-color: rgba(24, 231, 141, 0.3); box-shadow: 0 0 15px rgba(24, 231, 141, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }
    .pill.slow { color: #ffb11a; background: linear-gradient(135deg, rgba(255, 177, 26, 0.2), rgba(255, 177, 26, 0.05)); border-color: rgba(255, 177, 26, 0.3); box-shadow: 0 0 15px rgba(255, 177, 26, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }
    .pill.error { color: #ff4d5e; background: linear-gradient(135deg, rgba(255, 77, 94, 0.2), rgba(255, 77, 94, 0.05)); border-color: rgba(255, 77, 94, 0.3); box-shadow: 0 0 15px rgba(255, 77, 94, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1); }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 8px currentColor;
    }

    .right-meta {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 12px;
      padding-top: 80px;
      color: #7d828c;
      font-size: 13px;
      font-weight: 500;
    }

    .overall {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 12px 20px;
      border-radius: 999px;
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(30px) saturate(150%);
      -webkit-backdrop-filter: blur(30px) saturate(150%);
      font-size: 14px;
      font-weight: 800;
      letter-spacing: 0.5px;
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .grid {
      column-count: 2;
      column-gap: 24px;
    }

    .provider-card {
      display: inline-block;
      width: 100%;
      margin: 0 0 24px;
      break-inside: avoid;
      page-break-inside: avoid;
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%);
      backdrop-filter: blur(40px) saturate(180%);
      -webkit-backdrop-filter: blur(40px) saturate(180%);
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.3), inset 0 1px 1px rgba(255, 255, 255, 0.1);
      overflow: hidden;
    }

    .provider-head {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(0, 0, 0, 0.15);
    }

    .provider-icon {
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      width: 52px;
      height: 52px;
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.02) 100%);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4), inset 0 1px 2px rgba(255, 255, 255, 0.2);
      font-size: 20px;
      font-weight: 800;
    }

    .provider-icon svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }

    .provider-info h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 800;
      color: #f5f7fb;
    }

    .provider-info p {
      margin: 6px 0 0;
      color: #a0a5b0;
      font-size: 13px;
      font-weight: 600;
    }

    .provider-status {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 800;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02));
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .provider-status.ok, .status-badge.ok { color: #18e78d; border-color: rgba(24, 231, 141, 0.4); box-shadow: 0 0 10px rgba(24, 231, 141, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(11, 159, 93, 0.3), rgba(11, 159, 93, 0.1)); }
    .provider-status.slow, .status-badge.slow { color: #ffb11a; border-color: rgba(255, 177, 26, 0.4); box-shadow: 0 0 10px rgba(255, 177, 26, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(255, 177, 26, 0.3), rgba(255, 177, 26, 0.1)); }
    .provider-status.error, .status-badge.error { color: #ff4d5e; border-color: rgba(255, 77, 94, 0.4); box-shadow: 0 0 10px rgba(255, 77, 94, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1); background: linear-gradient(135deg, rgba(255, 77, 94, 0.3), rgba(255, 77, 94, 0.1)); }

    .models {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .model-row {
      position: relative;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
      padding: 16px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    }

    .curve-container {
      position: relative;
      height: 48px;
      margin-bottom: 24px;
      margin-top: -4px;
    }

    .curve-chart {
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      opacity: 0.8;
      pointer-events: none;
    }

    .curve-chart .area { fill: url(#curve-gradient-dark); }
    .curve-chart .line { fill: none; stroke: #8b5cf6; stroke-width: 1.5; }
    .light .curve-chart .area { fill: url(#curve-gradient-light); }
    .light .curve-chart .line { stroke: #6366f1; }

    .time-axis {
      position: absolute;
      left: 0;
      right: 0;
      bottom: -16px;
      height: 16px;
    }

    .time-axis span {
      position: absolute;
      transform: translateX(-50%);
      font-size: 10px;
      color: #7d828c;
      font-weight: 600;
      white-space: nowrap;
    }
    
    .light .time-axis span { color: #94a3b8; }

    .model-top, .metric-grid, .history, .error-text {
      position: relative;
      z-index: 1;
      pointer-events: none;
    }

    .model-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .model-name {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 10px;
      font-size: 17px;
      font-weight: 800;
    }

    .model-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex: 0 0 auto;
      box-shadow: 0 0 10px currentColor;
    }

    .model-dot.ok { color: #16d586; background: #16d586; }
    .model-dot.slow { color: #ffb11a; background: #ffb11a; }
    .model-dot.error { color: #ff3048; background: #ff3048; }

    .status-badge {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 11px;
      font-weight: 800;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.02));
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }

    .metric {
      min-width: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%);
      border: 1px solid rgba(255, 255, 255, 0.08);
      padding: 12px 16px;
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    }

    .metric label {
      display: block;
      color: #8b9099;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
    }

    .metric strong {
      display: block;
      color: #ffffff;
      font-size: 18px;
      font-weight: 900;
    }

    .metric strong.availability.ok { color: #18e78d; }
    .metric strong.availability.slow { color: #ffb11a; }
    .metric strong.availability.error { color: #ff4d5e; }

    .history {
      display: flex;
      align-items: flex-end;
      gap: 4px;
      height: 16px;
    }

    .bar {
      flex: 1 1 0;
      min-width: 4px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      transition: height 0.3s ease;
    }

    .bar.ok { height: 100%; background: #10c783; box-shadow: 0 0 6px rgba(16, 199, 131, 0.4); }
    .bar.slow { height: 100%; background: #ffb11a; box-shadow: 0 0 6px rgba(255, 177, 26, 0.4); }
    .bar.error { height: 100%; background: #ff3048; box-shadow: 0 0 6px rgba(255, 48, 72, 0.4); }
    .bar.empty { height: 100%; opacity: 0.3; }

    .error-text {
      margin-top: 12px;
      color: #ff98a2;
      font-size: 13px;
      line-height: 1.5;
      padding: 10px 12px;
      background: rgba(255, 48, 72, 0.08);
      border-radius: 8px;
      border: 1px solid rgba(255, 48, 72, 0.15);
    }

    body.light {
      color: #111827;
      background: 
        radial-gradient(circle at 15% 50%, rgba(20, 255, 140, 0.2), transparent 35%),
        radial-gradient(circle at 85% 30%, rgba(255, 77, 94, 0.2), transparent 35%),
        radial-gradient(circle at 50% 80%, rgba(26, 177, 255, 0.2), transparent 35%),
        linear-gradient(rgba(255, 255, 255, 0.5) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.5) 1px, transparent 1px),
        #f0f4f8;
      background-size: 100% 100%, 100% 100%, 100% 100%, 38px 38px, 38px 38px;
    }

    .light h1 {
      background: linear-gradient(135deg, #111827, #4b5563);
      -webkit-background-clip: text;
    }

    .light .provider-card {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.3) 100%);
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .provider-head {
      background: rgba(255, 255, 255, 0.4);
      border-bottom-color: rgba(0, 0, 0, 0.05);
    }

    .light .provider-icon {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.5) 100%);
      border: 1px solid rgba(255, 255, 255, 1);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), inset 0 1px 2px rgba(255, 255, 255, 1);
      color: #111827;
    }

    .light .provider-info h2,
    .light .model-name,
    .light .metric strong { color: #111827; }

    .light .provider-info p,
    .light .right-meta,
    .light .metric label,
    .light .eyebrow { color: #64748b; }

    .light .pill, .light .overall {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.5) 100%);
      color: #334155;
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .model-row {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.6) 0%, rgba(255, 255, 255, 0.3) 100%);
      border-color: rgba(255, 255, 255, 0.8);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02), inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .metric {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.7) 0%, rgba(255, 255, 255, 0.4) 100%);
      border-color: rgba(255, 255, 255, 0.9);
      box-shadow: inset 0 1px 1px rgba(255, 255, 255, 1);
    }

    .light .bar.empty { background: #e2e8f0; }

    .light .provider-status, .light .status-badge { 
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.4) 100%); 
      border-color: rgba(255, 255, 255, 0.9);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 1);
    }
  </style>
</head>
<body class="{{ theme }}">
  <svg width="0" height="0" style="position:absolute;">
    <defs>
      <linearGradient id="curve-gradient-dark" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="rgba(139, 92, 246, 0.5)" />
        <stop offset="100%" stop-color="rgba(139, 92, 246, 0.0)" />
      </linearGradient>
      <linearGradient id="curve-gradient-light" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="rgba(99, 102, 241, 0.3)" />
        <stop offset="100%" stop-color="rgba(99, 102, 241, 0.0)" />
      </linearGradient>
    </defs>
  </svg>
  <main class="page">
    <section class="topline">
      <div>
        <h1>{{ title }}</h1>
        <div class="summary">
          <span class="pill ok"><span class="dot"></span>{{ ok_count }} 正常</span>
          <span class="pill slow"><span class="dot"></span>{{ slow_count }} 较慢</span>
          <span class="pill error"><span class="dot"></span>{{ error_count }} 错误</span>
          <span class="pill">{{ provider_count }} 个 Provider</span>
          <span class="pill">{{ total }} 个模型</span>
        </div>
      </div>
      <div class="right-meta">
        <div class="overall"><span class="dot"></span>{{ overall_status }}</div>
        <div>更新于 {{ generated_at }} · 耗时 {{ elapsed_ms }} ms</div>
        <div>全局并发 {{ global_concurrency }} · 单 Provider {{ provider_concurrency }} · 统计 {{ stats_window_days }} 天 · 历史 {{ history_size }} 次</div>
      </div>
    </section>

    <section class="grid">
      {% for provider in providers %}
      <article class="provider-card">
        <header class="provider-head">
          <div class="provider-icon">
            {% if provider.provider_logo and provider.provider_logo.startswith('http') %}
              <img src="{{ provider.provider_logo }}" alt="logo" style="width:24px; height:24px; object-fit:contain;" />
            {% elif provider.provider_logo and '<svg' in provider.provider_logo %}
              {{ provider.provider_logo | safe }}
            {% else %}
              {{ provider.provider_name[:1] | upper }}
            {% endif %}
          </div>
          <div class="provider-info">
            <h2>{{ provider.provider_name }}</h2>
            <p>{{ provider.provider_type }} · {{ provider.provider_id }} · {{ provider.model_count }} models</p>
          </div>
          <div class="provider-status {{ provider.status }}">{{ provider.status_label }}</div>
        </header>

        <div class="models">
          {% for item in provider.results %}
          <div class="model-row">
            <div class="model-top">
              <div class="model-name">
                <span class="model-dot {{ item.status_class }}"></span>
                <span>{{ item.model }}</span>
              </div>
              <div class="status-badge {{ item.status_class }}">{{ item.status_label }}</div>
            </div>

            <div class="metric-grid">
              <div class="metric">
                <label>当前延迟</label>
                <strong>{{ item.latency_ms }} ms</strong>
              </div>
              <div class="metric">
                <label>24h平均</label>
                <strong>{{ item.avg_latency_24h }}</strong>
              </div>
              <div class="metric">
                <label>可用性</label>
                <strong class="availability {{ item.status_class }}">{{ item.availability }}</strong>
              </div>
              <div class="metric">
                <label>周成功次数</label>
                <strong class="availability {{ item.status_class }}">{{ item.weekly_success_text }}</strong>
              </div>
            </div>

            {% if item.show_curve_chart %}
            <div class="curve-container">
              <svg class="curve-chart" viewBox="0 0 100 40" preserveAspectRatio="none">
                <path d="{{ item.svg_path_area }}" class="area" />
                <path d="{{ item.svg_path_line }}" class="line" />
              </svg>
              <div class="time-axis">
                {% for label in item.time_labels %}
                <span style="{{ label.style }}">{{ label.text }}</span>
                {% endfor %}
              </div>
            </div>
            {% endif %}

            <div class="history" title="最近 {{ history_size }} 次检测">
              {% for status in item.history %}
              <span class="bar {{ status }}"></span>
              {% endfor %}
            </div>

            {% if item.error %}
            <div class="error-text">{{ item.error }}</div>
            {% endif %}
          </div>
          {% endfor %}
        </div>
      </article>
      {% endfor %}
    </section>

    {% if provider_errors %}
    <section class="provider-errors">
      <h3>Provider 枚举异常</h3>
      {% for item in provider_errors %}
      <p>{{ item.provider_type }} · {{ item.provider_id }}：{{ item.error }}</p>
      {% endfor %}
    </section>
    {% endif %}
  </main>
</body>
</html>
"""

mock_report = {
    'theme': 'dark',
    'title': '模型连通性',
    'ok_count': 12,
    'slow_count': 2,
    'error_count': 1,
    'provider_count': 3,
    'total': 15,
    'overall_status': 'OPERATIONAL',
    'generated_at': '2026-05-01 13:00:00',
    'elapsed_ms': 1234,
    'global_concurrency': 3,
    'provider_concurrency': 1,
    'stats_window_days': 7,
    'history_size': 30,
    'providers': [
        {
            'provider_logo': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/openai.svg',
            'provider_name': 'OpenAI',
            'provider_type': 'openai',
            'provider_id': 'openai-1',
            'model_count': 2,
            'status': 'ok',
            'status_label': '正常',
            'results': [
                {
                    'status_class': 'ok',
                    'status_label': '正常',
                    'model': 'gpt-4o',
                    'latency_ms': 850,
                    'avg_latency_24h': '820 ms',
                    'availability': '99.9%',
                    'weekly_success_text': '245/245',
                    'show_curve_chart': True,
                    'svg_path_area': 'M 0,30 L 50,20 L 100,25 L 100,40 L 0,40 Z',
                    'svg_path_line': 'M 0,30 L 50,20 L 100,25',
                    'time_labels': [{'text': '12:00', 'style': 'left: 10%;'}, {'text': '13:00', 'style': 'left: 90%;'}],
                    'history': ['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'slow', 'ok', 'ok', 'ok'] * 3,
                    'error': ''
                },
                {
                    'status_class': 'slow',
                    'status_label': '较慢',
                    'model': 'gpt-4-turbo',
                    'latency_ms': 4500,
                    'avg_latency_24h': '4100 ms',
                    'availability': '100%',
                    'weekly_success_text': '120/120',
                    'show_curve_chart': True,
                    'svg_path_area': 'M 0,10 L 50,30 L 100,15 L 100,40 L 0,40 Z',
                    'svg_path_line': 'M 0,10 L 50,30 L 100,15',
                    'time_labels': [{'text': '12:00', 'style': 'left: 10%;'}, {'text': '13:00', 'style': 'left: 90%;'}],
                    'history': ['ok', 'slow', 'slow', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok'] * 3,
                    'error': ''
                }
            ]
        },
        {
            'provider_logo': 'https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/anthropic.svg',
            'provider_name': 'Anthropic',
            'provider_type': 'anthropic',
            'provider_id': 'anthropic-1',
            'model_count': 1,
            'status': 'error',
            'status_label': '异常',
            'results': [
                {
                    'status_class': 'error',
                    'status_label': '错误',
                    'model': 'claude-3-opus',
                    'latency_ms': 0,
                    'avg_latency_24h': 'N/A',
                    'availability': '85.0%',
                    'weekly_success_text': '18/25',
                    'show_curve_chart': True,
                    'svg_path_area': 'M 0,40 L 100,40 Z',
                    'svg_path_line': 'M 0,40 L 100,40',
                    'time_labels': [{'text': '12:00', 'style': 'left: 10%;'}, {'text': '13:00', 'style': 'left: 90%;'}],
                    'history': ['ok', 'ok', 'error', 'error', 'error', 'error', 'ok', 'ok', 'ok', 'ok'] * 3,
                    'error': 'Connection timeout after 30s'
                }
            ]
        }
    ],
    'provider_errors': []
}

template = Template(STATUS_TEMPLATE)
html_dark = template.render(**mock_report)
mock_report['theme'] = 'light'
html_light = template.render(**mock_report)

with open(r'c:\Users\Lenovo\Desktop\模型连通性测试插件\preview_dark.html', 'w', encoding='utf-8') as f:
    f.write(html_dark)
    
with open(r'c:\Users\Lenovo\Desktop\模型连通性测试插件\preview_light.html', 'w', encoding='utf-8') as f:
    f.write(html_light)

---
name: trading_sentiment_analysis
description: Daily crypto news sentiment scoring for grid trading parameter adjustment
tags: [trading, sentiment, research]
---

## Trading Sentiment Analysis

> Equip this skill for the daily sentiment scoring task (part of ROB-011).

### Purpose

Score daily crypto market sentiment from news headlines. The score feeds into the grid trading system to adjust position sizing and aggressiveness.

### Workflow

1. **Read 3-5 top crypto headlines** using the browser tool:
   ```
   browser(url="https://www.coindesk.com/", action="get_text")
   browser(url="https://cointelegraph.com/", action="get_text")
   ```

2. **Score sentiment** on a scale of -1.0 to +1.0:

   | Score | Meaning | Example Headlines |
   |-------|---------|-------------------|
   | -1.0 | Extreme bearish | "Major exchange hacked", "Regulatory crackdown imminent" |
   | -0.5 | Bearish | "ETF outflows continue", "Fed signals more rate hikes" |
   | 0.0 | Neutral | "Market consolidates", "Mixed signals from indicators" |
   | +0.5 | Bullish | "ETF inflows surge", "Fed holds rates steady" |
   | +1.0 | Extreme bullish | "Bitcoin ETF approved", "Major institutional adoption announced" |

3. **Consider context beyond headlines:**
   - Is this a reaction to old news or genuinely new?
   - Is the market already priced in this news?
   - Are there upcoming events (FOMC, earnings, regulatory deadlines)?
   - Is social media amplifying fear/greed beyond what's warranted?

4. **Store the score** in a research report:
   ```
   research_store(
     title="Sentiment: Daily Market Score 2026-04-05",
     summary="Score: -0.3 (mildly bearish). Fed minutes hawkish, ETF flows flat.",
     body="<detailed reasoning>",
     tags=["sentiment", "daily", "trading"]
   )
   ```

5. **Report to Discord:**
   ```
   "Sentiment update: -0.3 (mildly bearish)
    FGI: 11 (extreme fear), Funding: -0.001% (neutral), News: -0.3
    Grid adjustment: normal capital, defensive spacing.
    Key factor: Fed minutes more hawkish than expected."
   ```

### Scoring Guidelines

**Focus on catalysts that move crypto markets:**
- Federal Reserve / central bank decisions (rates, QT, QE)
- ETF flows (inflows = bullish, outflows = bearish)
- Regulatory actions (SEC lawsuits, bans, approvals)
- Exchange/protocol incidents (hacks, exploits, insolvencies)
- Macro data (CPI, jobs, GDP — affects risk appetite)
- Institutional adoption (treasury allocations, payment integrations)

**Ignore noise:**
- Individual altcoin pumps/dumps (not relevant to BTC/ETH/SOL/XRP grid)
- Celebrity endorsements
- Technical analysis predictions from pundits
- Price predictions ("BTC to $100K by year end")

### What Grid Does With Your Score

Your score is weighted 20% in the composite sentiment calculation:

```
sentiment = FGI × 0.5 + funding_rate × 0.3 + YOUR_SCORE × 0.2
```

Impact on grid:
- Score pushes toward extreme_fear → grid opens with 1.5x capital (contrarian)
- Score pushes toward extreme_greed → grid pauses (don't buy euphoria)
- Score near neutral → no adjustment

### Anti-Hallucination Rules

- **Only score what you actually read** — don't invent headlines
- **If browser fails** — score 0.0 (neutral) and note "unable to fetch news"
- **If unsure** — lean toward 0.0 (neutral is always safe)
- **Never score based on price movement alone** — that's what indicators are for

# Expected TASE (maya.tase.co.il) response fields
# Validation rule: see README.md

## Price/quote endpoint
- security_id, symbol, last_price, bid, ask, volume, high, low, prev_close, timestamp

## Filing/disclosure endpoint (MAGNA)
- filing_id, company_id, filing_type, publish_date, title, document_url

## Fundamentals (semi-annual reports)
- period_start, period_end, revenue, net_income, ebitda, total_debt, cash, reporting_currency (expect ILS unless dual-listed), reporting_standard (Israeli IFRS vs US GAAP for dual-listed)

## Corporate actions endpoint
- action_type (split/rights_issue/buyback), announce_date, effective_date, ratio_or_amount

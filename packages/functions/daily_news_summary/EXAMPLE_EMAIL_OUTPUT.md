# Example Email Output

This document shows what the daily news summary email looks like with sample data.

## HTML Email Output

```
Daily Global News Summary
December 15, 2024
Here's what happened in the world today
```

### World Section

**Article 1:**
- **Title:** Global Climate Summit Reaches Historic Agreement
- **Sentiment:** POSITIVE
- **Source:** BBC News | Published: Mon, 15 Dec 2024 08:00:00 GMT
- **Summary:** World leaders reached a historic climate agreement at the UN summit in Dubai. The deal commits nations to reducing greenhouse gas emissions by 50% by 2030 and achieving net-zero by 2050...
- **Key Topics:** climate agreement, emissions reduction, renewable energy, global summit, net-zero emissions

**Article 2:**
- **Title:** Peace Talks Resume in Middle East
- **Sentiment:** NEUTRAL
- **Source:** BBC News | Published: Mon, 15 Dec 2024 07:30:00 GMT
- **Summary:** Diplomatic efforts to broker peace in the Middle East resumed today with representatives from multiple nations meeting in Geneva. The talks focus on humanitarian aid and...
- **Key Topics:** peace talks, Middle East, diplomatic efforts, humanitarian aid, Geneva summit

### Business Section

**Article 1:**
- **Title:** Stock Markets Hit Record Highs Amid Economic Optimism
- **Sentiment:** POSITIVE
- **Source:** Reuters | Published: Mon, 15 Dec 2024 06:00:00 GMT
- **Summary:** Global stock markets surged to record levels following positive economic indicators released today. Technology stocks led the gains, with major indices up 2.5%...
- **Key Topics:** stock market, economic growth, technology stocks, financial markets, record highs

**Article 2:**
- **Title:** Federal Reserve Signals Interest Rate Stability
- **Sentiment:** NEUTRAL
- **Source:** Reuters | Published: Sun, 14 Dec 2024 20:00:00 GMT
- **Summary:** The Federal Reserve announced it will maintain current interest rates, citing stable inflation and strong employment numbers. Analysts predict rates will remain steady through...
- **Key Topics:** Federal Reserve, interest rates, inflation, monetary policy, economic stability

### Technology Section

**Article 1:**
- **Title:** AI Breakthrough in Medical Diagnosis Announced
- **Sentiment:** POSITIVE
- **Source:** TechCrunch | Published: Mon, 15 Dec 2024 05:00:00 GMT
- **Summary:** Researchers at leading medical institutions announced a major breakthrough in AI-powered medical diagnosis. The new system can detect early-stage cancers with 95% accuracy...
- **Key Topics:** artificial intelligence, medical diagnosis, machine learning, healthcare technology, cancer detection

**Article 2:**
- **Title:** Major Tech Company Announces Quantum Computing Milestone
- **Sentiment:** POSITIVE
- **Source:** TechCrunch | Published: Sun, 14 Dec 2024 22:00:00 GMT
- **Summary:** A leading technology company announced it has achieved quantum supremacy in a new class of problems. The quantum computer solved a problem that would take classical computers...
- **Key Topics:** quantum computing, quantum supremacy, technology innovation, computational breakthrough

**Article 3:**
- **Title:** Cybersecurity Concerns Rise After Major Data Breach
- **Sentiment:** NEGATIVE
- **Source:** TechCrunch | Published: Sat, 13 Dec 2024 18:00:00 GMT
- **Summary:** A major data breach affecting millions of users has raised concerns about cybersecurity practices. The incident exposed personal information including names, emails, and...
- **Key Topics:** cybersecurity, data breach, information security, privacy concerns, digital safety

## Plain Text Email Output

```
Daily Global News Summary
December 15, 2024
Here's what happened in the world today

============================================================

World
-----

• Global Climate Summit Reaches Historic Agreement [POSITIVE]
  Source: BBC News | Published: Mon, 15 Dec 2024 08:00:00 GMT
  World leaders reached a historic climate agreement at the UN summit in Dubai. The deal commits nations to reducing greenhouse gas emissions by 50% by 2030 and achieving net-zero by 2050...
  Key Topics: climate agreement, emissions reduction, renewable energy, global summit, net-zero emissions
  Read more: https://www.bbc.com/news/climate-summit

• Peace Talks Resume in Middle East [NEUTRAL]
  Source: BBC News | Published: Mon, 15 Dec 2024 07:30:00 GMT
  Diplomatic efforts to broker peace in the Middle East resumed today with representatives from multiple nations meeting in Geneva. The talks focus on humanitarian aid and...
  Key Topics: peace talks, Middle East, diplomatic efforts, humanitarian aid, Geneva summit
  Read more: https://www.bbc.com/news/world-middle-east

Business
--------

• Stock Markets Hit Record Highs Amid Economic Optimism [POSITIVE]
  Source: Reuters | Published: Mon, 15 Dec 2024 06:00:00 GMT
  Global stock markets surged to record levels following positive economic indicators released today. Technology stocks led the gains, with major indices up 2.5%...
  Key Topics: stock market, economic growth, technology stocks, financial markets, record highs
  Read more: https://www.reuters.com/business/markets

• Federal Reserve Signals Interest Rate Stability [NEUTRAL]
  Source: Reuters | Published: Sun, 14 Dec 2024 20:00:00 GMT
  The Federal Reserve announced it will maintain current interest rates, citing stable inflation and strong employment numbers. Analysts predict rates will remain steady through...
  Key Topics: Federal Reserve, interest rates, inflation, monetary policy, economic stability
  Read more: https://www.reuters.com/business/finance

Technology
----------

• AI Breakthrough in Medical Diagnosis Announced [POSITIVE]
  Source: TechCrunch | Published: Mon, 15 Dec 2024 05:00:00 GMT
  Researchers at leading medical institutions announced a major breakthrough in AI-powered medical diagnosis. The new system can detect early-stage cancers with 95% accuracy...
  Key Topics: artificial intelligence, medical diagnosis, machine learning, healthcare technology, cancer detection
  Read more: https://techcrunch.com/ai-medical-breakthrough

• Major Tech Company Announces Quantum Computing Milestone [POSITIVE]
  Source: TechCrunch | Published: Sun, 14 Dec 2024 22:00:00 GMT
  A leading technology company announced it has achieved quantum supremacy in a new class of problems. The quantum computer solved a problem that would take classical computers...
  Key Topics: quantum computing, quantum supremacy, technology innovation, computational breakthrough
  Read more: https://techcrunch.com/quantum-milestone

• Cybersecurity Concerns Rise After Major Data Breach [NEGATIVE]
  Source: TechCrunch | Published: Sat, 13 Dec 2024 18:00:00 GMT
  A major data breach affecting millions of users has raised concerns about cybersecurity practices. The incident exposed personal information including names, emails, and...
  Key Topics: cybersecurity, data breach, information security, privacy concerns, digital safety
  Read more: https://techcrunch.com/data-breach

============================================================
This is an automated daily news summary. Stay informed!
```

## Key Features

1. **Sentiment Indicators**: Each article shows its sentiment (POSITIVE, NEGATIVE, NEUTRAL) with color-coded badges in HTML
2. **Organized by Category**: Articles are automatically categorized into World, Business, Technology, Health, Science, and General
3. **Rich Metadata**: Each article includes source, publication date, summary, and key topics
4. **Professional Formatting**: Clean HTML design with responsive layout for email clients
5. **Plain Text Alternative**: Includes plain text version for email clients that don't support HTML

## Customization

The email template can be customized by modifying the `generate_email_content` method in `lambda_function.py`. You can:
- Change color schemes
- Adjust category names
- Modify article limits per category
- Add custom sections
- Change date formatting


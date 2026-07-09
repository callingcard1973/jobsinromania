# Research: API HEALTH AGENT (IDEA-055)
Date: 2026-04-16

## Description
Monitorizeza API-uri (Kiwi, Brevo, Travelpayouts etc). Fallback automat daca pica. Uptime = bani.

## Market Size
- Application performance monitoring: $3.5B+ market
- UptimeRobot monitors millions of sites
- API economy growing = monitoring demand grows with it

## Competitors

| Tool | Free Tier | Paid/mo | Monitors | Interval |
|------|-----------|---------|----------|----------|
| UptimeRobot | 50 monitors | $7-8 | Unlimited | 1 min |
| Pingdom | Trial only | $15-19 | 10-150 | 1 min |
| Better Stack | 10 monitors | $24+ | 50+ | 30 sec |
| StatusCake | 10 monitors | $20+ | Unlimited | 30 sec |
| Uptime Kuma | Self-hosted | $0 | Unlimited | 20 sec |
| HetrixTools | 15 monitors | $10+ | 50+ | 1 min |
| OneUptime | Open source | $0-99 | Unlimited | Custom |
| Checkly | 5 checks | $30+ | API-focused | 10 sec |

## Our Advantage
- Uptime Kuma = free, self-hosted, fits our stack (raspibig)
- Need monitoring: Brevo (11 keys), Mailrelay, Gmail SMTP, Kiwi API, LLM
- Auto-fallback = unique (most tools only alert)
- Already have Telegram alerts + multi-provider email failover

## Validated?
YES -- Lost emails when 6 Brevo keys died. Auto-failover would have prevented loss. UptimeRobot free tier handles basics.

## Price
Internal tool. UptimeRobot free (50 monitors) or Uptime Kuma ($0). Prevents campaign interruptions.

## Risk
- VERY LOW: Simple implementation, free tools available
- Fallback logic already partially exists in send_campaign.py

## Recommendation
BUILD QUICK -- UptimeRobot free (50 monitors) for external APIs + fallback logic in campaign scripts. 2-hour setup. Should have done this after the 6 dead Brevo keys incident.

## Sources
- [UptimeRobot: 11 Best Monitoring Tools 2026](https://uptimerobot.com/knowledge-hub/monitoring/11-best-uptime-monitoring-tools-compared/)
- [OneUptime: 10 Best Pingdom Alternatives 2026](https://oneuptime.com/blog/post/2026-03-11-10-best-pingdom-alternatives-2026/view)
- [Hyperping: Pingdom vs UptimeRobot](https://hyperping.com/blog/pingdom-vs-uptimerobot-vs-hyperping)

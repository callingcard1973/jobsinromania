# COMPLETE Ticket & Travel Reselling Landscape (2026-04-12)

> From anywhere to anywhere. Flights, trains, buses, ferries, attractions, tours, events, transfers, insurance, cruises, car rental.
> Includes unified aggregator APIs, Romanian market analysis, B2B platforms.

---

## 0. UNIFIED FLIGHT AGGREGATOR APIs (NDC + GDS + LCC in one)

### Startup-Friendly (no IATA, self-service):

| Platform | Coverage | Pricing | Signup | Markup |
|----------|---------|---------|--------|--------|
| **Duffel** | 300+ airlines (NDC+GDS+LCC) | $3 + 1% per ticket. Searches free (1500:1 ratio) | duffel.com — instant | YES, you set price |
| **Kiwi Tequila** | 800+ airlines + virtual interlining | Free (3% affiliate commission) | affiliates@kiwi.com | NO, commission only |
| **DRCT** | NDC+GDS+LCC normalized | Fixed fee per ticketed reservation only, no subscription | drct.aero | YES |
| **Amadeus Self-Service** | Full GDS inventory | Free test, pay-per-call production | developers.amadeus.com/register — instant | Search only (booking = Enterprise) |

### Mid-Tier (sales contact, but accessible):

| Platform | Coverage | Pricing | Signup | Notes |
|----------|---------|---------|--------|-------|
| **TPConnects Iris** | 4 GDS + 60+ NDC/LCC airlines | Contact sales | tpconnects.com | Built-in markup engine, sub-agent hierarchy |
| **AirGateway** | 35+ airlines NDC-only | €108/mo + ~€1/booking + €2,500 setup | airgateway.com/pricing | Needs IATA |
| **TBO** | 600+ airlines + 400K hotels, 70K agencies | Agency license needed | tbo.com | India-origin B2B distributor |
| **PKFARE** | 600 airlines wholesale | Contact sales | pkfare.com | China-origin, needs IATA for suppliers |
| **Mystifly** | 700+ airlines (largest) | Per-transaction, contact sales | mystifly.com | 2,500+ travel businesses served |

### Enterprise (contract required):

| Platform | Coverage | Notes |
|----------|---------|-------|
| **Travelfusion** | 220+ LCC+FSC+NDC+rail | Largest LCC pool, 5B+ searches/year |
| **Verteil** | 50+ airlines NDC | NDC-focused, mid-size agencies welcome |
| **TripStack** | LCC+FSC+virtual interlining | Specializes in combining non-interlining airlines |
| **NUUA Flights** | 100+ GDS+NDC+LCC | Strong Asia-Pacific |
| **HitchHiker** | GDS+NDC+LCC | Smart rule engine picks best source per route |
| **Farelogix/Accelya** | Airline-side NDC (not for resellers) | Powers 57% of all NDC sales globally |
| **Gordian Software** | Ancillary-only (seats, bags, upgrades) | 100+ airlines, complement to booking API |

### Best Path for InterJob:
1. **Start with Duffel** — no IATA, $3+1% per ticket, self-service, set your own markup
2. **Add Kiwi Tequila** — free, 800+ airlines, for affiliate links in emails
3. **Grow to TPConnects Iris or Mystifly** — when volume justifies enterprise deal

---

## 1. FLIGHTS — See FLIGHT_APIs_RESEARCH.md (60+ programs)

**Top instant:** Travelpayouts, eSKY Linker, Amadeus
**Top networks:** CJ (airlines), Awin (OTAs), Impact (metasearch)
**Top margin:** Duffel (own markup), Sub-agent IATA (€30-100/ticket)

---

## 2. TOURS, ACTIVITIES & ATTRACTIONS

### Major OTAs (highest volume):

| Platform | Commission | Signup | Approval | API | Reseller |
|----------|-----------|--------|----------|-----|----------|
| **Viator** (TripAdvisor) | 8% | viator.com/affiliates | Instant (aff), Manual (API) | Full REST for distributors | YES — white-label |
| **GetYourGuide** | 8% | partner.getyourguide.com | Manual 1-5d | REST API for distributors | YES — Supply API |
| **Klook** | 3-5% | affiliate.klook.com | Instant (Impact) | Affiliate API + enterprise booking | YES — B2B net rates |
| **Musement** (TUI) | 6-8% | musement.com/affiliates | Manual | Full REST API | YES — white-label |
| **Tiqets** | 5-8% aff, net rates distrib | tiqets.com/venues/distributors | Manual | Full REST booking API | YES — distributor program |
| **Headout** | 6-10% | headout.com/affiliates | Manual (Impact) | Deeplinks + select API | Limited |
| **Civitatis** | ~5-8% (50% of their comm) | civitatis.com/en/affiliates | **INSTANT** | Deeplinks, widgets, CSV, API at volume | Partial |
| **GuruWalk** | €0.50-1/booking | guruwalk.com/affiliates | Instant | Deeplinks only | NO |

### B2B Reseller Platforms (you set markup):

| Platform | Model | Signup | API |
|----------|-------|--------|-----|
| **Bokun** (TripAdvisor) | Net rates + your markup | bokun.io | Full REST — search, book, manage |
| **Rezdy** | Net rates + your markup | rezdy.com/reseller-channel | Full REST for agents |
| **FareHarbor** | 10-20% agent commission | fareharbor.com/affiliates | REST API + widgets |
| **Peek Pro** | 10-20% agent commission | peek.com/pro/partners | REST API |
| **Checkfront** | Net rates from operators | checkfront.com/partners | REST API |
| **Xola** | Operator-set commissions | xola.com/partners | REST API |
| **Regiondo** | Net rates + your markup | regiondo.com/reseller | Full REST — strong EU |

---

## 3. TRANSPORT

### Trains:
| Platform | Commission | Signup | API | Reseller |
|----------|-----------|--------|-----|----------|
| **Trainline** | 2-4% CPA | trainline.com/affiliates | Deeplinks+widgets (via Awin) | NO |
| **Omio** | 4-6% CPA | omio.com/affiliate (via CJ) | Deeplinks | NO |
| **Rail Europe** | Net rates for agents | partners.raileurope.com | Full booking API | YES |

### Buses:
| Platform | Commission | Signup | Reseller |
|----------|-----------|--------|----------|
| **FlixBus** | 3-5% | flixbus.com/company/affiliate (via Awin) | NO |
| **BlaBlaCar** | ~2% | Via Awin | NO |

### Ferries:
| Platform | Commission | Signup | Reseller |
|----------|-----------|--------|----------|
| **Direct Ferries** | 50% of DF comm (~2-5%) | directferries.com/affiliates.htm (via Awin) | NO |
| **Ferryhopper** | CPA | ferryhopper.com/en/affiliates | NO |

### Airport Transfers:
| Platform | Commission | Signup | API | Reseller |
|----------|-----------|--------|-----|----------|
| **GetTransfer** | 4-10% | gettransfer.com/en/affiliate | REST API | YES — white-label |
| **Hoppa** (HolidayTaxis) | 10-15% | hoppa.com/en/affiliates (via Awin) | API+widgets | YES — white-label |
| **KiwiTaxi** | 30-50% of their comm | kiwitaxi.com/partners | API+widgets | YES — white-label |
| **Mozio** | Aggregator | mozio.com/en-us/affiliates | API+white-label | YES |

---

## 4. EVENTS & ENTERTAINMENT

| Platform | Commission | Signup | API |
|----------|-----------|--------|-----|
| **Ticketmaster** | 4-6% CPA | developer.ticketmaster.com + via CJ | Discovery API (free) |
| **StubHub** | 4-6% CPA | Via CJ | Deeplinks |
| **Eventbrite** | Organizer-set | eventbrite.com/platform/api | Free REST API |
| **Fever** | 4-8% | feverup.com/affiliates (via Impact) | Deeplinks |

---

## 5. CAR RENTAL

| Platform | Commission | Signup | API | Reseller |
|----------|-----------|--------|-----|----------|
| **Rentalcars.com** | ~4-6% (40% of their comm) | rentalcars.com/affiliates | API at volume | YES — white-label |
| **Auto Europe** | ~5% (40-50% of their comm) | autoeurope.com/affiliates | Deeplinks+widgets+phone | YES — agent net rates |
| **Discovercars.com** | ~6% (50-70% of their comm) | discovercars.com/affiliates | Widgets+API | Partial |

---

## 6. TRAVEL INSURANCE

| Platform | Commission | Signup | Reseller |
|----------|-----------|--------|----------|
| **World Nomads** | 10% per policy | worldnomads.com/affiliate (via Impact) | NO |
| **SafetyWing** | 10% recurring | safetywing.com/affiliates | NO |
| **Allianz Travel** | 15-25% | Via CJ | NO |
| **Heymondo** | 15-20% | heymondo.com/affiliates | YES — white-label |

---

## 7. CRUISES

| Platform | Commission | Signup |
|----------|-----------|--------|
| **CruiseDirect** | $50-200/booking | Via CJ |
| **Cruise Critic** | CPA varies | Via TripAdvisor |

---

## 8. MULTI-VERTICAL AGGREGATORS (one signup = everything)

| Platform | What It Covers | Signup | Commission |
|----------|---------------|--------|-----------|
| **Travelpayouts** | Flights, hotels, cars, tours, insurance, transfers | travelpayouts.com | Varies by program, 50-70% rev share |
| **TripAdvisor** | Hotels (CPC), experiences (CPA via Viator) | tripadvisor.com/affiliates | Varies |
| **Expedia Partner Solutions** | Hotels, flights, cars, activities | expediapartnersolutions.com | Full booking API, rev share | 

---

## PRIORITY SIGNUP ORDER — MAXIMUM COVERAGE

### DAY 1 (instant, 30 min):
1. **Travelpayouts** — flights + hotels + cars + tours + insurance in one
2. **Civitatis** — tours/activities, instant, 5-8%
3. **Klook** — attractions, instant via Impact
4. **eSKY Linker** — flights 20-40%, no approval

### DAY 2-3 (quick approval):
5. **CJ Affiliate** → Turkish, Emirates, Qatar, Ticketmaster, StubHub, CruiseDirect, Allianz
6. **Awin** → Booking.com, FlixBus, Direct Ferries, Hoppa, EasyJet, eDreams
7. **Impact** → Skyscanner, Omio, Headout, World Nomads, Fever
8. **Viator** affiliate → 300K+ tours, 8%

### WEEK 1 (apply within networks):
9. GetYourGuide partner
10. Tiqets distributor (net rates, API)
11. Musement affiliate
12. KiwiTaxi partner (30-50%)
13. GetTransfer affiliate

### WEEK 2 (B2B reseller, higher margin):
14. **Duffel** — flight tickets with own markup
15. **Bokun** — tours B2B marketplace
16. **Rezdy** — agent reseller channel
17. **Rail Europe** — train booking API

---

## REVENUE MODEL — ALL VERTICALS

| Vertical | Est. Monthly | Key Programs |
|----------|-------------|-------------|
| Flights | €1,000-15,000 | Travelpayouts, airlines, Duffel, IATA sub-agent |
| Tours & Activities | €500-5,000 | Viator, GetYourGuide, Civitatis, Tiqets |
| Trains+Buses+Ferries | €200-1,000 | Omio, Trainline, FlixBus, Direct Ferries |
| Transfers | €300-2,000 | Hoppa, KiwiTaxi, GetTransfer |
| Car Rental | €200-1,500 | Rentalcars, Discovercars |
| Events | €100-500 | Ticketmaster, Fever |
| Insurance | €200-1,000 | World Nomads, SafetyWing, Heymondo |
| Cruises | €100-500 | CruiseDirect |
| **TOTAL** | **€2,600-26,500/mo** | Scales with traffic |

Combined with IATA sub-agent flights: **€5,000-40,000/mo potential**

---

## 9. ROMANIA-SPECIFIC

### Museums & Attractions in Romania

Most Romanian museums sell tickets at the door only. **No national ticketing platform exists.**

Online tickets available for:
- **Castelul Bran** — bfrcastle.com (own site, no affiliate)
- **Castelul Peles** — own site, limited online
- **Salina Turda** — salinaturda.eu (own site, no affiliate)
- **Palatul Parlamentului** — cdep.ro (own site, no affiliate)
- **Muzeul National de Arta / Muzeul Satului** — door only, no online

**International platforms covering Romania (with affiliate):**
| Platform | RO Attractions Listed | Commission |
|----------|----------------------|-----------|
| **Tiqets** | Bran, Peles, Salina Turda, Bucharest tours | 6-8% |
| **GetYourGuide** | Bucharest, Bran, Brasov, Sibiu | 8% |
| **Viator** | 200+ Romania experiences | 8% |
| **Civitatis** | Bucharest, Transylvania | 5-8% |

**Opportunity:** Romania coverage is thin on these platforms — you could ALSO become a supplier (list your own tours) and earn 80%+ instead of 8%.

### Concert/Event Tickets in Romania

| Platform | Market Share | Affiliate |
|----------|-------------|-----------|
| **iaBilet.ro** | ~70% (largest) | **NO** affiliate program |
| **Eventim.ro** | ~20% | **NO** |
| **bilete.ro** | ~5% | **NO** |
| **MyTicket.ro** | Small | **NO** |
| **Entertix.ro** | Small | **NO** |
| **StubHub** | Minimal RO | YES — via CJ, 4-6% |
| **Viagogo** | Secondary market | YES — ~5-10% |

**Bottom line:** No Romanian concert platform has affiliate program. Only international secondary market (StubHub/Viagogo) works, with limited inventory.

---

## 10. ACCOMMODATION (instead of Airbnb)

**Airbnb affiliate program — DISCONTINUED (2021). No public API. Dead end.**

| Platform | Commission | Signup | API |
|----------|-----------|--------|-----|
| **Booking.com** | 25-40% of their commission | partnerships.booking.com | YES — full API |
| **Hotels.com** (Expedia) | 4-6% | Via Impact/CJ | Deeplinks |
| **Hostelworld** | 2-4% | Direct | Deeplinks |
| **TripAdvisor Hotels** | 50% of ad revenue/click | tripadvisor.com/affiliates | CPC |
| **Agoda** | 4-6% | Via Travelpayouts | Deeplinks+widgets |

**Booking.com is the clear winner** — best Romania coverage, highest commissions, full API available.

---

## UPDATED REVENUE MODEL — ALL VERTICALS

| Vertical | Est. Monthly | Key Programs |
|----------|-------------|-------------|
| Flights | €1,000-15,000 | Travelpayouts, airlines, Duffel, IATA |
| Tours & Activities | €500-5,000 | Viator, GetYourGuide, Civitatis, Tiqets |
| Accommodation | €500-3,000 | Booking.com (25-40%) |
| Trains+Buses+Ferries | €200-1,000 | Omio, Trainline, FlixBus |
| Transfers | €300-2,000 | Hoppa, KiwiTaxi, GetTransfer |
| Car Rental | €200-1,500 | Rentalcars, Discovercars |
| Events | €100-500 | Ticketmaster, Fever, Viagogo |
| Insurance | €200-1,000 | World Nomads, SafetyWing, Heymondo |
| Cruises | €100-500 | CruiseDirect |
| **TOTAL** | **€3,100-29,500/mo** | Scales with traffic |

Combined with IATA sub-agent: **€6,000-45,000/mo potential**

---

## 11. ROMANIA TRAVEL MARKET — AGGREGATOR LANDSCAPE

### Existing Aggregators in Romania:

| Platform | What It Does | Scale |
|----------|-------------|-------|
| **BJR Vacante** (bjr-vacante.ro) | Compares offers from 140+ German+Romanian tour operators + 700 airlines | Closest to real aggregator |
| **OcaziiTuristice.ro** | Aggregates real-time rates from Karpaten, Dertour, Coral Travel, Anex, JoinUp | Active since 2011 |
| **Infoturism.ro** | Portal with offers + agency directory | More listing than comparator |
| **Litoralulromanesc.ro** | 500+ accommodations, Romanian seaside only | Licensed agency (#536), niche |

### Major Romanian OTAs (own inventory, NOT aggregators):

| OTA | Status | Notes |
|-----|--------|-------|
| **Vola.ro** | ALIVE, #1 Romanian OTA | Airline search, owned by Daniel Truica + 3TS Capital |
| **Paravion** | ALIVE, 3rd largest agency | Also large online player |
| **eSky.ro** | ALIVE | Polish-origin, strong in RO |
| **Christian Tour** | ALIVE, major player | Own booking engine, IATA accredited |
| **Paralela 45** | ALIVE, largest traditional | IATA accredited, B2B division |
| **Karpaten** | ALIVE | Part of DER Touristik |

### B2B Travel in Romania:

| Platform | What |
|----------|------|
| **Travel Time** (travel-time.ro) | B2B flight consolidator for corporate |
| **Smart Tours DMC** | B2B white-label for inbound Romania |
| No true B2B multi-agency marketplace exists |

### THE GAP:

**Romania has NO dominant travel aggregator like Skyscanner/Kayak that pulls from all local agencies.** BJR Vacante is closest with 140 operators but low brand awareness. The market is fragmented — each major agency runs its own engine.

**This is an opportunity:** Build an aggregator page on expatsinromania.org or interjob.ro that:
- Uses Travelpayouts/Duffel for flight search
- Uses Booking.com API for accommodation
- Uses Viator/GetYourGuide for activities
- Uses Omio for trains/buses
- All through affiliate links = commission on everything
- Target: expats + workers coming to/from Romania
- **You become the Romanian Skyscanner for the working class**

"""Deploy enriched Schema.org markup to all job sites.

Adds to each site's homepage (index.html):
- Organization schema (full details, contactPoint, areaServed)
- FAQPage schema (5 niche-specific Q&As per site)
- EmploymentAgency schema
- BreadcrumbList schema

Injects via cPanel API — same mechanism as seo_deploy.py.
"""
import urllib.request, urllib.parse, json, ssl, os, sys, time, re
from datetime import date

API_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = "/home/loaiidil"
TODAY = date.today().isoformat()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

DOCROOT_OVERRIDES = {
    "warehouseworkers.eu": f"{HOME}/public_html/warehouseworkers.eu",
}

COUNTRIES = ["Germany", "Netherlands", "Belgium", "Austria", "Denmark", "Switzerland"]

# ── Site definitions with FAQ content ─────────────────────────────────────────
SITES = {
    "careworkers.eu": {
        "title": "Care Workers EU",
        "desc": "Healthcare & elderly care jobs in Europe",
        "niche": "healthcare and elderly care",
        "faqs": [
            ("What qualifications do I need for care work in Europe?",
             "Most European care positions require basic nursing or caregiving certification. Germany requires a recognized nursing qualification (Pflegefachkraft) or willingness to complete a recognition process. Netherlands and Belgium accept equivalent qualifications with language requirements. We help with credential recognition."),
            ("How much do care workers earn in Europe?",
             "Care worker salaries in Europe range from €1,800 to €3,500 per month depending on country and experience. Germany offers €2,200-€3,200/month, Netherlands €2,000-€3,000/month, and Switzerland €3,500-€5,000/month. Many positions include free or subsidized housing."),
            ("Do I need to speak the local language?",
             "Basic language skills are usually required. Germany typically requires B1-B2 German level. Netherlands may accept English in some facilities. We provide guidance on language requirements and resources for each destination country."),
            ("Can I bring my family when working as a care worker in Europe?",
             "Yes, most EU work permits allow family reunification after establishing employment. Timelines vary: Germany allows it immediately with sufficient income, Netherlands after 3-6 months. We assist with the process."),
            ("How long does the visa and work permit process take?",
             "Processing times vary by country: Germany 4-8 weeks, Netherlands 2-4 weeks, Belgium 4-12 weeks, Austria 6-12 weeks. We handle the paperwork and guide you through every step of the application process."),
        ],
    },
    "factoryjobs.eu": {
        "title": "Factory Jobs EU",
        "desc": "Factory & manufacturing jobs in Europe",
        "niche": "factory and manufacturing",
        "faqs": [
            ("What types of factory jobs are available in Europe?",
             "European factories hire for production line operators, quality control inspectors, machine operators, welders, CNC operators, packaging staff, forklift drivers, and warehouse workers. Sectors include automotive, food processing, electronics, plastics, and metal fabrication."),
            ("How much do factory workers earn in Europe?",
             "Factory worker salaries range from €1,600 to €3,000 per month. Germany offers €1,800-€2,800/month, Netherlands €1,900-€2,700/month, Belgium €2,000-€2,800/month. Overtime, shift bonuses, and holiday pay often add 20-30% to base salary."),
            ("Do I need previous factory experience?",
             "Many entry-level positions require no prior experience — employers provide on-the-job training. Specialized roles like CNC operators, welders, or quality inspectors may require certifications. Having forklift certification is a significant advantage."),
            ("Is accommodation provided for factory workers?",
             "Many European employers provide free or subsidized housing for international factory workers. This is especially common in Germany, Netherlands, and Belgium. Housing is typically shared apartments near the workplace, with costs deducted from salary (€200-€400/month) if not free."),
            ("What documents do I need to work in a European factory?",
             "You need a valid passport, work permit (we assist with this), health insurance, and any relevant certifications. EU citizens can work freely. Non-EU citizens need a work visa — we handle the application process, including document translation and apostille."),
        ],
    },
    "buildjobs.eu": {
        "title": "Build Jobs EU",
        "desc": "Construction & building jobs in Europe",
        "niche": "construction and building",
        "faqs": [
            ("What construction jobs are in demand in Europe?",
             "Europe has high demand for scaffolders, concrete workers, carpenters, rebar workers, heavy equipment operators, electricians, plumbers, painters, and general laborers. Germany, Netherlands, and Belgium have the most openings due to major infrastructure projects."),
            ("How much do construction workers earn in Europe?",
             "Construction salaries range from €1,800 to €4,000 per month. Germany: €2,000-€3,500/month, Netherlands: €2,200-€3,200/month, Switzerland: €4,000-€6,000/month. Skilled trades (electricians, welders) earn 30-50% more than general laborers."),
            ("Do I need certifications for construction work in Europe?",
             "Basic safety certification (VCA/SCC) is required in most EU countries. Specialized trades need recognized qualifications. Germany requires Gesellenbrief for skilled trades. We help with certification recognition and safety training."),
            ("Are construction jobs seasonal in Europe?",
             "Construction in Europe runs year-round, though outdoor work may slow in winter (December-February) in northern countries. Indoor finishing work, renovation, and infrastructure projects continue through winter. Many employers offer year-round contracts."),
            ("What safety standards apply to construction workers in Europe?",
             "European construction follows strict EU safety directives. All workers receive safety training, personal protective equipment (PPE), and regular health checks. Working hours are regulated (max 48h/week). Insurance and accident coverage are mandatory for all workers."),
        ],
    },
    "electricjobs.eu": {
        "title": "Electric Jobs EU",
        "desc": "Electrical & technical jobs in Europe",
        "niche": "electrical and technical",
        "faqs": [
            ("What electrical qualifications are recognized in Europe?",
             "EU member states recognize qualifications through the European Qualifications Framework (EQF). Electricians typically need an equivalent of EQF Level 3-4. Germany requires Gesellenbrief or equivalent, Netherlands requires VCA certification. We assist with credential recognition."),
            ("How much do electricians earn in Europe?",
             "Electricians earn €2,200 to €4,500 per month in Europe. Germany: €2,500-€3,800/month, Netherlands: €2,400-€3,500/month, Switzerland: €4,500-€6,500/month. Industrial electricians and automation specialists earn 20-40% premiums."),
            ("What types of electrical jobs are available?",
             "Positions include residential electricians, industrial electricians, automation technicians, PLC programmers, solar panel installers, EV charging station technicians, maintenance electricians, and high-voltage specialists. Green energy jobs are growing fastest."),
            ("Do I need to speak the local language for electrical work?",
             "Technical English is often sufficient for industrial settings. However, basic local language skills improve job prospects and safety. Germany typically requires A2-B1 German. We provide language resources and help match you with English-friendly employers."),
            ("Is there demand for electricians in Europe?",
             "Yes, electricians are among the most in-demand skilled trades in Europe. The green energy transition (solar, wind, EV infrastructure) has created thousands of new positions. Germany alone needs 400,000+ skilled tradespeople by 2030."),
        ],
    },
    "farmworkers.eu": {
        "title": "Farm Workers EU",
        "desc": "Agricultural & farming jobs in Europe",
        "niche": "agricultural and farming",
        "faqs": [
            ("What types of farm jobs are available in Europe?",
             "European farms hire for crop harvesting, greenhouse work, fruit picking, vegetable processing, livestock care, dairy farming, tractor operation, irrigation management, and organic farming. Peak seasons are spring-autumn, but greenhouse work is year-round."),
            ("How much do farm workers earn in Europe?",
             "Farm worker wages range from €1,400 to €2,500 per month. Netherlands: €1,800-€2,400/month (greenhouse), Germany: €1,600-€2,200/month, Denmark: €2,200-€3,000/month. Seasonal workers often earn piece-rate bonuses during harvest."),
            ("Is accommodation provided for farm workers?",
             "Yes, most European farms provide free or low-cost housing for seasonal and permanent workers. Accommodation is typically on or near the farm. Netherlands greenhouse employers commonly provide shared housing included in the employment package."),
            ("Do I need farming experience?",
             "Many positions accept workers with no prior farming experience, especially seasonal harvest jobs. Greenhouse work, livestock management, and tractor operation may require basic experience or training. Employers provide on-site training."),
            ("What is the visa process for seasonal farm work in Europe?",
             "EU seasonal worker permits are available for non-EU citizens for up to 9 months. Germany offers seasonal work visas, Netherlands has the TWV permit for agriculture. Processing takes 2-8 weeks. We handle all paperwork and coordination with employers."),
        ],
    },
    "horecaworkers.eu": {
        "title": "Horeca Workers EU",
        "desc": "Hotel, restaurant & catering jobs in Europe",
        "niche": "hotel, restaurant, and catering (HoReCa)",
        "faqs": [
            ("What HoReCa jobs are available in Europe?",
             "European hospitality offers positions for chefs, cooks, waiters, bartenders, hotel receptionists, housekeeping staff, kitchen assistants, baristas, and restaurant managers. Tourism hotspots in Austria, Switzerland, and Netherlands have the highest demand."),
            ("How much do hospitality workers earn in Europe?",
             "HoReCa salaries range from €1,500 to €4,000 per month. Chefs: €2,200-€4,000/month, Waiters: €1,500-€2,500/month plus tips, Hotel staff: €1,600-€2,800/month. Switzerland and Scandinavia offer the highest wages. Many positions include meals and accommodation."),
            ("Do I need hospitality qualifications?",
             "Entry-level positions (kitchen assistant, housekeeping, dishwasher) often require no formal qualifications. Chef positions typically require culinary training or 2+ years experience. Hotel reception may require language skills. We match your experience level with appropriate positions."),
            ("Is accommodation included with HoReCa jobs?",
             "Many European hospitality employers provide staff accommodation, especially in tourist areas, ski resorts, and remote locations. Hotels commonly offer free rooms for staff. Restaurant jobs in cities may provide housing allowance (€200-€500/month) instead."),
            ("What languages do I need for hospitality work in Europe?",
             "English is widely accepted in international hotels and tourist areas. Basic local language improves earning potential. German for Austria/Germany/Switzerland, French for Belgium, Dutch for Netherlands. Kitchen positions often require minimal language skills."),
        ],
    },
    "meatworkers.eu": {
        "title": "Meat Workers EU",
        "desc": "Meat processing & food industry jobs in Europe",
        "niche": "meat processing and food industry",
        "faqs": [
            ("What meat processing jobs are available in Europe?",
             "European meat processors hire for slaughterhouse line workers, butchers, meat cutters, deboners, quality control inspectors, packaging operators, cold storage workers, and sanitation staff. Germany, Netherlands, and Denmark are the largest employers."),
            ("How much do meat processing workers earn in Europe?",
             "Meat processing wages range from €1,700 to €3,000 per month. Germany: €1,800-€2,600/month (post-2021 labor law reforms), Netherlands: €1,900-€2,800/month, Denmark: €2,500-€3,500/month. Overtime and shift premiums add 15-25%."),
            ("What are working conditions in European meat processing?",
             "EU regulations ensure strict safety standards: temperature-controlled environments, regular breaks, maximum 48-hour work weeks, mandatory PPE, and health checks. Germany's 2021 reforms banned subcontracting in meat processing, ensuring direct employment with full benefits."),
            ("Do I need experience for meat processing work?",
             "Many positions accept workers without prior experience — employers provide 1-2 weeks of on-the-job training. Skilled butcher/deboner roles may require certification or 1+ years experience. Physical fitness is important due to the demanding nature of the work."),
            ("Is the work year-round?",
             "Yes, meat processing is a year-round industry with stable employment. Demand increases before holidays (Christmas, Easter) with overtime opportunities. Most contracts are permanent after an initial trial period of 1-3 months."),
        ],
    },
    "mechanicjobs.eu": {
        "title": "Mechanic Jobs EU",
        "desc": "Mechanic & automotive jobs in Europe",
        "niche": "mechanic and automotive",
        "faqs": [
            ("What mechanic jobs are available in Europe?",
             "European automotive sector hires for car mechanics, truck/bus technicians, auto electricians, body repair specialists, paint technicians, heavy equipment mechanics, motorcycle technicians, and EV/hybrid specialists. Germany has the largest automotive job market."),
            ("How much do mechanics earn in Europe?",
             "Mechanic salaries range from €2,000 to €4,000 per month. Germany: €2,200-€3,500/month, Netherlands: €2,100-€3,200/month, Switzerland: €4,000-€5,500/month. EV specialists and diagnostic technicians command 20-30% premium over general mechanics."),
            ("What certifications do European employers require?",
             "Most employers require a recognized mechanic qualification (equivalent to EU Level 3). German employers prefer Gesellenbrief. Manufacturer-specific certifications (Bosch, VW, BMW) are a major advantage. We help with credential recognition across EU countries."),
            ("Is there demand for EV mechanics in Europe?",
             "Massive demand. Europe's push to ban combustion engine sales by 2035 has created urgent need for EV-trained technicians. High-voltage certification (EU standard) is increasingly required. Employers often sponsor EV training for experienced mechanics."),
            ("Do mechanic jobs include accommodation?",
             "Some employers, especially in rural areas or for international hires, provide housing or housing allowance. In cities, expect housing allowance of €300-€600/month. We help negotiate accommodation packages as part of your employment offer."),
        ],
    },
    "warehouseworkers.eu": {
        "title": "Warehouse Workers EU",
        "desc": "Warehouse & logistics jobs in Europe",
        "niche": "warehouse and logistics",
        "faqs": [
            ("What warehouse jobs are available in Europe?",
             "European logistics centers hire for order pickers, forklift operators, inventory managers, loading/unloading staff, packaging workers, quality checkers, and warehouse supervisors. Netherlands, Germany, and Belgium have the most openings due to major distribution hubs."),
            ("How much do warehouse workers earn in Europe?",
             "Warehouse worker salaries range from €1,600 to €2,800 per month. Netherlands: €1,800-€2,500/month, Germany: €1,700-€2,600/month, Belgium: €1,900-€2,700/month. Forklift operators earn 15-25% more. Night shifts and weekends add premiums."),
            ("Do I need a forklift license?",
             "A forklift license significantly improves job prospects and salary. Many employers will sponsor forklift training for motivated workers. Common certifications: reach truck, counterbalance, EPT. Training takes 1-5 days depending on type."),
            ("What are the working hours?",
             "European warehouses operate in shifts: day (06:00-14:00), afternoon (14:00-22:00), and night (22:00-06:00). Most contracts are 38-40 hours/week with overtime available. Night and weekend shifts earn 25-50% premium pay."),
            ("Is warehouse work available year-round?",
             "Yes, with peaks during holiday seasons (November-January) and summer. Major logistics hubs (Rotterdam, Hamburg, Antwerp) offer permanent year-round positions. Temporary agencies also provide flexible seasonal opportunities."),
        ],
    },
    "aluminumrecyclehub.com": {
        "title": "Aluminum Recycle Hub",
        "desc": "Recycling industry jobs in Europe",
        "niche": "recycling and waste management",
        "faqs": [
            ("What recycling jobs are available in Europe?",
             "European recycling facilities hire for sorting line operators, material handlers, shredder operators, quality inspectors, waste collection drivers, recycling plant technicians, and environmental compliance officers. The circular economy is creating thousands of new positions."),
            ("How much do recycling workers earn?",
             "Recycling industry salaries range from €1,600 to €2,800 per month. Sorting operators: €1,600-€2,200/month, Plant technicians: €2,200-€3,000/month, Compliance officers: €2,500-€3,500/month. Germany and Netherlands offer the highest wages in this sector."),
            ("Do I need experience in recycling?",
             "Most entry-level positions require no prior experience. Employers provide safety training and on-the-job education. Technical roles (plant maintenance, quality control) may require relevant certifications. Environmental science background is valued for compliance roles."),
            ("Is recycling a growing industry in Europe?",
             "Yes, the EU Circular Economy Action Plan mandates significant increases in recycling rates by 2030. The sector is growing 5-8% annually, creating sustained demand for workers. Investment in recycling infrastructure across Europe exceeds €10 billion annually."),
            ("What safety measures are in place?",
             "EU regulations mandate comprehensive safety protocols: PPE requirements, regular safety training, air quality monitoring, noise protection, and hazardous material handling procedures. All facilities undergo regular inspections and workers receive ongoing health monitoring."),
        ],
    },
    "expatsinromania.org": {
        "title": "Expats in Romania",
        "desc": "Jobs and community for expats in Romania",
        "niche": "expatriate employment in Romania",
        "faqs": [
            ("What jobs are available for expats in Romania?",
             "Romania offers positions for IT professionals, English teachers, international business managers, tourism operators, manufacturing supervisors, and customer service representatives. Bucharest, Cluj-Napoca, and Timișoara have the most international job opportunities."),
            ("What is the average salary for expats in Romania?",
             "Expat salaries in Romania range from €1,000 to €4,000 per month depending on industry. IT: €2,000-€4,000/month, Teaching: €800-€1,500/month, Management: €2,500-€5,000/month. Cost of living is 40-60% lower than Western Europe, making purchasing power strong."),
            ("Do I need a work permit for Romania?",
             "EU/EEA citizens can work freely in Romania. Non-EU citizens need a work permit (Autorizație de Muncă) sponsored by an employer, plus a long-stay visa. Processing takes 30-45 days. We assist with the entire application process."),
            ("What is the cost of living in Romania?",
             "Romania has one of the lowest costs of living in the EU. Monthly expenses: rent €300-€600 (1-bedroom, city center), utilities €100-€150, food €200-€300, transport €30-€50. Total: €700-€1,200/month for a comfortable lifestyle in major cities."),
            ("What languages are spoken in business in Romania?",
             "Romanian is the official language, but English is widely spoken in business, especially in IT, multinational companies, and tourism. French, German, and Italian are also common due to historical ties. Many international companies operate in English."),
        ],
    },
    "interjob.ro": {
        "title": "InterJob Romania",
        "desc": "International job recruitment platform for Europe",
        "niche": "international recruitment",
        "faqs": [
            ("What countries does InterJob recruit for?",
             "InterJob places workers in 6 European countries: Germany, Netherlands, Belgium, Austria, Denmark, and Switzerland. We cover all major sectors: construction, manufacturing, hospitality, healthcare, agriculture, logistics, and automotive."),
            ("How does the application process work?",
             "Apply through our online form at interjob.ro/apply.html. We review your profile within 48 hours, match you with suitable positions, assist with documentation and work permits, and coordinate with employers. The entire process typically takes 2-8 weeks."),
            ("Is InterJob a legitimate recruitment agency?",
             "Yes, InterJob is a registered European recruitment agency operating since 2013. We are compliant with EU recruitment regulations and never charge workers for job placement. Our revenue comes from employer partnerships and placement fees paid by hiring companies."),
            ("What sectors does InterJob cover?",
             "We recruit for: healthcare/elderly care, factory/manufacturing, construction, electrical/technical, agriculture/farming, hospitality (HoReCa), meat processing, warehouse/logistics, automotive/mechanic, and recycling. Each sector has a dedicated website with multilingual content."),
            ("Do I have to pay any fees?",
             "No. Legitimate EU recruitment agencies do not charge workers. InterJob is paid by employers who need workers. All services — job matching, visa assistance, document preparation, and travel coordination — are free for job seekers."),
        ],
    },
    "mivromania.info": {
        "title": "MIV Romania",
        "desc": "Jobs and opportunities in Romania",
        "niche": "employment in Romania",
        "faqs": [
            ("What types of jobs are available through MIV Romania?",
             "MIV Romania connects workers with positions across all major sectors in Europe: manufacturing, construction, hospitality, healthcare, logistics, and agriculture. We specialize in placing Romanian and international workers in EU countries."),
            ("How do I apply for a job?",
             "Visit interjob.ro/apply.html to submit your application. Include your CV, work experience, language skills, and preferred destination country. Our team reviews applications within 48 hours and contacts suitable candidates."),
            ("What support do you provide?",
             "We provide full support: job matching, interview preparation, work permit and visa assistance, travel arrangement, accommodation coordination, and ongoing support after placement. All services are free for job seekers."),
            ("Which countries can I work in?",
             "We place workers in Germany, Netherlands, Belgium, Austria, Denmark, and Switzerland. Each country has different requirements and salary levels. We help you choose the best option based on your skills and preferences."),
            ("How long does placement take?",
             "From application to starting work typically takes 2-8 weeks, depending on the destination country and visa requirements. EU citizens can often start within 2-3 weeks. Non-EU citizens may need 4-8 weeks for work permit processing."),
        ],
    },
    "mivromania.online": {
        "title": "MIV Romania Online",
        "desc": "Jobs and opportunities in Romania",
        "niche": "employment in Romania",
        "faqs": [
            ("What makes MIV Romania Online different?",
             "MIV Romania Online provides a streamlined digital platform for job seekers. Browse positions in 37 languages, submit applications online, and track your placement status. Our platform connects you directly with verified European employers."),
            ("Can I apply from any country?",
             "Yes, we accept applications from workers worldwide. Our multilingual platform supports 37 languages. Non-EU citizens receive full visa and work permit assistance. EU citizens can apply and start work within weeks."),
            ("What salary can I expect?",
             "Salaries vary by country and sector: €1,500-€4,000/month in most positions. Germany and Netherlands offer €1,800-€3,000/month for most roles. Switzerland offers €3,500-€6,000/month. Many positions include housing and transport benefits."),
            ("Is housing provided?",
             "Many European employers provide free or subsidized housing for international workers. This is especially common in manufacturing, agriculture, and hospitality sectors. When housing isn't included, employers often provide a housing allowance of €200-€500/month."),
            ("How do I contact you?",
             "Apply online at interjob.ro/apply.html for the fastest response. You can also reach us through any of our sector-specific websites. We respond to all inquiries within 48 hours during business days."),
        ],
    },
    "nepalezi.com": {
        "title": "Nepalezi",
        "desc": "Jobs for Nepali workers in Europe",
        "niche": "Nepali worker placement in Europe",
        "faqs": [
            ("Can Nepali citizens work in Europe?",
             "Yes, Nepali citizens can work in Europe with a valid work permit. Several EU countries actively recruit from Nepal, especially for hospitality, construction, and manufacturing. We handle the entire visa and work permit process from Nepal to Europe."),
            ("What jobs are available for Nepali workers in Europe?",
             "Popular positions include hotel and restaurant staff (cooks, waiters, housekeeping), construction workers, factory operators, farm workers, and care workers. Germany, Netherlands, and Belgium have the most openings for Nepali workers."),
            ("How much can I earn working in Europe?",
             "Nepali workers in Europe typically earn €1,500-€3,000 per month — significantly more than Nepal average wages. Many positions include free housing and meals. After expenses, workers can save €800-€2,000 per month to send home."),
            ("What documents do I need from Nepal?",
             "You need: valid passport (6+ months validity), educational certificates, work experience letters, police clearance, medical certificate, and passport photos. We guide you through document preparation and handle translations and apostilles."),
            ("How long does it take to get to Europe from Nepal?",
             "The full process from application to arrival in Europe takes 6-12 weeks: 1-2 weeks application review, 2-4 weeks employer matching, 2-6 weeks visa processing. We manage every step and coordinate with the Nepali embassy and European consulates."),
        ],
    },
}

# ── cPanel helpers ────────────────────────────────────────────────────────────
def cpanel_get_file(remote_path):
    dir_part = remote_path.rsplit("/", 1)[0]
    file_part = remote_path.rsplit("/", 1)[1]
    url = f"{HOST}/execute/Fileman/get_file_content?dir={urllib.parse.quote(dir_part)}&file={urllib.parse.quote(file_part)}"
    req = urllib.request.Request(url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"})
    try:
        r = urllib.request.urlopen(req, timeout=30, context=CTX)
        data = json.loads(r.read())
        return data.get("data", {}).get("content", "")
    except Exception as e:
        print(f"  ERR downloading {remote_path}: {e}")
        return None

def cpanel_upload(content_bytes, filename, remote_dir):
    boundary = "----FormBound7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dir"\r\n\r\n'
        f"{remote_dir}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file-1"; filename="{filename}"\r\n'
        f"Content-Type: text/html\r\n\r\n"
    ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30, context=CTX)
            return True
        except Exception as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                print(f"  ERR upload {remote_dir}/{filename}: {e}")
                return False

# ── Schema generators ─────────────────────────────────────────────────────────
def gen_org_schema(site, meta):
    return {
        "@context": "https://schema.org",
        "@type": "EmploymentAgency",
        "name": meta["title"],
        "description": meta["desc"],
        "url": f"https://{site}/",
        "logo": f"https://{site}/favicon.ico",
        "sameAs": [
            "https://interjob.ro/",
            "https://t.me/jobsineurope",
        ],
        "areaServed": [{"@type": "Country", "name": c} for c in COUNTRIES],
        "serviceType": "International Recruitment",
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "recruitment",
            "url": "https://interjob.ro/apply.html",
            "availableLanguage": ["English", "Romanian", "German", "French", "Dutch",
                                   "Arabic", "Nepali", "Hindi", "Urdu", "Russian",
                                   "Ukrainian", "Bulgarian", "Polish"],
        },
        "knowsAbout": [
            f"{meta['niche']} recruitment",
            "European work permits",
            "EU visa assistance",
            "International worker placement",
        ],
        "foundingDate": "2013",
    }

def gen_faq_schema(meta):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a,
                },
            }
            for q, a in meta["faqs"]
        ],
    }

def gen_breadcrumb_schema(site, meta):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": f"https://{site}/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": meta["title"],
                "item": f"https://{site}/",
            },
        ],
    }

# ── Inject schema into HTML ──────────────────────────────────────────────────
def inject_schemas(html, site, meta):
    org = gen_org_schema(site, meta)
    faq = gen_faq_schema(meta)
    breadcrumb = gen_breadcrumb_schema(site, meta)

    # Build schema block
    schemas = "\n".join([
        f'<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script>',
        f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>',
        f'<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>',
    ])

    # Remove any existing EmploymentAgency, FAQPage, BreadcrumbList schemas (avoid duplicates)
    html = re.sub(r'<script type="application/ld\+json">\s*\{[^}]*"@type"\s*:\s*"EmploymentAgency"[^<]*</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script type="application/ld\+json">\s*\{[^}]*"@type"\s*:\s*"FAQPage"[^<]*</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<script type="application/ld\+json">\s*\{[^}]*"@type"\s*:\s*"BreadcrumbList"[^<]*</script>', '', html, flags=re.DOTALL)

    # Inject before </head>
    if '</head>' in html:
        html = html.replace('</head>', schemas + '\n</head>', 1)
    elif '</body>' in html:
        html = html.replace('</body>', schemas + '\n</body>', 1)
    else:
        html = schemas + '\n' + html

    return html

# ── Also inject visible FAQ section into homepage HTML ────────────────────────
def inject_faq_html(html, meta):
    """Add visible FAQ section before footer for SEO + user value."""
    if 'id="faq-section"' in html:
        return html  # Already has FAQ

    faq_items = ""
    for q, a in meta["faqs"]:
        faq_items += f"""<details style="margin-bottom:12px;border:1px solid #e2e8f0;border-radius:8px;padding:0">
<summary style="padding:15px 20px;cursor:pointer;font-weight:600;font-size:1rem;color:#1e293b;background:#f8fafc;border-radius:8px;list-style:none;display:flex;justify-content:space-between;align-items:center">{q}<span style="font-size:1.3rem;color:#065f46;transition:transform .2s">+</span></summary>
<div style="padding:15px 20px;color:#475569;line-height:1.7;font-size:.95rem;border-top:1px solid #e2e8f0">{a}</div>
</details>
"""

    faq_section = f"""<!-- FAQ Section -->
<section id="faq-section" style="max-width:800px;margin:40px auto;padding:20px">
<h2 style="text-align:center;font-size:1.8rem;color:#065f46;margin-bottom:25px">Frequently Asked Questions</h2>
{faq_items}</section>
"""

    # Insert before footer or before </body>
    if '<footer' in html.lower():
        html = re.sub(r'(<footer)', faq_section + r'\1', html, count=1, flags=re.I)
    elif '</body>' in html:
        html = html.replace('</body>', faq_section + '</body>', 1)
    else:
        html += faq_section

    return html

# ── Main ──────────────────────────────────────────────────────────────────────
def deploy_site(site):
    meta = SITES[site]
    docroot = DOCROOT_OVERRIDES.get(site, f"{HOME}/{site}")
    print(f"\n=== {site} ===")

    # Download index.html
    content = cpanel_get_file(f"{docroot}/index.html")
    if content is None:
        print(f"  SKIP: could not download index.html")
        return 0, 1

    # Inject schemas
    html = inject_schemas(content, site, meta)

    # Inject visible FAQ
    html = inject_faq_html(html, meta)

    # Upload
    if cpanel_upload(html.encode("utf-8"), "index.html", docroot):
        print(f"  OK index.html (Organization + FAQPage + BreadcrumbList + visible FAQ)")
        return 1, 0
    return 0, 1

if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(SITES.keys())
    total_ok = total_err = 0
    for site in sites:
        if site not in SITES:
            print(f"SKIP {site}: not configured")
            continue
        ok, err = deploy_site(site)
        total_ok += ok
        total_err += err
        time.sleep(0.5)
    print(f"\nTotal: {total_ok} OK, {total_err} errors across {len(sites)} sites")

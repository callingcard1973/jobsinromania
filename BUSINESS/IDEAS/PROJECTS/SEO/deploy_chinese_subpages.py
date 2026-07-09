"""Deploy full Chinese (zh-CN) subpage structure to all job sites.

Creates for each site:
- /zh.html — homepage (already deployed by deploy_chinese_pages.py)
- /zh/index.html — language landing page
- /zh/de/index.html — Germany jobs page
- /zh/nl/index.html — Netherlands jobs page
- /zh/be/index.html — Belgium jobs page
- /zh/at/index.html — Austria jobs page
- /zh/dk/index.html — Denmark jobs page
- /zh/ch/index.html — Switzerland jobs page
- /zh/faq/index.html — FAQ page
- /zh/salary/index.html — Salary info page
- /zh/visa/index.html — Visa info page
"""
import urllib.request, urllib.parse, json, ssl, sys, time
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

COUNTRIES = {
    "de": {"zh": "德国", "en": "Germany", "min_wage": "€2,080", "salary": "€2,000-€3,500", "vacation": "25+天", "visa_time": "4-8周", "housing": "许多雇主提供免费员工宿舍", "notes": "欧洲最大经济体，工业强国，对技术工人需求极大。"},
    "nl": {"zh": "荷兰", "en": "Netherlands", "min_wage": "€2,070", "salary": "€1,900-€3,200", "vacation": "20+天", "visa_time": "2-4周", "housing": "雇主通常提供共享公寓住宿", "notes": "物流枢纽，鹿特丹港是欧洲最大港口。温室农业发达。"},
    "be": {"zh": "比利时", "en": "Belgium", "min_wage": "€1,995", "salary": "€1,900-€3,000", "vacation": "20天", "visa_time": "4-12周", "housing": "许多雇主提供住房补贴", "notes": "欧盟总部所在地，三语国家（荷兰语、法语、德语）。"},
    "at": {"zh": "奥地利", "en": "Austria", "min_wage": "€1,800", "salary": "€1,800-€3,500", "vacation": "25天", "visa_time": "6-12周", "housing": "旅游区雇主提供免费住宿", "notes": "阿尔卑斯山国家，旅游业和制造业发达。"},
    "dk": {"zh": "丹麦", "en": "Denmark", "min_wage": "€2,500", "salary": "€2,200-€4,000", "vacation": "25天", "visa_time": "4-8周", "housing": "雇主协助安排住房", "notes": "北欧高福利国家，工资水平欧洲最高之一。"},
    "ch": {"zh": "瑞士", "en": "Switzerland", "min_wage": "€3,500", "salary": "€3,500-€6,000", "vacation": "20天", "visa_time": "6-12周", "housing": "雇主提供住房补贴（€500-€1,000/月）", "notes": "全球工资最高的国家之一，精密制造和金融中心。"},
}

SITES = {
    "careworkers.eu": {"zh": "护理", "en": "Care Workers EU", "niche": "医疗保健和老年护理"},
    "factoryjobs.eu": {"zh": "工厂", "en": "Factory Jobs EU", "niche": "工厂和制造业"},
    "buildjobs.eu": {"zh": "建筑", "en": "Build Jobs EU", "niche": "建筑和装修"},
    "electricjobs.eu": {"zh": "电气", "en": "Electric Jobs EU", "niche": "电气和技术"},
    "farmworkers.eu": {"zh": "农业", "en": "Farm Workers EU", "niche": "农业和农场"},
    "horecaworkers.eu": {"zh": "酒店餐饮", "en": "Horeca Workers EU", "niche": "酒店、餐厅和餐饮"},
    "meatworkers.eu": {"zh": "肉类加工", "en": "Meat Workers EU", "niche": "肉类加工和食品工业"},
    "mechanicjobs.eu": {"zh": "汽修", "en": "Mechanic Jobs EU", "niche": "汽车和机械维修"},
    "warehouseworkers.eu": {"zh": "仓库物流", "en": "Warehouse Workers EU", "niche": "仓库和物流"},
    "aluminumrecyclehub.com": {"zh": "回收", "en": "Aluminum Recycle Hub", "niche": "回收和废物管理"},
    "expatsinromania.org": {"zh": "罗马尼亚", "en": "Expats in Romania", "niche": "罗马尼亚外籍就业"},
    "interjob.ro": {"zh": "国际招聘", "en": "InterJob Romania", "niche": "国际招聘"},
    "mivromania.info": {"zh": "罗马尼亚就业", "en": "MIV Romania", "niche": "罗马尼亚就业"},
    "mivromania.online": {"zh": "在线招聘", "en": "MIV Romania Online", "niche": "罗马尼亚在线招聘"},
    "nepalezi.com": {"zh": "亚洲工人", "en": "Nepalezi", "niche": "亚洲工人欧洲就业"},
}

CSS = """<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.8;color:#1e293b;background:#f8fafc}
.hd{background:linear-gradient(135deg,#065f46,#1e3a5f);color:#fff;padding:15px 20px;position:sticky;top:0;z-index:100}
.hdc{max-width:1000px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}
.hdc a{color:#fff;text-decoration:none;font-weight:bold;font-size:1.2rem}
.hdc .nav a{color:#10b981;margin-left:15px;font-size:.9rem}
.hero{background:linear-gradient(135deg,#065f46,#1e3a5f);color:#fff;padding:50px 20px;text-align:center}
.hero h1{font-size:2rem;margin-bottom:10px}
.hero p{opacity:.9;font-size:1.1rem}
.ct{max-width:900px;margin:0 auto;padding:20px}
.section{margin:30px 0}
.section h2{color:#065f46;font-size:1.5rem;margin-bottom:15px;border-bottom:2px solid #10b981;padding-bottom:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px;margin:15px 0}
.card{background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card h3{color:#065f46;margin-bottom:8px}
.card .salary{font-size:1.3rem;font-weight:bold;color:#10b981}
.stat{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f1f5f9}
.stat:last-child{border-bottom:none}
details{margin-bottom:10px;background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
summary{padding:15px 20px;cursor:pointer;font-weight:600;list-style:none}
summary::-webkit-details-marker{display:none}
details div{padding:0 20px 15px;color:#475569;line-height:1.8}
.cta{text-align:center;margin:30px 0;padding:35px;background:linear-gradient(135deg,#065f46,#1e3a5f);border-radius:12px;color:#fff}
.cta a{display:inline-block;padding:15px 40px;background:#10b981;color:#fff;text-decoration:none;border-radius:8px;font-size:1.2rem;font-weight:bold}
.cta a:hover{background:#059669}
.ft{background:#1e293b;color:#fff;padding:20px;text-align:center;font-size:.9rem}
.ft a{color:#10b981;text-decoration:none}
.breadcrumb{padding:10px 20px;font-size:.85rem;color:#64748b;max-width:900px;margin:0 auto}
.breadcrumb a{color:#065f46;text-decoration:none}
@media(max-width:600px){.hero h1{font-size:1.5rem}.grid{grid-template-columns:1fr}}
</style>"""


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
        f"Content-Type: text/html; charset=utf-8\r\n\r\n"
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
                time.sleep(3 * (attempt + 1))
            else:
                print(f"  ERR {remote_dir}/{filename}: {e}")
                return False


def cpanel_mkdir(path):
    url = f"{HOST}/execute/Fileman/mkdir?path={urllib.parse.quote(path)}"
    req = urllib.request.Request(url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"})
    try:
        urllib.request.urlopen(req, timeout=15, context=CTX)
    except:
        pass  # dir may already exist


def nav(site, sm):
    return f"""<header class="hd"><div class="hdc">
<a href="https://{site}/zh.html">{sm["en"]}</a>
<div class="nav"><a href="https://{site}/zh.html">首页</a><a href="https://{site}/">English</a><a href="https://interjob.ro/apply.html">申请</a></div>
</div></header>"""


def footer(site, sm):
    return f"""<footer class="ft">
<p>{sm["en"]} — 欧洲{sm["niche"]}招聘</p>
<p style="margin-top:8px"><a href="https://{site}/zh.html">中文首页</a> · <a href="https://{site}/">English</a> · <a href="https://interjob.ro/apply.html">立即申请</a></p>
<p style="margin-top:8px;opacity:.6">&copy; 2026 {site}</p>
</footer>"""


def gen_lang_index(site, sm):
    """Chinese language landing page with country selection."""
    country_cards = ""
    for code, c in COUNTRIES.items():
        country_cards += f'<a href="/{code}/" class="card" style="text-decoration:none;color:#1e293b"><h3>{c["zh"]} {c["en"]}</h3><div class="salary">{c["salary"]}/月</div><p style="font-size:.85rem;color:#64748b;margin-top:5px">{c["notes"][:30]}...</p></a>\n'

    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>欧洲{sm["niche"]}工作 — 选择国家 | {sm["en"]}</title>
<meta name="description" content="在欧洲6个国家寻找{sm["niche"]}工作。德国、荷兰、比利时、奥地利、丹麦、瑞士。免费签证协助。">
<meta name="keywords" content="欧洲{sm["niche"]}工作,德国{sm["zh"]}工作,荷兰{sm["zh"]}工作,海外务工">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://{site}/zh/">
{CSS}</head><body>
{nav(site, sm)}
<section class="hero"><h1>欧洲{sm["niche"]}工作</h1><p>选择您想工作的国家</p></section>
<div class="breadcrumb"><a href="/zh.html">首页</a> &gt; 选择国家</div>
<div class="ct">
<div class="section"><h2>招聘国家</h2><div class="grid">{country_cards}</div></div>
<div class="grid">
<a href="/zh/faq/" class="card" style="text-decoration:none;color:#1e293b;text-align:center"><h3>常见问题</h3></a>
<a href="/zh/salary/" class="card" style="text-decoration:none;color:#1e293b;text-align:center"><h3>薪资指南</h3></a>
<a href="/zh/visa/" class="card" style="text-decoration:none;color:#1e293b;text-align:center"><h3>签证信息</h3></a>
</div>
<div class="cta"><h2>立即申请</h2><p style="margin:10px 0;opacity:.9">免费 — 48小时内回复</p><a href="https://interjob.ro/apply.html">申请 ➜</a></div>
</div>
{footer(site, sm)}</body></html>"""


def gen_country_page(site, sm, cc, c):
    """Country-specific job page in Chinese."""
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": f"{sm['niche']}工人 — {c['zh']}",
        "description": f"{c['zh']}{sm['niche']}工作，月薪{c['salary']}",
        "datePosted": TODAY,
        "hiringOrganization": {"@type": "Organization", "name": sm["en"], "sameAs": f"https://{site}/"},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressCountry": c["en"]}},
        "baseSalary": {"@type": "MonetaryAmount", "currency": "EUR", "value": {"@type": "QuantitativeValue", "unitText": "MONTH"}},
        "employmentType": "FULL_TIME",
    }, ensure_ascii=False)
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{c["zh"]}{sm["niche"]}工作 — 月薪{c["salary"]} | {sm["en"]}</title>
<meta name="description" content="{c["zh"]}{sm["niche"]}工作招聘。月薪{c["salary"]}。免费住宿和签证协助。{c["notes"]}">
<meta name="keywords" content="{c["zh"]}{sm["zh"]}工作,{c["zh"]}招聘中国工人,{c["en"]} {sm["niche"]} jobs">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://{site}/zh/{cc}/">
<script type="application/ld+json">{schema}</script>
{CSS}</head><body>
{nav(site, sm)}
<section class="hero"><h1>{c["zh"]} — {sm["niche"]}工作</h1><p>{c["notes"]}</p></section>
<div class="breadcrumb"><a href="/zh.html">首页</a> &gt; <a href="/zh/">选择国家</a> &gt; {c["zh"]}</div>
<div class="ct">
<div class="section"><h2>工作详情</h2>
<div class="card">
<div class="stat"><span>月薪</span><span class="salary">{c["salary"]}</span></div>
<div class="stat"><span>最低工资</span><span>{c["min_wage"]}/月</span></div>
<div class="stat"><span>带薪假期</span><span>{c["vacation"]}</span></div>
<div class="stat"><span>签证处理</span><span>{c["visa_time"]}</span></div>
<div class="stat"><span>住宿</span><span>✅ {c["housing"][:20]}...</span></div>
<div class="stat"><span>合法合同</span><span>✅ 正式劳动合同</span></div>
<div class="stat"><span>医疗保险</span><span>✅ 雇主提供</span></div>
</div></div>

<div class="section"><h2>住宿安排</h2><p>{c["housing"]}</p></div>

<div class="section"><h2>为什么选择{c["zh"]}？</h2><p>{c["notes"]}对{sm["niche"]}工人需求旺盛，工作环境优良，福利待遇完善。</p></div>

<div class="cta"><h2>申请{c["zh"]}{sm["niche"]}工作</h2><p style="margin:10px 0;opacity:.9">免费申请 — 签证协助 — 住宿安排</p><a href="https://interjob.ro/apply.html">立即申请 ➜</a></div>
</div>
{footer(site, sm)}</body></html>"""


def gen_faq_page(site, sm):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>常见问题 — 欧洲{sm["niche"]}工作 | {sm["en"]}</title>
<meta name="description" content="欧洲{sm["niche"]}工作常见问题：签证、工资、住宿、申请流程。中国工人赴欧工作指南。">
<meta name="keywords" content="欧洲工作常见问题,签证申请,海外务工FAQ,{sm["niche"]}工作问答">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://{site}/zh/faq/">
{CSS}</head><body>
{nav(site, sm)}
<section class="hero"><h1>常见问题</h1><p>欧洲{sm["niche"]}工作 — 你想知道的一切</p></section>
<div class="breadcrumb"><a href="/zh.html">首页</a> &gt; <a href="/zh/">选择国家</a> &gt; 常见问题</div>
<div class="ct">
<div class="section">
<details open><summary>中国人可以在欧洲做{sm["niche"]}工作吗？</summary><div>可以。中国公民可以通过工作签证在德国、荷兰、比利时、奥地利、丹麦和瑞士合法工作。我们协助办理所有工作许可和签证手续。</div></details>
<details><summary>需要什么资格？</summary><div>许多入门级职位不需要正式资格，雇主提供在职培训。专业岗位可能需要相关证书或1年以上工作经验。我们帮助您的资格获得欧洲认可。</div></details>
<details><summary>工资是多少？</summary><div>工资因国家和岗位而异。德国€2,000-€3,500/月，荷兰€1,900-€3,200/月，瑞士€3,500-€6,000/月。加班费和假日补贴额外增加20-30%。许多职位包含免费住宿。</div></details>
<details><summary>住宿怎么安排？</summary><div>许多欧洲雇主为国际工人提供免费或补贴住房。住宿通常是靠近工作地点的共享公寓。如果不是免费的，住房费用通常从工资中扣除€200-€400/月。</div></details>
<details><summary>需要会当地语言吗？</summary><div>许多岗位接受基本英语。工厂、仓库和农业岗位通常语言要求较低。我们会根据您的语言能力匹配合适的雇主。</div></details>
<details><summary>从申请到出发需要多久？</summary><div>整个过程通常6-12周：1-2周申请审核，2-4周雇主匹配，2-6周签证处理。我们管理每个步骤。</div></details>
<details><summary>需要付中介费吗？</summary><div>不需要。合法的欧盟招聘机构不向工人收费。InterJob由雇主付费。所有服务——工作匹配、签证协助、文件准备——对求职者完全免费。</div></details>
<details><summary>合同是什么样的？</summary><div>正式欧盟劳动合同，包含社会保险、医疗保险、带薪休假、工伤保险。受欧盟劳动法保护，每周最多48小时工作。</div></details>
</div>
<div class="cta"><h2>还有其他问题？</h2><p style="margin:10px 0;opacity:.9">申请后我们的团队会详细解答</p><a href="https://interjob.ro/apply.html">立即申请 ➜</a></div>
</div>
{footer(site, sm)}</body></html>"""


def gen_salary_page(site, sm):
    salary_cards = ""
    for cc, c in COUNTRIES.items():
        salary_cards += f'<div class="card"><h3>{c["zh"]}</h3><div class="salary">{c["salary"]}/月</div><div class="stat"><span>最低工资</span><span>{c["min_wage"]}</span></div><div class="stat"><span>带薪假期</span><span>{c["vacation"]}</span></div></div>\n'

    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>薪资指南 — 欧洲{sm["niche"]}工资 | {sm["en"]}</title>
<meta name="description" content="欧洲{sm["niche"]}工资对比：德国、荷兰、比利时、奥地利、丹麦、瑞士。包含最低工资、带薪假期和住宿信息。">
<meta name="keywords" content="欧洲{sm["niche"]}工资,德国工资,荷兰工资,海外务工收入">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://{site}/zh/salary/">
{CSS}</head><body>
{nav(site, sm)}
<section class="hero"><h1>薪资指南</h1><p>欧洲{sm["niche"]}工作各国工资对比</p></section>
<div class="breadcrumb"><a href="/zh.html">首页</a> &gt; <a href="/zh/">选择国家</a> &gt; 薪资指南</div>
<div class="ct">
<div class="section"><h2>各国工资对比</h2><div class="grid">{salary_cards}</div></div>
<div class="section"><h2>额外收入</h2>
<div class="card">
<div class="stat"><span>加班费</span><span>+25-50%</span></div>
<div class="stat"><span>夜班补贴</span><span>+15-30%</span></div>
<div class="stat"><span>节假日补贴</span><span>+50-100%</span></div>
<div class="stat"><span>年终奖</span><span>1个月工资（部分国家）</span></div>
<div class="stat"><span>住宿节省</span><span>€200-€600/月（免费住宿时）</span></div>
</div></div>
<div class="cta"><h2>开始赚取欧洲工资</h2><a href="https://interjob.ro/apply.html">立即申请 ➜</a></div>
</div>
{footer(site, sm)}</body></html>"""


def gen_visa_page(site, sm):
    visa_rows = ""
    for cc, c in COUNTRIES.items():
        visa_rows += f'<div class="card"><h3>{c["zh"]}</h3><div class="stat"><span>处理时间</span><span>{c["visa_time"]}</span></div><div class="stat"><span>签证类型</span><span>工作签证</span></div><div class="stat"><span>可否带家属</span><span>✅ 可以</span></div></div>\n'

    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>签证指南 — 中国工人赴欧洲工作签证 | {sm["en"]}</title>
<meta name="description" content="中国工人赴欧洲工作签证指南。德国、荷兰、比利时、奥地利、丹麦、瑞士工作许可申请流程和所需文件。">
<meta name="keywords" content="欧洲工作签证,中国人赴欧工作,工作许可,签证申请,海外务工签证">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://{site}/zh/visa/">
{CSS}</head><body>
{nav(site, sm)}
<section class="hero"><h1>签证与工作许可</h1><p>中国工人赴欧洲{sm["niche"]}工作签证指南</p></section>
<div class="breadcrumb"><a href="/zh.html">首页</a> &gt; <a href="/zh/">选择国家</a> &gt; 签证指南</div>
<div class="ct">
<div class="section"><h2>各国签证处理时间</h2><div class="grid">{visa_rows}</div></div>
<div class="section"><h2>所需文件</h2>
<div class="card">
<div class="stat"><span>1</span><span>有效护照（6个月以上有效期）</span></div>
<div class="stat"><span>2</span><span>教育证书和学历认证</span></div>
<div class="stat"><span>3</span><span>工作经验证明</span></div>
<div class="stat"><span>4</span><span>无犯罪记录证明（公证）</span></div>
<div class="stat"><span>5</span><span>体检报告</span></div>
<div class="stat"><span>6</span><span>护照照片（白色背景）</span></div>
</div></div>
<div class="section"><h2>我们的签证服务（免费）</h2>
<div class="grid">
<div class="card"><h3>文件准备</h3><p>协助准备所有所需文件，包括翻译和公证认证</p></div>
<div class="card"><h3>雇主担保</h3><p>我们的欧洲雇主提供正式工作邀请和签证担保</p></div>
<div class="card"><h3>大使馆协调</h3><p>协调中国大使馆和欧洲领事馆的签证申请</p></div>
<div class="card"><h3>家属签证</h3><p>协助办理配偶和子女的团聚签证</p></div>
</div></div>
<div class="cta"><h2>免费签证协助</h2><p style="margin:10px 0;opacity:.9">我们处理所有签证手续 — 您只需提供基本文件</p><a href="https://interjob.ro/apply.html">立即申请 ➜</a></div>
</div>
{footer(site, sm)}</body></html>"""


def deploy_site(site):
    sm = SITES[site]
    docroot = DOCROOT_OVERRIDES.get(site, f"{HOME}/{site}")
    ok = err = 0
    print(f"\n=== {site} ===")

    # Create /zh/ directory structure
    cpanel_mkdir(f"{docroot}/zh")
    for cc in COUNTRIES:
        cpanel_mkdir(f"{docroot}/zh/{cc}")
    cpanel_mkdir(f"{docroot}/zh/faq")
    cpanel_mkdir(f"{docroot}/zh/salary")
    cpanel_mkdir(f"{docroot}/zh/visa")

    # Language index
    html = gen_lang_index(site, sm)
    if cpanel_upload(html.encode("utf-8"), "index.html", f"{docroot}/zh"):
        print(f"  OK zh/index.html")
        ok += 1
    else:
        err += 1

    # Country pages
    for cc, c in COUNTRIES.items():
        html = gen_country_page(site, sm, cc, c)
        if cpanel_upload(html.encode("utf-8"), "index.html", f"{docroot}/zh/{cc}"):
            print(f"  OK zh/{cc}/index.html")
            ok += 1
        else:
            err += 1

    # FAQ
    html = gen_faq_page(site, sm)
    if cpanel_upload(html.encode("utf-8"), "index.html", f"{docroot}/zh/faq"):
        print(f"  OK zh/faq/index.html")
        ok += 1
    else:
        err += 1

    # Salary
    html = gen_salary_page(site, sm)
    if cpanel_upload(html.encode("utf-8"), "index.html", f"{docroot}/zh/salary"):
        print(f"  OK zh/salary/index.html")
        ok += 1
    else:
        err += 1

    # Visa
    html = gen_visa_page(site, sm)
    if cpanel_upload(html.encode("utf-8"), "index.html", f"{docroot}/zh/visa"):
        print(f"  OK zh/visa/index.html")
        ok += 1
    else:
        err += 1

    print(f"  Total: {ok} OK, {err} errors")
    return ok, err


if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(SITES.keys())
    total_ok = total_err = 0
    for site in sites:
        if site not in SITES:
            print(f"SKIP {site}")
            continue
        o, e = deploy_site(site)
        total_ok += o
        total_err += e
        time.sleep(0.3)
    print(f"\nGrand Total: {total_ok} OK, {total_err} errors")
    print(f"Pages per site: 10 (index + 6 countries + FAQ + salary + visa)")
    print(f"Total pages: {total_ok} across {len([s for s in sites if s in SITES])} sites")

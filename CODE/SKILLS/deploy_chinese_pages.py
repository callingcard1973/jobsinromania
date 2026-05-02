"""Deploy Chinese (zh-CN) landing pages to all job sites for Baidu/Sogou SEO.

Each site gets a /zh.html page with:
- Simplified Chinese content
- Baidu meta keywords + description
- No Google dependencies (fonts, analytics, reCAPTCHA)
- FAQPage + EmploymentAgency schema in Chinese
- Romania recruitment focus
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

SITES = {
    "careworkers.eu": {
        "title": "欧洲护理工作",
        "title_en": "Care Workers EU",
        "desc": "欧洲医疗保健和老年护理工作机会",
        "keywords": "欧洲护理工作,护理员招聘,德国护理工作,荷兰护理工作,罗马尼亚招聘,海外护工,养老护理",
        "niche_zh": "医疗保健和老年护理",
        "salary": "€1,800 - €3,500",
        "positions": "护理员、护士、老年护理助理、家庭护理员、康复治疗师",
    },
    "factoryjobs.eu": {
        "title": "欧洲工厂工作",
        "title_en": "Factory Jobs EU",
        "desc": "欧洲工厂和制造业招聘 — 高薪职位",
        "keywords": "欧洲工厂工作,制造业招聘,德国工厂,荷兰工厂,海外务工,工厂操作员,生产线工人",
        "niche_zh": "工厂和制造业",
        "salary": "€1,600 - €3,000",
        "positions": "生产线操作员、质检员、机器操作员、焊工、数控操作员、包装工、叉车司机",
    },
    "buildjobs.eu": {
        "title": "欧洲建筑工作",
        "title_en": "Build Jobs EU",
        "desc": "欧洲建筑行业高薪工作机会",
        "keywords": "欧洲建筑工作,建筑工人招聘,德国建筑,荷兰建筑,海外建筑工,脚手架工,混凝土工",
        "niche_zh": "建筑和装修",
        "salary": "€1,800 - €4,000",
        "positions": "脚手架工、混凝土工、木工、钢筋工、重型设备操作员、电工、管道工、油漆工",
    },
    "electricjobs.eu": {
        "title": "欧洲电气工作",
        "title_en": "Electric Jobs EU",
        "desc": "欧洲电气和技术岗位招聘",
        "keywords": "欧洲电工工作,电气技术员,德国电工,自动化技术员,光伏安装,海外电工",
        "niche_zh": "电气和技术",
        "salary": "€2,200 - €4,500",
        "positions": "电工、工业电气技术员、自动化技术员、PLC程序员、太阳能安装工、电动汽车充电站技术员",
    },
    "farmworkers.eu": {
        "title": "欧洲农业工作",
        "title_en": "Farm Workers EU",
        "desc": "欧洲农业和季节性农场工作",
        "keywords": "欧洲农业工作,农场工人,温室工作,荷兰农场,德国农业,采摘工,海外农工",
        "niche_zh": "农业和农场",
        "salary": "€1,400 - €2,500",
        "positions": "采摘工、温室工人、蔬菜加工、畜牧、奶牛场、拖拉机操作、灌溉管理",
    },
    "horecaworkers.eu": {
        "title": "欧洲酒店餐饮工作",
        "title_en": "Horeca Workers EU",
        "desc": "欧洲酒店、餐厅和餐饮业工作",
        "keywords": "欧洲酒店工作,厨师招聘,服务员工作,酒店前台,餐饮业,海外酒店,欧洲餐厅",
        "niche_zh": "酒店、餐厅和餐饮",
        "salary": "€1,500 - €4,000",
        "positions": "厨师、厨师长、服务员、调酒师、酒店前台、客房服务、厨房助理、咖啡师",
    },
    "meatworkers.eu": {
        "title": "欧洲肉类加工工作",
        "title_en": "Meat Workers EU",
        "desc": "欧洲肉类加工和食品工业工作",
        "keywords": "欧洲肉类加工,屠宰场工作,肉类切割,德国肉类加工,荷兰食品厂,海外务工",
        "niche_zh": "肉类加工和食品工业",
        "salary": "€1,700 - €3,000",
        "positions": "生产线工人、屠宰工、肉类切割工、去骨工、质检员、包装工、冷库工人",
    },
    "mechanicjobs.eu": {
        "title": "欧洲汽车维修工作",
        "title_en": "Mechanic Jobs EU",
        "desc": "欧洲汽车和机械维修技师工作",
        "keywords": "欧洲汽修工作,汽车技师,德国汽修,荷兰机械师,电动汽车维修,海外汽修",
        "niche_zh": "汽车和机械维修",
        "salary": "€2,000 - €4,000",
        "positions": "汽车维修技师、卡车技师、汽车电气师、车身修复师、喷漆技师、电动汽车专家",
    },
    "warehouseworkers.eu": {
        "title": "欧洲仓库物流工作",
        "title_en": "Warehouse Workers EU",
        "desc": "欧洲仓库和物流中心工作机会",
        "keywords": "欧洲仓库工作,物流中心,叉车司机,荷兰仓库,德国物流,拣货员,海外仓储",
        "niche_zh": "仓库和物流",
        "salary": "€1,600 - €2,800",
        "positions": "拣货员、叉车操作员、库存管理、装卸工、包装工、质检员、仓库主管",
    },
    "aluminumrecyclehub.com": {
        "title": "欧洲回收行业工作",
        "title_en": "Aluminum Recycle Hub",
        "desc": "欧洲回收和废物管理行业工作",
        "keywords": "欧洲回收工作,废物管理,铝回收,德国回收厂,循环经济,海外环保工作",
        "niche_zh": "回收和废物管理",
        "salary": "€1,600 - €2,800",
        "positions": "分拣操作员、物料搬运工、破碎机操作员、质检员、回收厂技术员、环保合规员",
    },
    "expatsinromania.org": {
        "title": "罗马尼亚外籍人士工作",
        "title_en": "Expats in Romania",
        "desc": "在罗马尼亚的外籍人士工作和社区",
        "keywords": "罗马尼亚工作,罗马尼亚外籍人士,布加勒斯特工作,中国人在罗马尼亚,罗马尼亚签证",
        "niche_zh": "罗马尼亚外籍人士就业",
        "salary": "€1,000 - €4,000",
        "positions": "IT工程师、英语教师、国际商务经理、旅游运营、制造业主管、客服代表",
    },
    "interjob.ro": {
        "title": "InterJob国际招聘",
        "title_en": "InterJob Romania",
        "desc": "欧洲国际招聘平台 — 连接求职者与欧洲雇主",
        "keywords": "欧洲招聘,国际招聘,罗马尼亚招聘公司,欧洲工作签证,海外务工,欧盟工作",
        "niche_zh": "国际招聘",
        "salary": "€1,500 - €5,000",
        "positions": "建筑工人、工厂操作员、护理员、厨师、仓库工人、电工、汽修技师、农场工人",
    },
    "mivromania.info": {
        "title": "MIV罗马尼亚",
        "title_en": "MIV Romania",
        "desc": "罗马尼亚就业机会",
        "keywords": "罗马尼亚工作,罗马尼亚就业,欧洲招聘,海外务工,罗马尼亚签证",
        "niche_zh": "罗马尼亚就业",
        "salary": "€1,500 - €3,500",
        "positions": "制造业、建筑、酒店餐饮、医疗保健、物流、农业各类岗位",
    },
    "mivromania.online": {
        "title": "MIV罗马尼亚在线",
        "title_en": "MIV Romania Online",
        "desc": "罗马尼亚在线招聘平台",
        "keywords": "罗马尼亚在线招聘,欧洲工作,海外务工平台,罗马尼亚工作机会",
        "niche_zh": "罗马尼亚在线招聘",
        "salary": "€1,500 - €3,500",
        "positions": "制造业、建筑、酒店餐饮、医疗保健、物流、农业各类岗位",
    },
    "nepalezi.com": {
        "title": "尼泊尔工人欧洲就业",
        "title_en": "Nepalezi",
        "desc": "尼泊尔和亚洲工人欧洲工作机会",
        "keywords": "亚洲工人欧洲工作,海外务工,欧洲招聘亚洲工人,工作签证,劳务输出",
        "niche_zh": "亚洲工人欧洲就业",
        "salary": "€1,500 - €3,000",
        "positions": "酒店餐饮、建筑、工厂、农场、护理、仓库各类岗位",
    },
}

COUNTRIES_ZH = {
    "德国": "Germany", "荷兰": "Netherlands", "比利时": "Belgium",
    "奥地利": "Austria", "丹麦": "Denmark", "瑞士": "Switzerland",
}


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
                time.sleep(5 * (attempt + 1))
            else:
                print(f"  ERR {remote_dir}/{filename}: {e}")
                return False


def gen_chinese_page(site, meta):
    title = meta["title"]
    title_en = meta["title_en"]
    desc = meta["desc"]
    keywords = meta["keywords"]
    niche_zh = meta["niche_zh"]
    salary = meta["salary"]
    positions = meta["positions"]

    country_cards = ""
    for zh, en in COUNTRIES_ZH.items():
        country_cards += f'<a href="https://{site}/zh.html" class="card">{zh}</a>\n'

    faq_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": "中国人可以在欧洲工作吗？",
             "acceptedAnswer": {"@type": "Answer", "text": f"可以。中国公民可以通过工作签证在欧洲合法工作。我们协助办理德国、荷兰、比利时、奥地利、丹麦和瑞士的工作许可和签证。{niche_zh}行业需求旺盛。"}},
            {"@type": "Question", "name": f"欧洲{niche_zh}工资多少？",
             "acceptedAnswer": {"@type": "Answer", "text": f"欧洲{niche_zh}月薪范围为{salary}，具体取决于国家和经验。许多雇主提供免费或补贴住房。加班费和假日补贴通常额外增加20-30%。"}},
            {"@type": "Question", "name": "需要什么文件？",
             "acceptedAnswer": {"@type": "Answer", "text": "您需要：有效护照（6个月以上有效期）、教育证书、工作经验证明、无犯罪记录证明、体检报告。我们负责文件翻译和公证认证。"}},
            {"@type": "Question", "name": "从申请到出国需要多长时间？",
             "acceptedAnswer": {"@type": "Answer", "text": "整个过程通常需要6-12周：1-2周申请审核，2-4周雇主匹配，2-6周签证处理。我们管理每一步并协调中国大使馆和欧洲领事馆。"}},
            {"@type": "Question", "name": "需要支付中介费吗？",
             "acceptedAnswer": {"@type": "Answer", "text": "合法的欧盟招聘机构不向工人收费。InterJob由雇主支付费用。所有服务——工作匹配、签证协助、文件准备和旅行协调——对求职者完全免费。"}},
        ],
    }, ensure_ascii=False)

    org_schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "EmploymentAgency",
        "name": title_en,
        "description": desc,
        "url": f"https://{site}/",
        "areaServed": [{"@type": "Country", "name": c} for c in COUNTRIES_ZH.values()],
        "serviceType": "国际招聘",
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "recruitment",
            "url": "https://interjob.ro/apply.html",
            "availableLanguage": ["Chinese", "English", "Romanian"],
        },
    }, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} | {title_en} — 欧洲{niche_zh}招聘</title>
<meta name="description" content="{desc}。月薪{salary}。免费住宿和签证协助。德国、荷兰、比利时、奥地利、丹麦、瑞士。">
<meta name="keywords" content="{keywords}">
<meta name="robots" content="index, follow">
<meta name="author" content="InterJob Solutions Europe">
<link rel="canonical" href="https://{site}/zh.html">
<link rel="alternate" hreflang="zh-CN" href="https://{site}/zh.html">
<link rel="alternate" hreflang="en" href="https://{site}/">
<link rel="alternate" hreflang="x-default" href="https://{site}/">
<meta property="og:title" content="{title} — 欧洲{niche_zh}招聘">
<meta property="og:description" content="{desc}。月薪{salary}。">
<meta property="og:type" content="website">
<meta property="og:url" content="https://{site}/zh.html">
<meta property="og:locale" content="zh_CN">
<script type="application/ld+json">{org_schema}</script>
<script type="application/ld+json">{faq_schema}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"Microsoft YaHei","PingFang SC","Hiragino Sans GB",sans-serif;line-height:1.8;color:#1e293b;background:#f8fafc}}
.header{{background:linear-gradient(135deg,#065f46,#1e3a5f);color:#fff;padding:20px;text-align:center}}
.header h1{{font-size:2rem;margin-bottom:8px}}
.header p{{opacity:.9;font-size:1.1rem}}
.container{{max-width:900px;margin:0 auto;padding:20px}}
.highlight{{background:linear-gradient(135deg,#10b981,#065f46);color:#fff;border-radius:12px;padding:30px;margin:25px 0;text-align:center}}
.highlight h2{{font-size:1.8rem;margin-bottom:10px}}
.highlight .salary{{font-size:2.5rem;font-weight:bold;margin:10px 0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}}
.card{{display:block;padding:18px;background:#fff;border-radius:10px;text-decoration:none;color:#1e293b;text-align:center;font-size:1.1rem;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:all .2s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 4px 16px rgba(0,0,0,.15);background:#10b981;color:#fff}}
.section{{margin:30px 0}}
.section h2{{color:#065f46;font-size:1.5rem;margin-bottom:15px;border-bottom:2px solid #10b981;padding-bottom:8px}}
.benefits{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}
.benefit{{background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.benefit h3{{color:#065f46;margin-bottom:8px}}
details{{margin-bottom:12px;background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
summary{{padding:15px 20px;cursor:pointer;font-weight:600;font-size:1rem;list-style:none}}
summary::-webkit-details-marker{{display:none}}
details div{{padding:0 20px 15px;color:#475569;line-height:1.8}}
.cta{{text-align:center;margin:40px 0;padding:40px;background:linear-gradient(135deg,#065f46,#1e3a5f);border-radius:12px;color:#fff}}
.cta h2{{font-size:1.8rem;margin-bottom:15px}}
.cta a{{display:inline-block;padding:18px 50px;background:#10b981;color:#fff;text-decoration:none;border-radius:8px;font-size:1.3rem;font-weight:bold;transition:all .2s}}
.cta a:hover{{background:#059669;transform:scale(1.05)}}
.footer{{background:#1e293b;color:#fff;padding:25px;text-align:center;margin-top:40px}}
.footer a{{color:#10b981;text-decoration:none}}
.process{{counter-reset:step}}
.step{{position:relative;padding-left:50px;margin-bottom:20px}}
.step::before{{counter-increment:step;content:counter(step);position:absolute;left:0;top:0;width:36px;height:36px;background:#065f46;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold}}
@media(max-width:600px){{.header h1{{font-size:1.5rem}}.highlight .salary{{font-size:2rem}}.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<header class="header">
<h1>{title}</h1>
<p>{desc} — 为中国工人提供欧洲就业机会</p>
</header>

<div class="container">

<div class="highlight">
<h2>月薪</h2>
<div class="salary">{salary}</div>
<p>+ 免费住宿 + 签证协助 + 机票补贴</p>
</div>

<div class="section">
<h2>招聘国家</h2>
<div class="cards">
{country_cards}</div>
</div>

<div class="section">
<h2>可用岗位</h2>
<p style="font-size:1.1rem;color:#475569">{positions}</p>
</div>

<div class="section">
<h2>我们提供的服务</h2>
<div class="benefits">
<div class="benefit"><h3>免费招聘</h3><p>求职者无需支付任何费用。所有费用由欧洲雇主承担。</p></div>
<div class="benefit"><h3>签证协助</h3><p>我们处理所有工作许可和签证申请文件，包括翻译和公证。</p></div>
<div class="benefit"><h3>免费住宿</h3><p>许多雇主提供免费或补贴住房，靠近工作地点。</p></div>
<div class="benefit"><h3>合法合同</h3><p>正式劳动合同、社会保险、医疗保险、带薪休假。</p></div>
</div>
</div>

<div class="section">
<h2>申请流程</h2>
<div class="process">
<div class="step"><strong>在线申请</strong> — 填写申请表，提交简历和证书</div>
<div class="step"><strong>资格审核</strong> — 48小时内审核您的资料</div>
<div class="step"><strong>雇主匹配</strong> — 为您匹配合适的欧洲雇主</div>
<div class="step"><strong>文件准备</strong> — 协助准备签证和工作许可文件</div>
<div class="step"><strong>出发欧洲</strong> — 安排旅行和接机，开始工作</div>
</div>
</div>

<div class="section">
<h2>常见问题</h2>
<details><summary>中国人可以在欧洲工作吗？</summary><div>可以。中国公民可以通过工作签证在欧洲合法工作。我们协助办理德国、荷兰、比利时、奥地利、丹麦和瑞士的工作许可和签证。{niche_zh}行业需求旺盛，欢迎中国工人。</div></details>
<details><summary>欧洲{niche_zh}工资多少？</summary><div>月薪范围为{salary}，具体取决于国家和工作经验。许多雇主额外提供免费住宿。加班费和假日补贴通常增加20-30%。瑞士和北欧工资最高。</div></details>
<details><summary>需要什么文件？</summary><div>您需要：有效护照（6个月以上有效期）、教育证书、工作经验证明、无犯罪记录证明、体检报告和护照照片。我们负责所有文件的翻译和公证认证。</div></details>
<details><summary>从申请到出国需要多长时间？</summary><div>整个过程通常需要6-12周：1-2周申请审核，2-4周雇主匹配，2-6周签证处理。我们管理每一步流程，协调中国大使馆和欧洲领事馆。</div></details>
<details><summary>需要支付中介费吗？</summary><div>不需要。合法的欧盟招聘机构不向求职者收取任何费用。InterJob的服务费由欧洲雇主支付。所有服务——工作匹配、签证协助、文件准备和旅行协调——对求职者完全免费。</div></details>
</div>

<div class="cta">
<h2>立即申请欧洲工作</h2>
<p style="margin-bottom:15px;opacity:.9">免费申请 — 48小时内回复</p>
<a href="https://interjob.ro/apply.html">立即申请 ➜</a>
</div>

<div class="section" style="text-align:center;color:#64748b;font-size:.9rem">
<p>InterJob Solutions Europe — 自2013年起服务欧洲国际招聘</p>
<p>服务国家：德国 · 荷兰 · 比利时 · 奥地利 · 丹麦 · 瑞士</p>
<p style="margin-top:10px">
<a href="https://{site}/" style="color:#065f46">English</a> ·
<a href="https://{site}/ro.html" style="color:#065f46">Română</a> ·
<a href="https://{site}/zh.html" style="color:#065f46;font-weight:bold">中文</a>
</p>
</div>

</div>

<footer class="footer">
<p>{title_en} — {desc}</p>
<p style="margin-top:10px"><a href="https://{site}/">首页</a> · <a href="https://interjob.ro/apply.html">申请</a> · <a href="https://interjob.ro/">InterJob</a></p>
<p style="margin-top:10px;opacity:.6;font-size:.85rem">&copy; 2026 {site} · InterJob Solutions Europe</p>
</footer>
</body>
</html>"""


if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(SITES.keys())
    total_ok = total_err = 0
    for site in sites:
        if site not in SITES:
            print(f"SKIP {site}")
            continue
        docroot = DOCROOT_OVERRIDES.get(site, f"{HOME}/{site}")
        html = gen_chinese_page(site, SITES[site])
        print(f"\n=== {site} ===")
        if cpanel_upload(html.encode("utf-8"), "zh.html", docroot):
            print(f"  OK zh.html")
            total_ok += 1
        else:
            total_err += 1
        time.sleep(0.3)
    print(f"\nTotal: {total_ok} OK, {total_err} errors")

#!/usr/bin/env python3
"""Inject PostHog snippet into all static HTML sites on A2 hosting via cPanel API."""
import requests, json, urllib3
urllib3.disable_warnings()

HOST   = "nl1-cl8-ats1.a2hosting.com"
PORT   = 2083
USER   = "loaiidil"
TOKEN  = "9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX"

SNIPPET = """<script>
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog && window.posthog.__loaded)||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init Dr qr Ci Br Zr Pr capture calculateEventProperties Ur register register_once register_for_session unregister unregister_for_session Xr getFeatureFlag getFeatureFlagPayload getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey displaySurvey cancelPendingSurvey canRenderSurvey canRenderSurveyAsync Jr identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset setIdentity clearIdentity get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException captureLog startExceptionAutocapture stopExceptionAutocapture loadToolbar get_property getSessionProperty Gr Hr createPersonProfile setInternalOrTestUser Wr Fr tn opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing get_explicit_consent_status is_capturing clear_opt_in_out_capturing $r debug ki Yr getPageViewId captureTraceFeedback captureTraceMetric Rr".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
    posthog.init('phc_shRANXNXNAHmSgf3Y3pBHWyg3X2h7C87B8xoem3rWehi', {
        api_host: 'https://us.i.posthog.com',
        defaults: '2026-01-30',
        person_profiles: 'identified_only',
    })
</script>"""

# Static HTML sites (not WordPress)
STATIC_SITES = [
    "careworkers.eu", "factoryjobs.eu", "buildjobs.eu", "electricjobs.eu",
    "farmworkers.eu", "horecaworkers.eu", "meatworkers.eu", "mechanicjobs.eu",
    "warehouseworkers.eu", "aluminumrecyclehub.com", "expatsinromania.org",
    "interjob.ro", "mivromania.info", "mivromania.online", "nepalezi.com",
    "internaltransfers.eu", "horecaworkers2026.com", "horecaworkers2026.eu",
    "horecaworkers2026.online", "weddnesday.org",
]

def cpanel(module, func, params={}):
    url = f"https://{HOST}:{PORT}/execute/{module}/{func}"
    r = requests.get(url, params=params, verify=False,
                     headers={"Authorization": f"cpanel {USER}:{TOKEN}"}, timeout=15)
    return r.json()

def get_file(path):
    r = cpanel("Fileman", "get_file_content", {"dir": path.rsplit("/",1)[0], "file": path.rsplit("/",1)[1]})
    return r.get("data", {}).get("content", "")

def save_file(path, content):
    r = cpanel("Fileman", "save_file_content", {
        "dir": path.rsplit("/",1)[0],
        "file": path.rsplit("/",1)[1],
        "content": content
    })
    return r.get("status", 0) == 1

def inject(domain):
    # A2 docroot: ~/domainname/
    index_path = f"/home/{USER}/{domain}/index.html"
    content = get_file(index_path)
    if not content:
        print(f"  SKIP {domain} — no index.html or empty")
        return False
    if "posthog.init" in content:
        print(f"  SKIP {domain} — already injected")
        return False
    if "</head>" not in content:
        print(f"  SKIP {domain} — no </head> tag")
        return False
    new_content = content.replace("</head>", SNIPPET + "\n</head>", 1)
    if save_file(index_path, new_content):
        print(f"  OK   {domain}")
        return True
    else:
        print(f"  FAIL {domain}")
        return False

ok = fail = skip = 0
for domain in STATIC_SITES:
    r = inject(domain)
    if r is True: ok += 1
    elif r is False: skip += 1
    else: fail += 1

print(f"\nDone: {ok} injected, {skip} skipped, {fail} failed")
print("WordPress sites need snippet via WP admin (8 sites)")

#!/usr/bin/env python3
"""Inject PostHog into WordPress sites on A2 via cPanel — writes to wp-content/mu-plugins/posthog.php"""
import requests, urllib3
urllib3.disable_warnings()

HOST  = "nl1-cl8-ats1.a2hosting.com"
PORT  = 2083
USER  = "loaiidil"
TOKEN = "9QEJ4ANOPHXZ0YE34NEWDAKA1UXZPKNX"

PHP = """<?php
/* PostHog Analytics — auto-injected */
add_action('wp_head', function() { ?>
<script>
    !function(t,e){var o,n,p,r;e.__SV||(window.posthog && window.posthog.__loaded)||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags on onFeatureFlags onSessionId getSurveys identify setPersonProperties group reset get_distinct_id get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
    posthog.init('phc_shRANXNXNAHmSgf3Y3pBHWyg3X2h7C87B8xoem3rWehi', {
        api_host: 'https://us.i.posthog.com',
        defaults: '2026-01-30',
        person_profiles: 'identified_only',
    });
</script>
<?php }, 1);
"""

WP_SITES = [
    "cumparlegume.com", "seicarescu.com", "agroevolution.com", "ajwang.org",
    "baneasa39.com", "cifn.info", "haritina.com", "mivromania.com",
]

def cpanel(module, func, params={}):
    url = f"https://{HOST}:{PORT}/execute/{module}/{func}"
    r = requests.get(url, params=params, verify=False,
                     headers={"Authorization": f"cpanel {USER}:{TOKEN}"}, timeout=15)
    return r.json()

def save_file(path, content):
    r = cpanel("Fileman", "save_file_content", {
        "dir": path.rsplit("/", 1)[0],
        "file": path.rsplit("/", 1)[1],
        "content": content,
    })
    return r.get("status", 0) == 1

def ensure_dir(path):
    cpanel("Fileman", "mkdir", {"path": path, "name": ""})

for domain in WP_SITES:
    mu_dir = f"/home/{USER}/{domain}/wp-content/mu-plugins"
    mu_file = f"{mu_dir}/posthog.php"
    ensure_dir(mu_dir)
    if save_file(mu_file, PHP):
        print(f"  OK   {domain}")
    else:
        print(f"  FAIL {domain}")

print("\nDone. PostHog active on all 8 WordPress sites via mu-plugin.")

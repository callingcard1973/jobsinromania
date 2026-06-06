/* PostHog snippet + tracking for pentru-angajatori */
(function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(o,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]);t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.setAttribute("src","https://us.i.posthog.com/static/array.js"),(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var q=e;for(void 0!==a?q=e[a]=[]:a="posthog",q.people=q.people||[],q.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},q.people.toString=function(){return q.toString(1)+".people (stub)"},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing opt_in_capturing isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group resetGroups onReady addEventProperties removeEventProperties".split(" "),n=0;n<o.length;n++)g(q,o[n]);e._i.push([a,s])})})(document,window.posthog||[]);
posthog.init('phc_nUcXMsA8vMWayxe6dgGhq2wgagnBZmcDbGWGkCVXnhcE',{api_host:'https://t.interjob.ro',person_profiles:'identified_only'});
posthog.register({domain:'factoryjobs.eu',page:'pentru-angajatori',site_type:'employer_landing'});

function track(ev, props){
  try{ if(window.posthog) window.posthog.capture(ev, props || {}); }catch(e){}
}

track('view_employer_landing',{lang:'ro',referrer:document.referrer||'direct'});

(function(){
  // Scroll depth
  var hit={25:0,50:0,75:0,100:0};
  window.addEventListener('scroll', function(){
    var h=document.documentElement, b=document.body;
    var st=h.scrollTop||b.scrollTop;
    var sh=(h.scrollHeight||b.scrollHeight)-h.clientHeight;
    var pct=sh>0?(st/sh)*100:0;
    [25,50,75,100].forEach(function(p){
      if(!hit[p]&&pct>=p){ hit[p]=1; track('scroll_'+p,{pct:p}); }
    });
  },{passive:true});

  // Delegated click tracking via data-track
  document.addEventListener('click', function(ev){
    var el = ev.target.closest('[data-track]');
    if(el) track(el.dataset.track, {href: el.href || null});
  });


  // Categories accordion
  var catData={
    packaging:{title:'Packaging — 202 candidați',countries:'Nepal, India, Bangladesh',lang:'Engleză A2-B2',exp:'2-7 ani experiență medie'},
    machinery:{title:'Machinery — 155 candidați',countries:'India, Vietnam, Filipine',lang:'Engleză B1-B2',exp:'4-10 ani experiență medie'},
    logistics:{title:'Logistics — 129 candidați',countries:'Filipine, Sri Lanka, Pakistan',lang:'Engleză A2-B1',exp:'2-5 ani experiență medie'},
    factory:{title:'Factory — 58 candidați',countries:'Nepal, Bangladesh, India',lang:'Engleză A2',exp:'1-4 ani experiență medie'},
    warehouse:{title:'Warehouse — 25 candidați',countries:'India, Pakistan, Bangladesh',lang:'Engleză A2-B1',exp:'2-6 ani experiență medie'}
  };
  var detail = document.getElementById('catDetail');
  var current = null;
  function toggleCat(c){
    var k = c.dataset.cat;
    track('expand_category',{category:k});
    var cats = document.querySelectorAll('.cat');
    if(current === k){
      detail.classList.remove('open');
      current = null;
      cats.forEach(function(x){ x.setAttribute('aria-expanded','false'); });
      return;
    }
    var d = catData[k];
    detail.innerHTML = '<h4>'+d.title+'</h4><div class="row">'+
      '<div><strong>Top țări sursă</strong>'+d.countries+'</div>'+
      '<div><strong>Nivel limbă</strong>'+d.lang+'</div>'+
      '<div><strong>Experiență</strong>'+d.exp+'</div></div>';
    detail.classList.add('open');
    current = k;
    cats.forEach(function(x){ x.setAttribute('aria-expanded', x.dataset.cat===k?'true':'false'); });
  }
  document.querySelectorAll('.cat').forEach(function(c){
    c.addEventListener('click', function(){ toggleCat(c); });
    c.addEventListener('keydown', function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); toggleCat(c); }
    });
  });

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach(function(q){
    q.addEventListener('click', function(){
      var open = q.getAttribute('aria-expanded') === 'true';
      q.setAttribute('aria-expanded', !open);
      var a = q.nextElementSibling;
      a.style.maxHeight = open ? '0' : a.scrollHeight + 'px';
      if(!open) track('click_faq_question',{index: parseInt(q.dataset.idx,10)});
    });
  });

})();

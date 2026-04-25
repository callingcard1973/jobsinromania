{extends file='parent:_partials/head.tpl'}

{block name='head_fonts'}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Barlow+Condensed:wght@400;500;600;700&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
{/block}

{block name='head_open_graph'}
  <meta property="og:title" content="{$page.meta.title|escape:'html'}">
  <meta property="og:description" content="{$page.meta.description|escape:'html'}">
  <meta property="og:url" content="{$urls.current_url|escape:'html'}">
  <meta property="og:site_name" content="{$shop.name|escape:'html'}">
  {if !isset($product) && $page.page_name != 'product'}<meta property="og:type" content="website">{/if}
  <meta name="theme-color" content="#1a5c2a">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{$page.meta.title|default:'HYPER BNDF'|escape:'html'}">
  <meta name="twitter:description" content="Echipamente certificate EN 1176 TUV pentru locuri de joacă. Primării România.">
{/block}

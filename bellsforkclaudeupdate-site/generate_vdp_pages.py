#!/usr/bin/env python3
"""
generate_vdp_pages.py
Reads inventory.json and generates a standalone HTML page for every vehicle.

Output structure (mirrors what goes on the web server):
  vdp/
    D2601/
      Used-2017-Chevrolet-Silverado-LTZ-for-sale-in-Greenville-NC-27858/
        index.html

Usage:
  python3 generate_vdp_pages.py [--inventory PATH] [--out DIR]

Defaults:
  --inventory  inventory.json
  --out        .   (current dir, so vdp/ folder appears alongside index.html)
"""

import json, os, re, argparse, textwrap

# ── helpers ─────────────────────────────────────────────────────────────────

def fnv1a32(s: str) -> str:
    """Deterministic 32-bit hash (FNV-1a) for stable, non-sensitive IDs."""
    h = 0x811c9dc5
    for b in (s or '').encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xffffffff
    return f"{h:08x}"

def slug_id(v):
    """Return a stable, SEO-safe id that NEVER includes the raw VIN."""
    base = (v.get('publicId') or v.get('stockNumber') or '').strip()
    if base:
        return re.sub(r'[^a-z0-9]', '', base, flags=re.I)

    # If older records lack stockNumber/publicId, fall back to a short hash.
    vin = (v.get('vin') or '').strip().upper()
    if vin:
        return 'V' + fnv1a32(vin)

    fallback = f"{v.get('year','')}|{v.get('make','')}|{v.get('model','')}|{v.get('dateAdded','')}|{v.get('id','')}"
    return 'V' + fnv1a32(fallback)

def slug_tail(v):
    parts = ['Used', v.get('year'), v.get('make'), v.get('model'), v.get('trim'),
             'for-sale-in-Greenville-NC-27858']
    clean = [re.sub(r'[^a-z0-9]+','-', str(p).strip(), flags=re.I).strip('-') for p in parts if p]
    return '-'.join(filter(None, clean))

def build_slug(v):
    return f"{slug_id(v)}/{slug_tail(v)}"

def fmt_price(p):
    try:
        return f"${int(p):,}"
    except:
        return "Call for Price"

def fmt_miles(m):
    try:
        return f"{int(m):,} miles"
    except:
        return "—"

def esc(s):
    return str(s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

# ── HTML template ────────────────────────────────────────────────────────────

def build_vdp_page(v, depth=3):
    """Uses absolute paths so the page works at any directory depth."""
    prefix = '/'        # absolute root
    assetpfx = '/'      # absolute root

    title      = f"{v.get('year','')} {v.get('make','')} {v.get('model','')}".strip()
    trim       = esc(v.get('trim',''))
    full_title = f"{title} {v.get('trim','') or ''}".strip()
    price_str  = fmt_price(v.get('price'))
    miles_str  = fmt_miles(v.get('mileage'))
    stock      = esc(v.get('stockNumber',''))
    vin        = esc(v.get('vin',''))
    engine     = esc(v.get('engine','—'))
    trans      = esc(v.get('transmission','—'))
    drive      = esc(v.get('drivetrain','—'))
    fuel       = esc(v.get('fuelType','—'))
    ext_color  = esc(v.get('exteriorColor','—') or '—')
    int_color  = esc(v.get('interiorColor','—') or '—')
    vtype      = esc((v.get('type') or '').capitalize())
    desc       = esc(v.get('description',''))
    features   = v.get('features') or []
    images     = v.get('images') or []
    mpg_city   = v.get('mpgCity')
    mpg_hwy    = v.get('mpgHighway')
    badge      = esc(v.get('badge',''))
    can_slug   = build_slug(v)
    page_url   = f"https://bellsforkautoandtruck.com/vdp/{can_slug}/"
    apply_url  = f"{prefix}financing.html?tab=financing&vehicle={full_title}&vin={vin}&price={v.get('price','')}#applications"
    inq_url    = f"{prefix}contact.html?vehicle={full_title}&vin={vin}#appointment"

    # Image HTML
    if images:
        main_img = f'<img src="{assetpfx}assets/vehicles/{esc(images[0])}" alt="{esc(full_title)}" class="vdp-main-img">'
        photo_label = f'Photos ({len(images)})'
    else:
        main_img = '''<div class="vdp-placeholder">
          <div class="text-center">
            <svg width="80" height="80" fill="#ccc" viewBox="0 0 16 16">
              <rect x="1" y="3" width="15" height="13" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
              <circle cx="5.5" cy="14.5" r="1.5" fill="currentColor"/>
              <circle cx="12.5" cy="14.5" r="1.5" fill="currentColor"/>
            </svg>
            <div class="mt-2 text-muted" style="font-size:.85rem;">Photo Coming Soon</div>
          </div>
        </div>'''
        photo_label = ''

    # Specs table rows
    specs = [
        ('Stock #',       stock or '—'),
        ('VIN',           vin or '—'),
        ('Year',          str(v.get('year','—'))),
        ('Make',          esc(v.get('make','—'))),
        ('Model',         esc(v.get('model','—'))),
        ('Trim',          trim or '—'),
        ('Mileage',       miles_str),
        ('Engine',        engine),
        ('Transmission',  trans),
        ('Drive Train',   drive),
        ('Fuel Type',     fuel),
        ('Exterior Color',ext_color),
        ('Interior Color',int_color),
        ('Type',          vtype or '—'),
    ]
    spec_rows = '\n'.join(
        f'<tr><td>{k}</td><td>{val}</td></tr>' for k, val in specs
    )

    # MPG block
    if mpg_city and mpg_hwy:
        mpg_block = f'''
        <div class="mb-3">
          <div class="text-muted small mb-1">Estimated By E.P.A.</div>
          <div class="mpg-badge">
            <div class="text-center">
              <div class="mpg-num">{mpg_city}</div>
              <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;">City</div>
            </div>
            <svg width="28" height="28" fill="#555" viewBox="0 0 16 16">
              <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h9A1.5 1.5 0 0 1 12 3.5V5h1.02a1.5 1.5 0 0 1 1.17.563l1.481 1.85a1.5 1.5 0 0 1 .329.938V10.5a1.5 1.5 0 0 1-1.5 1.5H14a2 2 0 1 1-4 0H5a2 2 0 1 1-3.998-.085A1.5 1.5 0 0 1 0 10.5v-7zm1.294 7.456A1.999 1.999 0 0 1 4.732 11h5.536a2.01 2.01 0 0 1 .732-.732V3.5a.5.5 0 0 0-.5-.5h-9a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .294.456zM12 10a2 2 0 0 1 1.732 1h.768a.5.5 0 0 0 .5-.5V8.35a.5.5 0 0 0-.11-.312l-1.48-1.85A.5.5 0 0 0 13.02 6H12v4zm-9 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
            </svg>
            <div class="text-center">
              <div class="mpg-num">{mpg_hwy}</div>
              <div style="font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;">Hwy</div>
            </div>
          </div>
          <div class="text-muted" style="font-size:.72rem;margin-top:.3rem;">Actual Mileage May Vary</div>
        </div>'''
    else:
        mpg_block = ''

    # Description block
    desc_block = f'''
        <div class="mt-4">
          <h5 class="fw-bold">Vehicle Description</h5>
          <p class="text-muted">{desc}</p>
        </div>''' if desc else ''

    # Features block
    if features:
        feat_badges = '\n'.join(
            f'<span class="badge bg-light text-dark border px-3 py-2">{esc(f)}</span>'
            for f in features
        )
        feat_block = f'''
        <div class="mt-3">
          <h5 class="fw-bold">Features &amp; Options</h5>
          <div class="d-flex flex-wrap gap-2">{feat_badges}</div>
        </div>'''
    else:
        feat_block = ''

    # Badge pill
    badge_html = f'<span class="badge bg-danger px-3 py-2 mb-2">{badge}</span>' if badge else ''

    # Schema.org Vehicle structured data
    schema = {
        "@context": "https://schema.org",
        "@type": "Car",
        "name": full_title,
        "url": page_url,
        "description": v.get('description', f"Used {full_title} for sale at Bells Fork Auto & Truck in Greenville, NC 27858"),
        "vehicleIdentificationNumber": v.get('vin',''),
        "productionDate": str(v.get('year','')),
        "mileageFromOdometer": {"@type":"QuantitativeValue","value": v.get('mileage',0),"unitCode":"SMI"},
        "vehicleTransmission": v.get('transmission',''),
        "driveWheelConfiguration": v.get('drivetrain',''),
        "fuelType": v.get('fuelType',''),
        "color": v.get('exteriorColor',''),
        "offers": {
            "@type": "Offer",
            "priceCurrency": "USD",
            "price": str(v.get('price','')),
            "availability": "https://schema.org/InStock",
            "seller": {
                "@type": "AutoDealer",
                "name": "Bells Fork Auto & Truck",
                "telephone": "+1-252-496-0005",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "3840 Charles Blvd",
                    "addressLocality": "Greenville",
                    "addressRegion": "NC",
                    "postalCode": "27858",
                    "addressCountry": "US"
                }
            }
        }
    }
    schema_json = json.dumps(schema, indent=2)

    # ── Assemble full page ───────────────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <title>{esc(full_title)} for Sale in Greenville NC | Bells Fork Auto &amp; Truck</title>
  <meta name="description" content="{esc(full_title)} for sale at Bells Fork Auto &amp; Truck in Greenville, NC 27858. {miles_str}, {price_str}. Stock #{stock}. Call (252) 496-0005.">
  <meta name="keywords" content="{esc(full_title)}, used {esc(v.get('make',''))} {esc(v.get('model',''))} Greenville NC, used cars Greenville NC, Bells Fork Auto, 27858">
  <link rel="canonical" href="{page_url}">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(full_title)} for Sale | Bells Fork Auto &amp; Truck">
  <meta property="og:description" content="{esc(full_title)}, {miles_str} — {price_str}. Available at Bells Fork Auto &amp; Truck, Greenville NC.">
  <meta property="og:url" content="{page_url}">
  <meta property="og:site_name" content="Bells Fork Auto &amp; Truck">

  <!-- Schema.org Vehicle structured data -->
  <script type="application/ld+json">
  {schema_json}
  </script>

  <!-- Favicon -->
  <link rel="icon" type="image/png" href="{assetpfx}assets/favicon.png">

  <!-- Bootstrap 5 -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">

  <!-- Site stylesheet -->
  <link href="{assetpfx}assets/style.css" rel="stylesheet">

  <style>
    /* ── Nav hover ── */
    .bfat-navlink {{
      font-size: .88rem; letter-spacing: .07em;
      color: #ffffff !important;
      transition: background .18s, color .18s;
    }}
    .bfat-navlink:hover, .bfat-navlink:focus, .bfat-navlink.active {{
      background: #dc3545 !important; color: #ffffff !important;
    }}
    .footer-link:hover {{ color: #fff !important; }}
    .site-identity-bar {{ position: relative; }}

    /* ── VDP page ── */
    body {{ background: #f1f1f1; }}
    .vdp-breadcrumb {{
      background: #fff;
      border-bottom: 1px solid #e0e0e0;
      padding: .55rem 0;
      font-size: .82rem;
    }}
    .vdp-breadcrumb a {{ color: #3a7bd5; text-decoration: none; }}
    .vdp-breadcrumb a:hover {{ text-decoration: underline; }}
    .vdp-title-bar {{
      background: #fff;
      border: 1px solid #ddd;
      border-top: 4px solid #3a7bd5;
      padding: .9rem 1.2rem;
      border-radius: 0 0 4px 4px;
      margin-bottom: 1.25rem;
      display: flex; flex-wrap: wrap;
      align-items: center; justify-content: space-between; gap: 1rem;
    }}
    .vdp-title-bar h1 {{ font-size: 1.5rem; font-weight: 700; margin: 0; }}
    .vdp-price-area {{ display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }}
    .vdp-price-retail-lbl {{
      background: #444; color: #fff; font-size: .8rem; font-weight: 700;
      padding: .4rem .8rem; border-radius: 3px;
      text-transform: uppercase; letter-spacing: .04em;
    }}
    .vdp-price-pill {{
      background: #28a745; color: #fff;
      font-size: 1.4rem; font-weight: 800;
      padding: .4rem 1rem; border-radius: 3px;
      white-space: nowrap;
    }}
    .vdp-main-img {{
      width: 100%; max-height: 420px; object-fit: cover;
      border-radius: 6px; border: 1px solid #ddd;
    }}
    .vdp-placeholder {{
      width: 100%; height: 320px; background: #f0f0f0;
      border-radius: 6px; border: 1px solid #ddd;
      display: flex; align-items: center; justify-content: center;
    }}
    .vdp-specs-table {{ width: 100%; font-size: .9rem; border-collapse: collapse; }}
    .vdp-specs-table tr {{ border-bottom: 1px solid #f0f0f0; }}
    .vdp-specs-table td {{ padding: .45rem .3rem; }}
    .vdp-specs-table td:first-child {{ font-weight: 700; color: #333; width: 42%; }}
    .vdp-specs-table td:last-child  {{ color: #555; }}
    .vdp-cta-bar {{
      background: #f8f8f8; border: 1px solid #e0e0e0;
      border-radius: 6px; padding: 1.2rem;
    }}
    .vdp-phone-link {{
      font-size: 1.2rem; font-weight: 700;
      color: #111; text-decoration: none;
    }}
    .vdp-phone-link:hover {{ color: #dc3545; }}
    .mpg-badge {{
      display: inline-flex; align-items: center; gap: .75rem;
      background: #f0f0f0; border-radius: 6px;
      padding: .5rem 1rem; font-size: .85rem; color: #444;
    }}
    .mpg-badge .mpg-num {{
      font-size: 1.4rem; font-weight: 800; color: #222; line-height: 1;
    }}
  </style>
</head>

<body>
  <a class="skip-link" href="#main">Skip to main content</a>

  <!-- ── TOP IDENTITY BAR ── -->
  <div class="site-identity-bar bg-white border-bottom py-3" style="position:relative;">
    <div class="container">
      <div class="d-flex align-items-center justify-content-between gap-3">
        <div class="d-flex flex-column align-items-start gap-1" style="min-width:120px;">
          <span class="fw-bold text-muted" style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;">Connect</span>
          <div class="d-flex gap-2 align-items-center">
            <a href="https://www.facebook.com/profile.php?id=61585590120772" target="_blank" aria-label="Facebook"
               style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:5px;background:#1877f2;color:#fff;text-decoration:none;">
              <svg width="17" height="17" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8.049c0-4.446-3.582-8.05-8-8.05C3.58 0-.002 3.603-.002 8.05c0 4.017 2.926 7.347 6.75 7.951v-5.625h-2.03V8.05H6.75V6.275c0-2.017 1.195-3.131 3.022-3.131.876 0 1.791.157 1.791.157v1.98h-1.009c-.993 0-1.303.621-1.303 1.258v1.51h2.218l-.354 2.326H9.25V16c3.824-.604 6.75-3.934 6.75-7.951z"/></svg>
            </a>
            <a href="https://www.facebook.com/profile.php?id=61585590120772" target="_blank" aria-label="Instagram"
               style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:5px;background:radial-gradient(circle at 30% 107%,#fdf497 0%,#fd5949 45%,#d6249f 60%,#285AEB 90%);color:#fff;text-decoration:none;">
              <svg width="17" height="17" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0C5.829 0 5.556.01 4.703.048 3.85.088 3.269.222 2.76.42a3.9 3.9 0 0 0-1.417.923A3.9 3.9 0 0 0 .42 2.76C.222 3.268.087 3.85.048 4.7.01 5.555 0 5.827 0 8.001c0 2.172.01 2.444.048 3.297.04.852.174 1.433.372 1.942.205.526.478.972.923 1.417.444.445.89.719 1.416.923.51.198 1.09.333 1.942.372C5.555 15.99 5.827 16 8 16s2.444-.01 3.298-.048c.851-.04 1.434-.174 1.943-.372a3.9 3.9 0 0 0 1.416-.923c.445-.445.718-.891.923-1.417.197-.509.332-1.09.372-1.942C15.99 10.445 16 10.173 16 8s-.01-2.445-.048-3.299c-.04-.851-.175-1.433-.372-1.941a3.9 3.9 0 0 0-.923-1.417A3.9 3.9 0 0 0 13.24.42c-.51-.198-1.092-.333-1.943-.372C10.443.01 10.172 0 7.998 0h.003zm-.717 1.442h.718c2.136 0 2.389.007 3.232.046.78.035 1.204.166 1.486.275.373.145.64.319.92.599.28.28.453.546.598.92.11.281.24.705.275 1.485.039.843.047 1.096.047 3.231s-.008 2.389-.047 3.232c-.035.78-.166 1.203-.275 1.485a2.47 2.47 0 0 1-.599.919c-.28.28-.546.453-.92.598-.28.11-.704.24-1.485.276-.843.038-1.096.047-3.232.047s-2.39-.009-3.232-.047c-.78-.036-1.203-.166-1.485-.276a2.478 2.478 0 0 1-.92-.598 2.48 2.48 0 0 1-.6-.92c-.109-.281-.24-.705-.275-1.485-.038-.843-.046-1.096-.046-3.233 0-2.136.008-2.388.046-3.231.036-.78.166-1.204.276-1.486.145-.373.319-.64.599-.92.28-.28.546-.453.92-.598.282-.11.705-.24 1.485-.276.738-.034 1.024-.044 2.515-.045v.002zm4.988 1.328a.96.96 0 1 0 0 1.92.96.96 0 0 0 0-1.92zm-4.27 1.122a4.109 4.109 0 1 0 0 8.217 4.109 4.109 0 0 0 0-8.217zm0 1.441a2.667 2.667 0 1 1 0 5.334 2.667 2.667 0 0 1 0-5.334z"/></svg>
            </a>
          </div>
        </div>
        <a href="{assetpfx}index.html" class="text-decoration-none"
           style="position:absolute;left:50%;transform:translateX(-50%);">
          <img src="{assetpfx}assets/logo.png" height="68" alt="Bells Fork Auto and Truck Logo">
        </a>
        <div class="text-end ms-auto" style="min-width:160px;">
          <a href="tel:+12524960005" class="text-decoration-none fw-bold d-flex align-items-center justify-content-end gap-2" style="font-size:1.2rem;color:#111;">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M1.885.511a1.745 1.745 0 0 1 2.61.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.678.678 0 0 0 .178.643l2.457 2.457a.678.678 0 0 0 .644.178l2.189-.547a1.745 1.745 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.634 18.634 0 0 1-7.01-4.42 18.634 18.634 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877L1.885.511z"/>
            </svg>
            (252) 496-0005
          </a>
          <a href="https://maps.google.com/?q=3840+Charles+Blvd+Greenville+NC" target="_blank"
             class="text-decoration-none text-muted d-flex align-items-start justify-content-end gap-1 mt-1" style="font-size:.82rem;line-height:1.5;">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="flex-shrink-0 mt-1" viewBox="0 0 16 16">
              <path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/>
            </svg>
            <span>3840 Charles Blvd<br>Greenville, NC 27858</span>
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- ── NAV BAR ── -->
  <header class="sticky-top" role="banner" style="z-index:1030;">
    <nav class="navbar navbar-expand-lg navbar-dark py-0" style="background:#111111;">
      <div class="container-fluid">
        <button class="navbar-toggler border-0 ms-auto py-3" type="button"
                data-bs-toggle="collapse" data-bs-target="#navMain"
                aria-controls="navMain" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse justify-content-center" id="navMain">
          <ul class="navbar-nav align-items-lg-center">
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink active" href="{assetpfx}inventory.html" aria-current="page">Inventory</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="{assetpfx}about.html">About</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="{assetpfx}reviews.html">Reviews</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="{assetpfx}financing.html">Financing</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="{assetpfx}contact.html#visit">Contact</a></li>
          </ul>
        </div>
      </div>
    </nav>
  </header>

  <main id="main">

    <!-- Breadcrumb -->
    <div class="vdp-breadcrumb">
      <div class="container">
        <a href="{assetpfx}index.html">Home</a>
        &rsaquo;
        <a href="{assetpfx}inventory.html">Inventory</a>
        &rsaquo;
        <span class="text-muted">{esc(full_title)}</span>
      </div>
    </div>

    <section class="py-4">
      <div class="container">

        {badge_html}

        <!-- Title + Price bar -->
        <div class="vdp-title-bar">
          <h1>{esc(title)}{f' <span style="font-weight:400;color:#666;font-size:1.1rem;">{trim}</span>' if trim else ''}</h1>
          <div class="vdp-price-area">
            <span class="vdp-price-retail-lbl">Our Price</span>
            <span class="vdp-price-pill">{price_str}</span>
          </div>
        </div>

        <div class="row g-4">

          <!-- Left: Photo -->
          <div class="col-lg-7">
            {main_img}
            {f'<p class="text-muted text-center small mt-2">{photo_label}</p>' if photo_label else ''}
          </div>

          <!-- Right: CTAs + Specs -->
          <div class="col-lg-5">

            <!-- CTA card -->
            <div class="vdp-cta-bar mb-3">
              <a href="tel:+12524960005" class="vdp-phone-link d-flex align-items-center gap-2 mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M1.885.511a1.745 1.745 0 0 1 2.61.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.678.678 0 0 0 .178.643l2.457 2.457a.678.678 0 0 0 .644.178l2.189-.547a1.745 1.745 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.634 18.634 0 0 1-7.01-4.42 18.634 18.634 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877L1.885.511z"/>
                </svg>
                (252) 496-0005
              </a>
              <div class="d-grid gap-2">
                <a href="{apply_url}" class="btn btn-danger fw-bold">Apply for Financing</a>
                <a href="{inq_url}" class="btn btn-primary fw-bold">Inquiry / Schedule Test Drive</a>
              </div>
            </div>

            {mpg_block}

            <!-- Specs table -->
            <table class="vdp-specs-table">
              <tbody>
                {spec_rows}
              </tbody>
            </table>

          </div>
        </div><!-- /row -->

        {desc_block}
        {feat_block}

        <!-- Back to inventory -->
        <div class="mt-4 pt-2 border-top">
          <a href="{assetpfx}inventory.html" class="btn btn-secondary">
            &larr; Back to Inventory
          </a>
        </div>

      </div>
    </section>

  </main>

  <!-- ── FOOTER ── -->
  <footer style="background:#1a1a1a;color:#ccc;">
    <div class="container py-5">
      <div class="row g-5">
        <div class="col-lg-4 col-md-6">
          <h5 class="fw-bold text-white mb-3 pb-2" style="border-bottom:1px solid #444;">Contact Information</h5>
          <div class="d-flex gap-3 align-items-start mb-3">
            <div style="width:38px;height:38px;border-radius:50%;background:#3a7bd5;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#fff" viewBox="0 0 16 16"><path d="M8 16s6-5.686 6-10A6 6 0 0 0 2 6c0 4.314 6 10 6 10zm0-7a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/></svg>
            </div>
            <div>
              <div class="text-white-50 small mb-1">Address</div>
              <a href="https://maps.google.com/?q=3840+Charles+Blvd+Greenville+NC" target="_blank"
                 class="text-white text-decoration-none fw-semibold">3840 Charles Blvd<br>Greenville, NC 27858</a>
            </div>
          </div>
          <div class="d-flex gap-3 align-items-start mb-4">
            <div style="width:38px;height:38px;border-radius:50%;background:#3a7bd5;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#fff" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.885.511a1.745 1.745 0 0 1 2.61.163L6.29 2.98c.329.423.445.974.315 1.494l-.547 2.19a.678.678 0 0 0 .178.643l2.457 2.457a.678.678 0 0 0 .644.178l2.189-.547a1.745 1.745 0 0 1 1.494.315l2.306 1.794c.829.645.905 1.87.163 2.611l-1.034 1.034c-.74.74-1.846 1.065-2.877.702a18.634 18.634 0 0 1-7.01-4.42 18.634 18.634 0 0 1-4.42-7.009c-.362-1.03-.037-2.137.703-2.877L1.885.511z"/></svg>
            </div>
            <div>
              <div class="text-white-50 small mb-1">Phone</div>
              <a href="tel:+12524960005" class="text-white text-decoration-none fw-bold" style="font-size:1.15rem;">(252) 496-0005</a>
            </div>
          </div>
          <div>
            <div class="text-white-50 small mb-2">Connect</div>
            <div class="d-flex gap-2">
              <a href="https://www.facebook.com/profile.php?id=61585590120772" target="_blank" aria-label="Facebook"
                 style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:5px;background:#1877f2;color:#fff;text-decoration:none;">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8.049c0-4.446-3.582-8.05-8-8.05C3.58 0-.002 3.603-.002 8.05c0 4.017 2.926 7.347 6.75 7.951v-5.625h-2.03V8.05H6.75V6.275c0-2.017 1.195-3.131 3.022-3.131.876 0 1.791.157 1.791.157v1.98h-1.009c-.993 0-1.303.621-1.303 1.258v1.51h2.218l-.354 2.326H9.25V16c3.824-.604 6.75-3.934 6.75-7.951z"/></svg>
              </a>
            </div>
          </div>
        </div>
        <div class="col-lg-4 col-md-6">
          <h5 class="fw-bold text-white mb-3 pb-2" style="border-bottom:1px solid #444;">Store Hours</h5>
          <table class="w-100" style="font-size:.92rem;border-collapse:separate;border-spacing:0 6px;">
            <tr><td class="text-white-50" style="width:45%;">Monday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Tuesday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Wednesday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Thursday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Friday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Saturday:</td><td class="text-white fw-semibold">8:00 am – 5:30 pm</td></tr>
            <tr><td class="text-white-50">Sunday:</td><td class="text-white fw-semibold">Appointment Only</td></tr>
          </table>
        </div>
        <div class="col-lg-4 col-md-12">
          <h5 class="fw-bold text-white mb-3 pb-2" style="border-bottom:1px solid #444;">Quick Links</h5>
          <ul class="list-unstyled mb-0" style="font-size:.95rem;">
            <li class="mb-2"><a href="{assetpfx}inventory.html" class="text-white-50 text-decoration-none footer-link">Inventory</a></li>
            <li class="mb-2"><a href="{assetpfx}about.html" class="text-white-50 text-decoration-none footer-link">About Us</a></li>
            <li class="mb-2"><a href="{assetpfx}reviews.html" class="text-white-50 text-decoration-none footer-link">Reviews</a></li>
            <li class="mb-2"><a href="{assetpfx}financing.html" class="text-white-50 text-decoration-none footer-link">Financing</a></li>
            <li class="mb-2"><a href="{assetpfx}contact.html#visit" class="text-white-50 text-decoration-none footer-link">Contact Us</a></li>
            <li class="mb-2"><a href="{assetpfx}privacy.html" class="text-white-50 text-decoration-none footer-link">Privacy Policy</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div style="background:#111;border-top:1px solid #333;padding:1rem 0;">
      <div class="container text-center" style="font-size:.82rem;color:#666;">
        &copy; <span id="year"></span> Bells Fork Auto &amp; Truck &bull; 3840 Charles Blvd, Greenville, NC 27858 &bull; (252) 496-0005
      </div>
    </div>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>document.getElementById('year').textContent = new Date().getFullYear();</script>
</body>
</html>'''
    return html


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Generate VDP pages from inventory.json')
    ap.add_argument('--inventory', default='inventory.json')
    ap.add_argument('--out',       default='.')
    args = ap.parse_args()

    with open(args.inventory) as f:
        data = json.load(f)

    vehicles = data.get('vehicles', [])
    generated = []

    for v in vehicles:
        if v.get('status','available') not in ('available',''):
            continue

        sid   = slug_id(v)
        tail  = slug_tail(v)
        rel   = os.path.join('vdp', sid, tail)
        outdir = os.path.join(args.out, rel)
        os.makedirs(outdir, exist_ok=True)
        outfile = os.path.join(outdir, 'index.html')

        html = build_vdp_page(v, depth=3)   # vdp/ID/SLUG/ = 3 levels deep
        with open(outfile, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f'  ✓  {rel}/index.html')
        generated.append({'vehicle': v, 'path': rel})

    print(f'\nGenerated {len(generated)} VDP page(s).')
    return generated


if __name__ == '__main__':
    main()

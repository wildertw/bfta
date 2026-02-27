#!/usr/bin/env python3
"""
generate_vdp_pages.py
Reads inventory.json and generates a standalone HTML page for every vehicle.

Output structure:
  vdp/
    <ID>/
      <SEO-SLUG>/
        index.html

The URL format matches:
  /vdp/<ID>/<SEO-SLUG>/

Example:
  /vdp/22920062/Used-2023-Acura-MDX-Technology-for-sale-in-Greenville-NC-27858/

Usage:
  python3 generate_vdp_pages.py [--inventory PATH] [--out DIR] [--site-url URL] [--update-sitemap]

Defaults:
  --inventory  inventory.json
  --out        .   (current dir)
  --site-url   https://bellsforkautoandtruck.com
"""

import json, os, re, argparse, html, datetime, hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

def esc(s):
    return html.escape("" if s is None else str(s), quote=True)

def vehicle_id(v):
    # Prefer a stable, non-sensitive identifier (never expose VIN in URLs)
    raw = v.get("vehicleId") or v.get("stockNumber") or v.get("id")
    if raw:
        return re.sub(r"[^a-z0-9]", "", str(raw), flags=re.I)

    # Fallback: deterministic hash (VIN allowed as input but never shown)
    seed = v.get("vin") or "|".join([
        str(v.get("year","")),
        str(v.get("make","")),
        str(v.get("model","")),
        str(v.get("trim","")),
        str(v.get("price","")),
        str(v.get("mileage","")),
        str(v.get("dateAdded","")),
    ])
    h = hashlib.sha1(str(seed).encode("utf-8")).hexdigest()[:10]
    return f"v{h}"

def slug_id(v):
    # Backwards-compatible alias
    return vehicle_id(v)

def slug_tail(v, city="Greenville", state="NC", zip_code="27858"):
    parts = ["Used", v.get("year"), v.get("make"), v.get("model"), v.get("trim"),
             f"for-sale-in-{city}-{state}-{zip_code}"]
    clean = []
    for p in parts:
        if p is None:
            continue
        s = str(p).strip()
        if not s:
            continue
        s = re.sub(r"[^a-z0-9]+", "-", s, flags=re.I).strip("-")
        if s:
            clean.append(s)
    return "-".join(clean)

def fmt_price(p):
    try:
        return f"${int(float(p)):,}"
    except:
        return "Call for Price"

def fmt_int(n):
    try:
        return f"{int(float(n)):,}"
    except:
        return "—"

def write_text(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")

def update_sitemap(out_dir, vdp_urls):
    sitemap_path = Path(out_dir) / "sitemap.xml"
    if not sitemap_path.exists():
        return
    try:
        tree = ET.parse(str(sitemap_path))
        root = tree.getroot()
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0].strip("{")
        def q(tag):
            return f"{{{ns}}}{tag}" if ns else tag

        # remove old VDP entries
        for url_el in list(root.findall(q("url"))):
            loc_el = url_el.find(q("loc"))
            if loc_el is not None and loc_el.text and "/vdp/" in loc_el.text:
                root.remove(url_el)

        today = datetime.date.today().isoformat()
        for u in vdp_urls:
            url_el = ET.Element(q("url"))
            ET.SubElement(url_el, q("loc")).text = u
            ET.SubElement(url_el, q("lastmod")).text = today
            ET.SubElement(url_el, q("changefreq")).text = "weekly"
            ET.SubElement(url_el, q("priority")).text = "0.6"
            root.append(url_el)

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        sitemap_path.write_bytes(xml_bytes)
    except Exception as e:
        print(f"[WARN] Could not update sitemap.xml: {e}")

def render_vdp_html(v, *, page_url, asset_prefix, city="Greenville", state="NC", zip_code="27858"):
    year  = v.get("year") or ""
    make  = v.get("make") or ""
    model = v.get("model") or ""
    trim  = v.get("trim") or ""
    title = f"{year} {make} {model}".strip()
    full_title = f"{title} {trim}".strip()

    vin   = v.get("vin") or ""
    stock = v.get("stockNumber") or vin or "—"
    price_val = v.get("price")
    price_str = fmt_price(price_val)
    mileage = v.get("mileage")
    miles_str = f"{fmt_int(mileage)} miles" if mileage not in (None, "", 0, "0") else "Mileage N/A"
    trans = v.get("transmission") or "—"
    engine = v.get("engine") or v.get("engineSpecs") or "—"
    drive = v.get("drive") or v.get("drivetrain") or "—"
    fuel  = v.get("fuel") or v.get("fuelType") or "—"
    ext_color = v.get("exteriorColor") or v.get("color") or "—"
    int_color = v.get("interiorColor") or "—"
    body_type = v.get("type") or v.get("bodyStyle") or "—"
    badge = v.get("badge") or ""
    desc = v.get("description") or ""
    features = v.get("features") or []
    images = v.get("images") or []
    if not isinstance(features, list):
        features = [str(features)]
    if not isinstance(images, list):
        images = []

    inv_url   = f"{asset_prefix}inventory.html"
    apply_url = f"{asset_prefix}financing.html?vehicle={esc(full_title)}&vin={esc(vin)}&price={esc(price_val or '')}#applications"
    inq_url   = f"{asset_prefix}contact.html?vehicle={esc(full_title)}&vin={esc(vin)}#appointment"

    if images:
        carousel_items = []
        thumb_items = []
        gallery_tiles = []
        for i, img in enumerate(images):
            src = f"{asset_prefix}assets/vehicles/{esc(img)}"
            active = " active" if i == 0 else ""
            carousel_items.append(
                f"<div class=\"carousel-item{active}\"><img src=\"{src}\" class=\"d-block w-100 vdp-carousel-img\" alt=\"{esc(full_title)} photo {i+1}\" loading=\"lazy\"></div>"
            )
            thumb_items.append(
                f"<button type=\"button\" class=\"vdp-thumb\" data-bs-target=\"#vdpCarousel\" data-bs-slide-to=\"{i}\" aria-label=\"Go to photo {i+1}\"><img src=\"{src}\" alt=\"{esc(full_title)} thumbnail {i+1}\" loading=\"lazy\"></button>"
            )
            gallery_tiles.append(
                f"<div class=\"col-6 col-md-4 col-lg-3\"><button class=\"vdp-gallery-tile\" type=\"button\" data-bs-toggle=\"modal\" data-bs-target=\"#photoModal\" data-photo=\"{src}\" aria-label=\"Open photo\"><img src=\"{src}\" alt=\"{esc(full_title)} photo\" loading=\"lazy\"></button></div>"
            )
        carousel_html = """<div class="vdp-media">
  <div id="vdpCarousel" class="carousel slide" data-bs-ride="carousel">
    <div class="carousel-inner">
      {items}
    </div>
    <button class="carousel-control-prev" type="button" data-bs-target="#vdpCarousel" data-bs-slide="prev" aria-label="Previous photo">
      <span class="carousel-control-prev-icon" aria-hidden="true"></span>
    </button>
    <button class="carousel-control-next" type="button" data-bs-target="#vdpCarousel" data-bs-slide="next" aria-label="Next photo">
      <span class="carousel-control-next-icon" aria-hidden="true"></span>
    </button>
  </div>
  <div class="vdp-thumbs mt-2">
    {thumbs}
  </div>
</div>""".format(items="".join(carousel_items), thumbs="".join(thumb_items))
        gallery_html = "".join(gallery_tiles)
    else:
        carousel_html = """<div class="vdp-media">
  <div class="vdp-placeholder">
    <div class="text-center">
      <svg width="80" height="80" fill="#bbb" viewBox="0 0 16 16" aria-hidden="true">
        <rect x="1" y="3" width="15" height="13" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
        <circle cx="5.5" cy="14.5" r="1.5" fill="currentColor"/>
        <circle cx="12.5" cy="14.5" r="1.5" fill="currentColor"/>
      </svg>
      <div class="mt-2 text-muted" style="font-size:.9rem;">Photo Coming Soon</div>
    </div>
  </div>
</div>"""
        gallery_html = "<div class=\"text-muted\">No photos available yet.</div>"

    if features:
        features_html = "<ul class=\"list-group list-group-flush\">" + "".join(f"<li class=\"list-group-item\">{esc(f)}</li>" for f in features) + "</ul>"
    else:
        features_html = "<div class=\"text-muted\">No options listed. Ask us for details.</div>"

    desc_html = f"<p class=\"text-muted\">{esc(desc)}</p>" if desc else "<div class=\"text-muted\">Description coming soon.</div>"
    badge_html = f"<span class=\"badge bg-danger px-3 py-2\">{esc(badge)}</span>" if badge else ""

    schema = {
        "@context": "https://schema.org",
        "@type": "Car",
        "name": full_title,
        "url": page_url,
        "description": desc or f"Used {full_title} for sale in {city}, {state} {zip_code}.",
        "vehicleIdentificationNumber": vin,
        "productionDate": str(year),
        "mileageFromOdometer": {"@type":"QuantitativeValue","value": mileage or 0,"unitCode":"SMI"},
        "vehicleTransmission": trans if trans != "—" else "",
        "driveWheelConfiguration": drive if drive != "—" else "",
        "fuelType": fuel if fuel != "—" else "",
        "color": ext_color if ext_color != "—" else "",
        "manufacturer": {"@type":"Organization","name": make} if make else None,
        "model": model if model else None,
        "offers": {
            "@type":"Offer",
            "price": str(price_val) if price_val not in (None, "", "Call") else "",
            "priceCurrency":"USD",
            "availability":"https://schema.org/InStock",
            "url": page_url
        },
        "seller": {
            "@type":"AutoDealer",
            "name":"Bells Fork Auto & Truck",
            "telephone":"+1-252-496-0005",
            "address":{
                "@type":"PostalAddress",
                "streetAddress":"3840 Charles Blvd",
                "addressLocality": city,
                "addressRegion": state,
                "postalCode": zip_code,
                "addressCountry":"US"
            }
        }
    }
    schema = {k:v for k,v in schema.items() if v is not None}
    schema_json = json.dumps(schema, indent=2)

    # Build title line with trim muted
    trim_span = f" <span class=\"text-muted fw-semibold\">{esc(trim)}</span>" if trim else ""

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">

  <title>{esc(full_title)} for Sale in {city} {state} {zip_code} | Bells Fork Auto &amp; Truck</title>
  <meta name=\"description\" content=\"{esc(full_title)} for sale at Bells Fork Auto &amp; Truck in {city}, {state} {zip_code}. {esc(miles_str)}, {esc(price_str)}. VIN {esc(vin)}. Call (252) 496-0005.\">
  <meta name=\"keywords\" content=\"{esc(full_title)}, used {esc(make)} {esc(model)} {city} {state}, used trucks {zip_code}, used cars {zip_code}, Bells Fork Auto &amp; Truck\">
  <link rel=\"canonical\" href=\"{page_url}\">

  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:title\" content=\"{esc(full_title)} for Sale | Bells Fork Auto &amp; Truck\">
  <meta property=\"og:description\" content=\"{esc(full_title)} — {esc(miles_str)} — {esc(price_str)}. Available in {city}, {state}.\">
  <meta property=\"og:url\" content=\"{page_url}\">
  <meta property=\"og:site_name\" content=\"Bells Fork Auto &amp; Truck\">

  <link rel=\"icon\" type=\"image/png\" href=\"{asset_prefix}assets/favicon.png\">

  <script type=\"application/ld+json\">
{schema_json}
  </script>

  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
  <style>
    :root {{
      --bfat-red: #dc3545;
      --bfat-dark: #111111;
      --bfat-bg: #f1f1f1;
    }}
    .btn-primary, .bg-primary {{ --bs-primary: var(--bfat-red); }}
    a {{ color: var(--bfat-red); }}
    a:hover {{ color: #b02a37; }}
    body {{ background: var(--bfat-bg); }}

    .bfat-navlink {{
      color: #fff !important;
      letter-spacing: .08em;
      font-size: .86rem;
      transition: background-color .18s ease, color .18s ease;
    }}
    .bfat-navlink:hover, .bfat-navlink:focus, .bfat-navlink.active {{
      background: var(--bfat-red) !important;
      color: #fff !important;
    }}
    .site-identity-bar {{ position: relative; }}
    @media (max-width: 576px) {{
      .site-identity-bar .ms-auto {{ margin-left: 0 !important; }}
      .site-identity-bar a[style*="position:absolute"] {{
        position: static !important;
        transform: none !important;
      }}
    }}

    .vdp-breadcrumb {{
      background: #fff;
      border-bottom: 1px solid #e0e0e0;
      padding: .55rem 0;
      font-size: .82rem;
    }}
    .vdp-titlebar {{
      background: #fff;
      border: 1px solid #ddd;
      border-top: 0;
      border-radius: 0 0 10px 10px;
      padding: 1rem;
    }}
    .vdp-price-label {{
      display:inline-block;
      font-size:.72rem;
      letter-spacing:.12em;
      text-transform:uppercase;
      color:#6c757d;
    }}
    .vdp-price {{
      font-weight:900;
      font-size:1.8rem;
      line-height:1.05;
      color:#0a0a0a;
    }}
    .vdp-media {{
      background:#fff;
      border:1px solid #ddd;
      border-radius:10px;
      overflow:hidden;
    }}
    .vdp-carousel-img {{
      max-height:460px;
      object-fit:cover;
      background:#000;
    }}
    .vdp-thumbs {{
      display:flex;
      flex-wrap:wrap;
      gap:.5rem;
      padding:.75rem;
      border-top:1px solid #eee;
      background:#fff;
    }}
    .vdp-thumb {{
      border:1px solid #ddd;
      border-radius:8px;
      padding:0;
      overflow:hidden;
      width:78px;
      height:58px;
      background:#fff;
    }}
    .vdp-thumb img {{
      width:100%;
      height:100%;
      object-fit:cover;
      display:block;
    }}
    .vdp-placeholder {{
      min-height:320px;
      display:flex;
      align-items:center;
      justify-content:center;
      padding:2rem;
      background:#fff;
    }}
    .vdp-specs {{
      background:#fff;
      border:1px solid #ddd;
      border-radius:10px;
      padding:1rem;
    }}
    .vdp-specs dt {{
      color:#6c757d;
      font-weight:700;
      font-size:.78rem;
      letter-spacing:.08em;
      text-transform:uppercase;
    }}
    .vdp-specs dd {{
      margin-bottom:.75rem;
      font-weight:600;
    }}

    .nav-tabs .nav-link {{
      border-radius:10px 10px 0 0;
      font-weight:800;
      letter-spacing:.05em;
      text-transform:uppercase;
      font-size:.82rem;
      color:#222;
    }}
    .nav-tabs .nav-link.active {{
      background: var(--bfat-red);
      color:#fff;
      border-color: var(--bfat-red);
    }}
    .tab-pane {{
      background:#fff;
      border:1px solid #ddd;
      border-top:0;
      border-radius:0 0 10px 10px;
      padding:1rem;
    }}

    .vdp-gallery-tile {{
      width:100%;
      border:1px solid #ddd;
      border-radius:10px;
      overflow:hidden;
      background:#fff;
      padding:0;
    }}
    .vdp-gallery-tile img {{
      width:100%;
      height:170px;
      object-fit:cover;
      display:block;
    }}

    .vdp-cta-bar {{
      position: fixed;
      left:0; right:0; bottom:0;
      z-index:1050;
      background: rgba(17,17,17,.96);
      border-top: 1px solid rgba(255,255,255,.08);
    }}
    .vdp-cta-bar a {{
      color:#fff;
      text-decoration:none;
      font-weight:800;
      font-size:.82rem;
      letter-spacing:.06em;
      text-transform:uppercase;
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      gap:.25rem;
      padding:.7rem .4rem;
    }}
    .vdp-cta-bar a.primary {{ background: var(--bfat-red); }}
    .vdp-cta-spacer {{ height:68px; }}
    @media (min-width: 992px) {{
      .vdp-cta-bar, .vdp-cta-spacer {{ display:none; }}
    }}
  </style>
</head>

<body>

  <div class=\"site-identity-bar bg-white border-bottom py-3\" style=\"position:relative;\">
    <div class=\"container\">
      <div class=\"d-flex align-items-center justify-content-between gap-3\">
        <div class=\"d-flex flex-column align-items-start gap-1\" style=\"min-width:120px;\">
          <span class=\"fw-bold text-muted\" style=\"font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;\">Connect</span>
          <div class=\"d-flex gap-2 align-items-center\">
            <a href=\"https://www.facebook.com/\" target=\"_blank\" rel=\"noopener\" aria-label=\"Facebook\" style=\"display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:6px;background:#1877f2;color:#fff;text-decoration:none;\">f</a>
            <a href=\"https://www.instagram.com/\" target=\"_blank\" rel=\"noopener\" aria-label=\"Instagram\" style=\"display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:6px;background:linear-gradient(45deg,#fdf497,#fd5949,#d6249f,#285AEB);color:#fff;text-decoration:none;\">i</a>
          </div>
        </div>

        <a href=\"{asset_prefix}index.html\" class=\"text-decoration-none\" style=\"position:absolute;left:50%;transform:translateX(-50%);\">
          <img src=\"{asset_prefix}assets/logo.png\" alt=\"Bells Fork Truck &amp; Auto\" style=\"height:62px;max-width:280px;object-fit:contain;\">
        </a>

        <div class=\"text-end ms-auto\" style=\"min-width:160px;\">
          <a href=\"tel:+12524960005\" class=\"text-decoration-none fw-bold d-flex align-items-center justify-content-end gap-2\" style=\"font-size:1.2rem;color:#111;\">(252) 496-0005</a>
          <a href=\"https://maps.google.com/?q=3840+Charles+Blvd+Greenville+NC+27858\" target=\"_blank\" rel=\"noopener\" class=\"text-decoration-none text-muted d-flex align-items-start justify-content-end gap-1 mt-1\" style=\"font-size:.82rem;line-height:1.5;\">
            <span>3840 Charles Blvd<br>{city}, {state} {zip_code}</span>
          </a>
        </div>
      </div>
    </div>
  </div>

  <header class=\"sticky-top\" role=\"banner\" style=\"z-index:1030;\">
    <nav class=\"navbar navbar-expand-lg navbar-dark py-0\" style=\"background:#111111;\">
      <div class=\"container-fluid\">
        <button class=\"navbar-toggler border-0 ms-auto py-3\" type=\"button\" data-bs-toggle=\"collapse\" data-bs-target=\"#navMain\" aria-controls=\"navMain\" aria-expanded=\"false\" aria-label=\"Toggle navigation\">
          <span class=\"navbar-toggler-icon\"></span>
        </button>
        <div class=\"collapse navbar-collapse justify-content-center\" id=\"navMain\">
          <ul class=\"navbar-nav align-items-lg-center\">
            <li class=\"nav-item\"><a class=\"nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink active\" href=\"{asset_prefix}inventory.html\">Inventory</a></li>
            <li class=\"nav-item\"><a class=\"nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink\" href=\"{asset_prefix}about.html\">About</a></li>
            <li class=\"nav-item\"><a class=\"nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink\" href=\"{asset_prefix}reviews.html\">Reviews</a></li>
            <li class=\"nav-item\"><a class=\"nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink\" href=\"{asset_prefix}financing.html\">Financing</a></li>
            <li class=\"nav-item\"><a class=\"nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink\" href=\"{asset_prefix}contact.html\">Contact</a></li>
          </ul>
        </div>
      </div>
    </nav>
  </header>

  <div class=\"vdp-breadcrumb\">
    <div class=\"container\">
      <a href=\"{asset_prefix}index.html\" class=\"text-decoration-none\">Home</a>
      <span class=\"text-muted mx-2\">/</span>
      <a href=\"{inv_url}\" class=\"text-decoration-none\">Inventory</a>
      <span class=\"text-muted mx-2\">/</span>
      <span class=\"text-muted\">{esc(full_title)}</span>
    </div>
  </div>

  <main class=\"container my-3 my-lg-4\">
    <div class=\"vdp-titlebar\">
      <div class=\"d-flex flex-column flex-lg-row align-items-lg-center justify-content-between gap-3\">
        <div>
          {badge_html}
          <h1 class=\"h3 mb-1\" style=\"font-weight:900;\">{esc(title)}{trim_span}</h1>
          <div class=\"text-muted small\">VIN: {esc(vin) if vin else '—'} &nbsp;•&nbsp; Stock: {esc(stock)}</div>
        </div>
        <div class=\"text-lg-end\">
          <div class=\"vdp-price-label\">Our Price</div>
          <div class=\"vdp-price\">{esc(price_str)}</div>
          <div class=\"small text-muted\">{esc(miles_str)}</div>
        </div>
      </div>
    </div>

    <div class=\"row g-3 g-lg-4 mt-0 mt-lg-1\">
      <div class=\"col-lg-7\">
        {carousel_html}
      </div>
      <div class=\"col-lg-5\">
        <div class=\"vdp-specs\">
          <div class=\"d-grid gap-2 mb-3\">
            <a href=\"tel:+12524960005\" class=\"btn btn-dark fw-bold\">Call (252) 496-0005</a>
            <a href=\"{apply_url}\" class=\"btn btn-danger fw-bold\">Apply for Financing</a>
            <a href=\"{inq_url}\" class=\"btn btn-primary fw-bold\">Inquiry / Schedule Test Drive</a>
          </div>
          <dl class=\"row mb-0\">
            <div class=\"col-6\"><dt>Year</dt><dd>{esc(year) if year else '—'}</dd></div>
            <div class=\"col-6\"><dt>Make</dt><dd>{esc(make) if make else '—'}</dd></div>
            <div class=\"col-6\"><dt>Model</dt><dd>{esc(model) if model else '—'}</dd></div>
            <div class=\"col-6\"><dt>Trim</dt><dd>{esc(trim) if trim else '—'}</dd></div>
            <div class=\"col-6\"><dt>Mileage</dt><dd>{fmt_int(mileage)} mi</dd></div>
            <div class=\"col-6\"><dt>Transmission</dt><dd>{esc(trans)}</dd></div>
            <div class=\"col-6\"><dt>Engine</dt><dd>{esc(engine)}</dd></div>
            <div class=\"col-6\"><dt>Drive</dt><dd>{esc(drive)}</dd></div>
            <div class=\"col-6\"><dt>Fuel</dt><dd>{esc(fuel)}</dd></div>
            <div class=\"col-6\"><dt>Type</dt><dd>{esc(body_type)}</dd></div>
            <div class=\"col-6\"><dt>Exterior</dt><dd>{esc(ext_color)}</dd></div>
            <div class=\"col-6\"><dt>Interior</dt><dd>{esc(int_color)}</dd></div>
          </dl>
        </div>
      </div>
    </div>

    <ul class=\"nav nav-tabs mt-4\" id=\"vdpTabs\" role=\"tablist\">
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link active\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-details\" type=\"button\" role=\"tab\">Details</button></li>
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-photos\" type=\"button\" role=\"tab\">Photos</button></li>
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-options\" type=\"button\" role=\"tab\">Options</button></li>
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-description\" type=\"button\" role=\"tab\">Description</button></li>
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-inquiry\" type=\"button\" role=\"tab\">Inquiry</button></li>
      <li class=\"nav-item\" role=\"presentation\"><button class=\"nav-link\" data-bs-toggle=\"tab\" data-bs-target=\"#pane-share\" type=\"button\" role=\"tab\">Share</button></li>
    </ul>

    <div class=\"tab-content\" id=\"vdpTabsContent\">
      <div class=\"tab-pane fade show active\" id=\"pane-details\" role=\"tabpanel\">
        <div class=\"row g-3\">
          <div class=\"col-md-6\">
            <h5 class=\"fw-bold\">Highlights</h5>
            <ul class=\"mb-0\">
              <li>{esc(miles_str)}</li>
              <li>Price: {esc(price_str)}</li>
              <li>VIN: {esc(vin) if vin else '—'}</li>
            </ul>
          </div>
          <div class=\"col-md-6\">
            <h5 class=\"fw-bold\">Need more info?</h5>
            <p class=\"text-muted mb-2\">Call us or send an inquiry — we’ll get you answers fast.</p>
            <div class=\"d-grid gap-2\">
              <a class=\"btn btn-dark fw-bold\" href=\"tel:+12524960005\">Call Now</a>
              <a class=\"btn btn-danger fw-bold\" href=\"{apply_url}\">Apply for Financing</a>
              <a class=\"btn btn-primary fw-bold\" href=\"{inq_url}\">Send Inquiry</a>
            </div>
          </div>
        </div>
      </div>

      <div class=\"tab-pane fade\" id=\"pane-photos\" role=\"tabpanel\">
        <div class=\"row g-3\">
          {gallery_html}
        </div>
      </div>

      <div class=\"tab-pane fade\" id=\"pane-options\" role=\"tabpanel\">
        <h5 class=\"fw-bold\">Features &amp; Options</h5>
        {features_html}
      </div>

      <div class=\"tab-pane fade\" id=\"pane-description\" role=\"tabpanel\">
        <h5 class=\"fw-bold\">Vehicle Description</h5>
        {desc_html}
      </div>

      <div class=\"tab-pane fade\" id=\"pane-inquiry\" role=\"tabpanel\">
        <h5 class=\"fw-bold\">Vehicle Inquiry</h5>
        <p class=\"text-muted\">This form forwards you to the Contact page with the vehicle pre-filled.</p>
        <form id=\"vdpInquiryForm\" class=\"row g-3\">
          <div class=\"col-md-6\"><label class=\"form-label\">First Name</label><input class=\"form-control\" name=\"firstName\" required></div>
          <div class=\"col-md-6\"><label class=\"form-label\">Last Name</label><input class=\"form-control\" name=\"lastName\" required></div>
          <div class=\"col-md-6\"><label class=\"form-label\">Email</label><input class=\"form-control\" type=\"email\" name=\"email\" required></div>
          <div class=\"col-md-6\"><label class=\"form-label\">Phone</label><input class=\"form-control\" name=\"phone\"></div>
          <div class=\"col-12\"><label class=\"form-label\">Message</label><textarea class=\"form-control\" name=\"message\" rows=\"4\">I’m interested in the {esc(full_title)} (VIN {esc(vin)}). Please contact me.</textarea></div>
          <div class=\"col-12 d-grid d-sm-flex gap-2\">
            <button class=\"btn btn-danger fw-bold\" type=\"submit\">Continue to Contact Page</button>
            <a class=\"btn btn-outline-dark fw-bold\" href=\"tel:+12524960005\">Call Instead</a>
          </div>
        </form>
      </div>

      <div class=\"tab-pane fade\" id=\"pane-share\" role=\"tabpanel\">
        <h5 class=\"fw-bold\">Share this vehicle</h5>
        <div class=\"d-grid d-sm-flex gap-2\">
          <button class=\"btn btn-dark fw-bold\" id=\"copyLinkBtn\" type=\"button\">Copy Link</button>
          <a class=\"btn btn-outline-danger fw-bold\" target=\"_blank\" rel=\"noopener\" href=\"https://www.facebook.com/sharer/sharer.php?u={esc(page_url)}\">Share on Facebook</a>
        </div>
        <p class=\"text-muted mt-3 mb-0 small\">SEO URL: <span class=\"text-break\">{esc(page_url)}</span></p>
      </div>
    </div>

    <div class=\"vdp-cta-spacer\"></div>
  </main>

  <div class=\"modal fade\" id=\"photoModal\" tabindex=\"-1\" aria-hidden=\"true\">
    <div class=\"modal-dialog modal-dialog-centered modal-xl\">
      <div class=\"modal-content\">
        <div class=\"modal-header\">
          <h5 class=\"modal-title\">{esc(full_title)}</h5>
          <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"modal\" aria-label=\"Close\"></button>
        </div>
        <div class=\"modal-body p-0\">
          <img id=\"photoModalImg\" src=\"\" alt=\"Vehicle photo\" style=\"width:100%;height:auto;display:block;\">
        </div>
      </div>
    </div>
  </div>

  <div class=\"vdp-cta-bar d-lg-none\">
    <div class=\"container\">
      <div class=\"row g-0 text-center\">
        <div class=\"col-3\"><a href=\"tel:+12524960005\"><span>Call</span></a></div>
        <div class=\"col-3\"><a href=\"{apply_url}\"><span>Finance</span></a></div>
        <div class=\"col-3\"><a class=\"primary\" href=\"{inq_url}\"><span>Inquiry</span></a></div>
        <div class=\"col-3\"><a href=\"{inv_url}\"><span>Inventory</span></a></div>
      </div>
    </div>
  </div>

  <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
  <script>
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {{
      photoModal.addEventListener('show.bs.modal', function (event) {{
        const btn = event.relatedTarget;
        const src = btn && btn.getAttribute('data-photo');
        const img = document.getElementById('photoModalImg');
        if (img && src) img.src = src;
      }});
    }}

    const copyBtn = document.getElementById('copyLinkBtn');
    if (copyBtn) {{
      copyBtn.addEventListener('click', async () => {{
        try {{
          await navigator.clipboard.writeText(window.location.href);
          copyBtn.textContent = 'Copied!';
          setTimeout(() => copyBtn.textContent = 'Copy Link', 1200);
        }} catch (e) {{
          alert('Copy failed. You can copy the URL from your browser address bar.');
        }}
      }});
    }}

    const inquiryForm = document.getElementById('vdpInquiryForm');
    if (inquiryForm) {{
      inquiryForm.addEventListener('submit', (e) => {{
        e.preventDefault();
        const fd = new FormData(inquiryForm);
        const params = new URLSearchParams();
        params.set('vehicle', "{esc(full_title)}");
        params.set('vin', "{esc(vin)}");
        params.set('firstName', fd.get('firstName') || '');
        params.set('lastName', fd.get('lastName') || '');
        params.set('email', fd.get('email') || '');
        params.set('phone', fd.get('phone') || '');
        params.set('message', fd.get('message') || '');
        window.location.href = "{asset_prefix}contact.html?" + params.toString() + "#appointment";
      }});
    }}
  </script>
</body>
</html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", default="inventory.json")
    ap.add_argument("--out", default=".")
    ap.add_argument("--site-url", default="https://bellsforkautoandtruck.com")
    ap.add_argument("--city", default="Greenville")
    ap.add_argument("--state", default="NC")
    ap.add_argument("--zip", dest="zip_code", default="27858")
    ap.add_argument("--no-update-sitemap", action="store_true")
    args = ap.parse_args()

    inv_path = Path(args.inventory)
    out_dir = Path(args.out)
    data = json.loads(inv_path.read_text(encoding="utf-8"))
    vehicles = data.get("vehicles", [])
    if not isinstance(vehicles, list):
        raise SystemExit("inventory.json: expected vehicles to be a list")

    vdp_urls = []
    count = 0

    for v in vehicles:
        sid = slug_id(v)
        tail = slug_tail(v, city=args.city, state=args.state, zip_code=args.zip_code)
        rel_dir = Path("vdp") / sid / tail
        out_path = out_dir / rel_dir / "index.html"
        page_url = f"{args.site_url.rstrip('/')}/{rel_dir.as_posix()}/"
        asset_prefix = "../../../"

        html_text = render_vdp_html(v, page_url=page_url, asset_prefix=asset_prefix, city=args.city, state=args.state, zip_code=args.zip_code)
        write_text(out_path, html_text)
        vdp_urls.append(page_url)
        count += 1

    if not args.no_update_sitemap:
        update_sitemap(out_dir, vdp_urls)

    print(f"Generated {count} VDP pages into {out_dir}/vdp/")

if __name__ == "__main__":
    main()

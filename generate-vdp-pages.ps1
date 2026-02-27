Param(
  [string]$Inventory = "inventory.json",
  [string]$OutDir = ".",
  [string]$SiteUrl = "https://bellsforkautoandtruck.com",
  [string]$City = "Greenville",
  [string]$State = "NC",
  [string]$Zip = "27858",
  [switch]$NoUpdateSitemap
)

function Escape-Html([string]$s) {
  if ($null -eq $s) { return "" }
  return [System.Net.WebUtility]::HtmlEncode($s)
}

function Slug-Id($v) {
  # Prefer a stable, non-sensitive identifier (never expose VIN in URLs)
  $raw = $v.vehicleId
  if (-not $raw) { $raw = $v.stockNumber }
  if (-not $raw) { $raw = $v.id }

  if (-not $raw) {
    # Fallback: deterministic SHA-1 hash (VIN allowed as input but never shown)
    $seed = $v.vin
    if (-not $seed) {
      $seed = @($v.year,$v.make,$v.model,$v.trim,$v.price,$v.mileage,$v.dateAdded) -join '|'
      if (-not $seed) { $seed = "NA" }
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($seed.ToString())
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    $hash = ($sha1.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ''
    $raw = "v" + $hash.Substring(0, 10)
  }

  return ($raw.ToString() -replace '[^a-zA-Z0-9]','')
}

function Slug-Part([object]$p) {
  if ($null -eq $p) { return $null }
  $s = $p.ToString().Trim()
  if (-not $s) { return $null }
  $s = ($s -replace '[^a-zA-Z0-9]+','-').Trim('-')
  if (-not $s) { return $null }
  return $s
}

function Slug-Tail($v) {
  $parts = @("Used", $v.year, $v.make, $v.model, $v.trim, "for-sale-in-$City-$State-$Zip")
  $clean = @()
  foreach ($p in $parts) {
    $sp = Slug-Part $p
    if ($sp) { $clean += $sp }
  }
  return ($clean -join '-')
}

function Ensure-Dir([string]$p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

function Update-Sitemap([string[]]$VdpUrls) {
  $sitemapPath = Join-Path $OutDir "sitemap.xml"
  if (-not (Test-Path $sitemapPath)) { return }
  try {
    [xml]$xml = Get-Content -Raw $sitemapPath
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace("sm", "http://www.sitemaps.org/schemas/sitemap/0.9") | Out-Null

    # Remove old /vdp/ entries
    $urls = $xml.SelectNodes("//sm:url", $ns)
    foreach ($u in @($urls)) {
      $loc = $u.SelectSingleNode("sm:loc", $ns)
      if ($loc -and $loc.InnerText -like "*\/vdp\/*") {
        $null = $u.ParentNode.RemoveChild($u)
      }
    }

    $today = (Get-Date).ToString("yyyy-MM-dd")
    foreach ($u in $VdpUrls) {
      $urlNode = $xml.CreateElement("url", $xml.DocumentElement.NamespaceURI)
      $locNode = $xml.CreateElement("loc", $xml.DocumentElement.NamespaceURI); $locNode.InnerText = $u
      $lmNode  = $xml.CreateElement("lastmod", $xml.DocumentElement.NamespaceURI); $lmNode.InnerText = $today
      $cfNode  = $xml.CreateElement("changefreq", $xml.DocumentElement.NamespaceURI); $cfNode.InnerText = "weekly"
      $prNode  = $xml.CreateElement("priority", $xml.DocumentElement.NamespaceURI); $prNode.InnerText = "0.6"
      $null = $urlNode.AppendChild($locNode)
      $null = $urlNode.AppendChild($lmNode)
      $null = $urlNode.AppendChild($cfNode)
      $null = $urlNode.AppendChild($prNode)
      $null = $xml.DocumentElement.AppendChild($urlNode)
    }

    $xml.Save($sitemapPath)
  } catch {
    Write-Host "[WARN] Could not update sitemap.xml: $($_.Exception.Message)"
  }
}

# ---- Load inventory ----
if (-not (Test-Path $Inventory)) {
  Write-Error "Inventory file not found: $Inventory"
  exit 1
}

$data = Get-Content -Raw $Inventory | ConvertFrom-Json
if (-not $data.vehicles) {
  Write-Error "inventory.json missing vehicles[]"
  exit 1
}

$vdpUrls = @()
$count = 0

foreach ($v in $data.vehicles) {
  $id = Slug-Id $v
  $tail = Slug-Tail $v
  $relDir = "vdp/$id/$tail"
  $pageUrl = ($SiteUrl.TrimEnd('/') + "/" + $relDir + "/")

  $outPath = Join-Path $OutDir (Join-Path (Join-Path "vdp" $id) (Join-Path $tail "index.html"))
  Ensure-Dir (Split-Path -Parent $outPath)

  $assetPrefix = "../../../"

  $year = Escape-Html ($v.year)
  $make = Escape-Html ($v.make)
  $model = Escape-Html ($v.model)
  $trim = Escape-Html ($v.trim)
  $title = ("$($v.year) $($v.make) $($v.model)").Trim()
  $fullTitle = ("$title $($v.trim)").Trim()
  $vin = Escape-Html ($v.vin)
  $stock = Escape-Html ($v.stockNumber)
  if (-not $stock) { $stock = $vin }
  if (-not $stock) { $stock = "—" }

  $priceStr = "Call for Price"
  if ($v.price) {
    try { $priceStr = ("$" + ([int]$v.price).ToString("N0")) } catch {}
  }

  $milesStr = "Mileage N/A"
  if ($v.mileage) {
    try { $milesStr = ([int]$v.mileage).ToString("N0") + " miles" } catch {}
  }

  $trans = Escape-Html ($v.transmission)
  if (-not $trans) { $trans = "—" }
  $engine = Escape-Html ($v.engine)
  if (-not $engine) { $engine = Escape-Html ($v.engineSpecs) }
  if (-not $engine) { $engine = "—" }

  $drive = Escape-Html ($v.drive)
  if (-not $drive) { $drive = Escape-Html ($v.drivetrain) }
  if (-not $drive) { $drive = "—" }

  $fuel = Escape-Html ($v.fuelType)
  if (-not $fuel) { $fuel = Escape-Html ($v.fuel) }
  if (-not $fuel) { $fuel = "—" }

  $extColor = Escape-Html ($v.exteriorColor)
  if (-not $extColor) { $extColor = Escape-Html ($v.color) }
  if (-not $extColor) { $extColor = "—" }

  $intColor = Escape-Html ($v.interiorColor)
  if (-not $intColor) { $intColor = "—" }

  $type = Escape-Html ($v.type)
  if (-not $type) { $type = Escape-Html ($v.bodyStyle) }
  if (-not $type) { $type = "—" }

  $badge = Escape-Html ($v.badge)
  $badgeHtml = ""
  if ($badge) { $badgeHtml = "<span class='badge bg-danger px-3 py-2'>$badge</span>" }

  $desc = Escape-Html ($v.description)
  $descHtml = "<div class='text-muted'>Description coming soon.</div>"
  if ($desc) { $descHtml = "<p class='text-muted'>$desc</p>" }

  $featuresHtml = "<div class='text-muted'>No options listed. Ask us for details.</div>"
  if ($v.features) {
    $lis = @()
    foreach ($f in $v.features) { $lis += "<li class='list-group-item'>$(Escape-Html $f)</li>" }
    $featuresHtml = "<ul class='list-group list-group-flush'>" + ($lis -join "") + "</ul>"
  }

  $invUrl = $assetPrefix + "inventory.html"
  $applyUrl = $assetPrefix + "financing.html?vehicle=" + [uri]::EscapeDataString($fullTitle) + "&vin=" + [uri]::EscapeDataString($v.vin) + "&price=" + [uri]::EscapeDataString([string]$v.price) + "#applications"
  $inqUrl = $assetPrefix + "contact.html?vehicle=" + [uri]::EscapeDataString($fullTitle) + "&vin=" + [uri]::EscapeDataString($v.vin) + "#appointment"

  # Build carousel + gallery
  $carouselHtml = ""
  $galleryHtml = ""

  if ($v.images -and $v.images.Count -gt 0) {
    $items = @()
    $thumbs = @()
    $tiles = @()
    for ($i=0; $i -lt $v.images.Count; $i++) {
      $img = $v.images[$i]
      $src = $assetPrefix + "assets/vehicles/" + (Escape-Html $img)
      $active = ""
      if ($i -eq 0) { $active = " active" }
      $items += "<div class='carousel-item$active'><img src='$src' class='d-block w-100 vdp-carousel-img' alt='$(Escape-Html $fullTitle) photo $($i+1)' loading='lazy'></div>"
      $thumbs += "<button type='button' class='vdp-thumb' data-bs-target='#vdpCarousel' data-bs-slide-to='$i' aria-label='Go to photo $($i+1)'><img src='$src' alt='$(Escape-Html $fullTitle) thumbnail $($i+1)' loading='lazy'></button>"
      $tiles += "<div class='col-6 col-md-4 col-lg-3'><button class='vdp-gallery-tile' type='button' data-bs-toggle='modal' data-bs-target='#photoModal' data-photo='$src' aria-label='Open photo'><img src='$src' alt='$(Escape-Html $fullTitle) photo' loading='lazy'></button></div>"
    }

    $carouselHtml = @"
<div class="vdp-media">
  <div id="vdpCarousel" class="carousel slide" data-bs-ride="carousel">
    <div class="carousel-inner">
      $($items -join "")
    </div>
    <button class="carousel-control-prev" type="button" data-bs-target="#vdpCarousel" data-bs-slide="prev" aria-label="Previous photo">
      <span class="carousel-control-prev-icon" aria-hidden="true"></span>
    </button>
    <button class="carousel-control-next" type="button" data-bs-target="#vdpCarousel" data-bs-slide="next" aria-label="Next photo">
      <span class="carousel-control-next-icon" aria-hidden="true"></span>
    </button>
  </div>
  <div class="vdp-thumbs mt-2">
    $($thumbs -join "")
  </div>
</div>
"@

    $galleryHtml = ($tiles -join "")
  } else {
    $carouselHtml = @"
<div class="vdp-media">
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
</div>
"@
    $galleryHtml = "<div class='text-muted'>No photos available yet.</div>"
  }

  $trimSpan = ""
  if ($trim) { $trimSpan = " <span class='text-muted fw-semibold'>$trim</span>" }

  $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$(Escape-Html $fullTitle) for Sale in $City $State $Zip | Bells Fork Auto &amp; Truck</title>
  <meta name="description" content="$(Escape-Html $fullTitle) for sale at Bells Fork Auto &amp; Truck in $City, $State $Zip. $milesStr, $priceStr. VIN $vin. Call (252) 496-0005.">
  <link rel="canonical" href="$pageUrl">
  <link rel="icon" type="image/png" href="${assetPrefix}assets/favicon.png">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    :root { --bfat-red:#dc3545; --bfat-dark:#111111; --bfat-bg:#f1f1f1; }
    .btn-primary, .bg-primary { --bs-primary: var(--bfat-red); }
    a{ color: var(--bfat-red);} a:hover{ color:#b02a37;}
    body{ background: var(--bfat-bg); }
    .bfat-navlink{ color:#fff !important; letter-spacing:.08em; font-size:.86rem; transition:background-color .18s ease,color .18s ease;}
    .bfat-navlink:hover,.bfat-navlink:focus,.bfat-navlink.active{ background:var(--bfat-red) !important; color:#fff !important;}
    .site-identity-bar{ position:relative;}
    @media (max-width:576px){ .site-identity-bar .ms-auto{ margin-left:0 !important;} .site-identity-bar a[style*="position:absolute"]{ position:static !important; transform:none !important; } }
    .vdp-breadcrumb{ background:#fff; border-bottom:1px solid #e0e0e0; padding:.55rem 0; font-size:.82rem;}
    .vdp-titlebar{ background:#fff; border:1px solid #ddd; border-top:0; border-radius:0 0 10px 10px; padding:1rem;}
    .vdp-price-label{ display:inline-block; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:#6c757d;}
    .vdp-price{ font-weight:900; font-size:1.8rem; line-height:1.05; color:#0a0a0a;}
    .vdp-media{ background:#fff; border:1px solid #ddd; border-radius:10px; overflow:hidden;}
    .vdp-carousel-img{ max-height:460px; object-fit:cover; background:#000;}
    .vdp-thumbs{ display:flex; flex-wrap:wrap; gap:.5rem; padding:.75rem; border-top:1px solid #eee; background:#fff;}
    .vdp-thumb{ border:1px solid #ddd; border-radius:8px; padding:0; overflow:hidden; width:78px; height:58px; background:#fff;}
    .vdp-thumb img{ width:100%; height:100%; object-fit:cover; display:block;}
    .vdp-placeholder{ min-height:320px; display:flex; align-items:center; justify-content:center; padding:2rem; background:#fff;}
    .vdp-specs{ background:#fff; border:1px solid #ddd; border-radius:10px; padding:1rem;}
    .vdp-specs dt{ color:#6c757d; font-weight:700; font-size:.78rem; letter-spacing:.08em; text-transform:uppercase;}
    .vdp-specs dd{ margin-bottom:.75rem; font-weight:600;}
    .nav-tabs .nav-link{ border-radius:10px 10px 0 0; font-weight:800; letter-spacing:.05em; text-transform:uppercase; font-size:.82rem; color:#222;}
    .nav-tabs .nav-link.active{ background:var(--bfat-red); color:#fff; border-color:var(--bfat-red);}
    .tab-pane{ background:#fff; border:1px solid #ddd; border-top:0; border-radius:0 0 10px 10px; padding:1rem;}
    .vdp-gallery-tile{ width:100%; border:1px solid #ddd; border-radius:10px; overflow:hidden; background:#fff; padding:0;}
    .vdp-gallery-tile img{ width:100%; height:170px; object-fit:cover; display:block;}
    .vdp-cta-bar{ position:fixed; left:0; right:0; bottom:0; z-index:1050; background:rgba(17,17,17,.96); border-top:1px solid rgba(255,255,255,.08);}
    .vdp-cta-bar a{ color:#fff; text-decoration:none; font-weight:800; font-size:.82rem; letter-spacing:.06em; text-transform:uppercase; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.25rem; padding:.7rem .4rem;}
    .vdp-cta-bar a.primary{ background:var(--bfat-red);}
    .vdp-cta-spacer{ height:68px;}
    @media (min-width:992px){ .vdp-cta-bar,.vdp-cta-spacer{ display:none; } }
  </style>
</head>
<body>

  <div class="site-identity-bar bg-white border-bottom py-3" style="position:relative;">
    <div class="container">
      <div class="d-flex align-items-center justify-content-between gap-3">
        <div class="d-flex flex-column align-items-start gap-1" style="min-width:120px;">
          <span class="fw-bold text-muted" style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;">Connect</span>
          <div class="d-flex gap-2 align-items-center">
            <a href="https://www.facebook.com/" target="_blank" rel="noopener" aria-label="Facebook" style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:6px;background:#1877f2;color:#fff;text-decoration:none;">f</a>
            <a href="https://www.instagram.com/" target="_blank" rel="noopener" aria-label="Instagram" style="display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:6px;background:linear-gradient(45deg,#fdf497,#fd5949,#d6249f,#285AEB);color:#fff;text-decoration:none;">i</a>
          </div>
        </div>

        <a href="${assetPrefix}index.html" class="text-decoration-none" style="position:absolute;left:50%;transform:translateX(-50%);">
          <img src="${assetPrefix}assets/logo.png" alt="Bells Fork Truck &amp; Auto" style="height:62px;max-width:280px;object-fit:contain;">
        </a>

        <div class="text-end ms-auto" style="min-width:160px;">
          <a href="tel:+12524960005" class="text-decoration-none fw-bold d-flex align-items-center justify-content-end gap-2" style="font-size:1.2rem;color:#111;">(252) 496-0005</a>
          <a href="https://maps.google.com/?q=3840+Charles+Blvd+Greenville+NC+27858" target="_blank" rel="noopener" class="text-decoration-none text-muted d-flex align-items-start justify-content-end gap-1 mt-1" style="font-size:.82rem;line-height:1.5;">
            <span>3840 Charles Blvd<br>$City, $State $Zip</span>
          </a>
        </div>
      </div>
    </div>
  </div>

  <header class="sticky-top" role="banner" style="z-index:1030;">
    <nav class="navbar navbar-expand-lg navbar-dark py-0" style="background:#111111;">
      <div class="container-fluid">
        <button class="navbar-toggler border-0 ms-auto py-3" type="button" data-bs-toggle="collapse" data-bs-target="#navMain" aria-controls="navMain" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse justify-content-center" id="navMain">
          <ul class="navbar-nav align-items-lg-center">
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink active" href="${assetPrefix}inventory.html">Inventory</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="${assetPrefix}about.html">About</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="${assetPrefix}reviews.html">Reviews</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="${assetPrefix}financing.html">Financing</a></li>
            <li class="nav-item"><a class="nav-link px-4 py-3 fw-semibold text-uppercase bfat-navlink" href="${assetPrefix}contact.html">Contact</a></li>
          </ul>
        </div>
      </div>
    </nav>
  </header>

  <div class="vdp-breadcrumb">
    <div class="container">
      <a href="${assetPrefix}index.html" class="text-decoration-none">Home</a>
      <span class="text-muted mx-2">/</span>
      <a href="$invUrl" class="text-decoration-none">Inventory</a>
      <span class="text-muted mx-2">/</span>
      <span class="text-muted">$(Escape-Html $fullTitle)</span>
    </div>
  </div>

  <main class="container my-3 my-lg-4">
    <div class="vdp-titlebar">
      <div class="d-flex flex-column flex-lg-row align-items-lg-center justify-content-between gap-3">
        <div>
          $badgeHtml
          <h1 class="h3 mb-1" style="font-weight:900;">$(Escape-Html $title)$trimSpan</h1>
          <div class="text-muted small">VIN: $vin &nbsp;•&nbsp; Stock: $stock</div>
        </div>
        <div class="text-lg-end">
          <div class="vdp-price-label">Our Price</div>
          <div class="vdp-price">$priceStr</div>
          <div class="small text-muted">$milesStr</div>
        </div>
      </div>
    </div>

    <div class="row g-3 g-lg-4 mt-0 mt-lg-1">
      <div class="col-lg-7">
        $carouselHtml
      </div>
      <div class="col-lg-5">
        <div class="vdp-specs">
          <div class="d-grid gap-2 mb-3">
            <a href="tel:+12524960005" class="btn btn-dark fw-bold">Call (252) 496-0005</a>
            <a href="$applyUrl" class="btn btn-danger fw-bold">Apply for Financing</a>
            <a href="$inqUrl" class="btn btn-primary fw-bold">Inquiry / Schedule Test Drive</a>
          </div>
          <dl class="row mb-0">
            <div class="col-6"><dt>Year</dt><dd>$year</dd></div>
            <div class="col-6"><dt>Make</dt><dd>$make</dd></div>
            <div class="col-6"><dt>Model</dt><dd>$model</dd></div>
            <div class="col-6"><dt>Trim</dt><dd>$trim</dd></div>
            <div class="col-6"><dt>Mileage</dt><dd>$(Escape-Html ($v.mileage))</dd></div>
            <div class="col-6"><dt>Transmission</dt><dd>$trans</dd></div>
            <div class="col-6"><dt>Engine</dt><dd>$engine</dd></div>
            <div class="col-6"><dt>Drive</dt><dd>$drive</dd></div>
            <div class="col-6"><dt>Fuel</dt><dd>$fuel</dd></div>
            <div class="col-6"><dt>Type</dt><dd>$type</dd></div>
            <div class="col-6"><dt>Exterior</dt><dd>$extColor</dd></div>
            <div class="col-6"><dt>Interior</dt><dd>$intColor</dd></div>
          </dl>
        </div>
      </div>
    </div>

    <ul class="nav nav-tabs mt-4" id="vdpTabs" role="tablist">
      <li class="nav-item" role="presentation"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#pane-details" type="button" role="tab">Details</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-photos" type="button" role="tab">Photos</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-options" type="button" role="tab">Options</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-description" type="button" role="tab">Description</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-inquiry" type="button" role="tab">Inquiry</button></li>
      <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-share" type="button" role="tab">Share</button></li>
    </ul>

    <div class="tab-content" id="vdpTabsContent">
      <div class="tab-pane fade show active" id="pane-details" role="tabpanel">
        <div class="row g-3">
          <div class="col-md-6">
            <h5 class="fw-bold">Highlights</h5>
            <ul class="mb-0">
              <li>$milesStr</li>
              <li>Price: $priceStr</li>
              <li>VIN: $vin</li>
            </ul>
          </div>
          <div class="col-md-6">
            <h5 class="fw-bold">Need more info?</h5>
            <p class="text-muted mb-2">Call us or send an inquiry — we’ll get you answers fast.</p>
            <div class="d-grid gap-2">
              <a class="btn btn-dark fw-bold" href="tel:+12524960005">Call Now</a>
              <a class="btn btn-danger fw-bold" href="$applyUrl">Apply for Financing</a>
              <a class="btn btn-primary fw-bold" href="$inqUrl">Send Inquiry</a>
            </div>
          </div>
        </div>
      </div>

      <div class="tab-pane fade" id="pane-photos" role="tabpanel">
        <div class="row g-3">
          $galleryHtml
        </div>
      </div>

      <div class="tab-pane fade" id="pane-options" role="tabpanel">
        <h5 class="fw-bold">Features &amp; Options</h5>
        $featuresHtml
      </div>

      <div class="tab-pane fade" id="pane-description" role="tabpanel">
        <h5 class="fw-bold">Vehicle Description</h5>
        $descHtml
      </div>

      <div class="tab-pane fade" id="pane-inquiry" role="tabpanel">
        <h5 class="fw-bold">Vehicle Inquiry</h5>
        <p class="text-muted">This form forwards you to the Contact page with the vehicle pre-filled.</p>
        <form id="vdpInquiryForm" class="row g-3">
          <div class="col-md-6"><label class="form-label">First Name</label><input class="form-control" name="firstName" required></div>
          <div class="col-md-6"><label class="form-label">Last Name</label><input class="form-control" name="lastName" required></div>
          <div class="col-md-6"><label class="form-label">Email</label><input class="form-control" type="email" name="email" required></div>
          <div class="col-md-6"><label class="form-label">Phone</label><input class="form-control" name="phone"></div>
          <div class="col-12"><label class="form-label">Message</label><textarea class="form-control" name="message" rows="4">I’m interested in the $(Escape-Html $fullTitle) (VIN $vin). Please contact me.</textarea></div>
          <div class="col-12 d-grid d-sm-flex gap-2">
            <button class="btn btn-danger fw-bold" type="submit">Continue to Contact Page</button>
            <a class="btn btn-outline-dark fw-bold" href="tel:+12524960005">Call Instead</a>
          </div>
        </form>
      </div>

      <div class="tab-pane fade" id="pane-share" role="tabpanel">
        <h5 class="fw-bold">Share this vehicle</h5>
        <div class="d-grid d-sm-flex gap-2">
          <button class="btn btn-dark fw-bold" id="copyLinkBtn" type="button">Copy Link</button>
          <a class="btn btn-outline-danger fw-bold" target="_blank" rel="noopener" href="https://www.facebook.com/sharer/sharer.php?u=$pageUrl">Share on Facebook</a>
        </div>
        <p class="text-muted mt-3 mb-0 small">SEO URL: <span class="text-break">$pageUrl</span></p>
      </div>
    </div>

    <div class="vdp-cta-spacer"></div>
  </main>

  <div class="modal fade" id="photoModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-xl">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">$(Escape-Html $fullTitle)</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-0">
          <img id="photoModalImg" src="" alt="Vehicle photo" style="width:100%;height:auto;display:block;">
        </div>
      </div>
    </div>
  </div>

  <div class="vdp-cta-bar d-lg-none">
    <div class="container">
      <div class="row g-0 text-center">
        <div class="col-3"><a href="tel:+12524960005"><span>Call</span></a></div>
        <div class="col-3"><a href="$applyUrl"><span>Finance</span></a></div>
        <div class="col-3"><a class="primary" href="$inqUrl"><span>Inquiry</span></a></div>
        <div class="col-3"><a href="$invUrl"><span>Inventory</span></a></div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
      photoModal.addEventListener('show.bs.modal', function (event) {
        const btn = event.relatedTarget;
        const src = btn && btn.getAttribute('data-photo');
        const img = document.getElementById('photoModalImg');
        if (img && src) img.src = src;
      });
    }

    const copyBtn = document.getElementById('copyLinkBtn');
    if (copyBtn) {
      copyBtn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(window.location.href);
          copyBtn.textContent = 'Copied!';
          setTimeout(() => copyBtn.textContent = 'Copy Link', 1200);
        } catch (e) {
          alert('Copy failed. You can copy the URL from your browser address bar.');
        }
      });
    }

    const inquiryForm = document.getElementById('vdpInquiryForm');
    if (inquiryForm) {
      inquiryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const fd = new FormData(inquiryForm);
        const params = new URLSearchParams();
        params.set('vehicle', "$fullTitle");
        params.set('vin', "$($v.vin)");
        params.set('firstName', fd.get('firstName') || '');
        params.set('lastName', fd.get('lastName') || '');
        params.set('email', fd.get('email') || '');
        params.set('phone', fd.get('phone') || '');
        params.set('message', fd.get('message') || '');
        window.location.href = "${assetPrefix}contact.html?" + params.toString() + "#appointment";
      });
    }
  </script>
</body>
</html>
"@

  Set-Content -Path $outPath -Value $html -Encoding UTF8

  $vdpUrls += $pageUrl
  $count++
}

if (-not $NoUpdateSitemap) {
  Update-Sitemap $vdpUrls
}

Write-Host "Generated $count VDP pages into $OutDir/vdp/"

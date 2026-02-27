// inventory-loader.js - Dynamic Inventory Loading System
// Place this file in your website root and include it in your HTML pages.

class InventoryLoader {
  constructor(jsonPath = 'inventory.json') {
    this.jsonPath = jsonPath;
    this.vehicles = [];
    this.grid = document.getElementById('inventoryGrid');
    this.limit = this.grid ? parseInt(this.grid.getAttribute('data-limit') || '', 10) : NaN;
  }

  // Build SEO-friendly VDP URL matching generate_vdp_pages.py format
  buildVDPUrl(v) {
    // Must match generate_vdp_pages_NO_VIN_URL.py and inventory.html buildVDPUrl()
    const id = this.vehicleId(v);

    const parts = ['Used', v.year, v.make, v.model, v.trim, 'for-sale-in-Greenville-NC-27858']
      .filter(Boolean)
      .map(p => String(p).trim().replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, ''))
      .filter(Boolean);

    const slug = parts.join('-');
    return `/vdp/${id}/${slug}/`;
  }

  vehicleId(v) {
    // Prefer non-sensitive stable ids
    const raw = (v.vehicleId || v.stockNumber || v.id);
    if (raw) return String(raw).replace(/[^a-z0-9]/gi, '');

    // Fallback: deterministic hash (VIN can be used as input but is never shown)
    const seed = (v.vin || [v.year, v.make, v.model, v.trim, v.price, v.mileage, v.dateAdded].filter(Boolean).join('|') || 'NA');
    const h = sha1Hex(String(seed)).slice(0, 10);
    return `v${h}`;
  }

  // SHA-1 now provided by assets/js/utils.js (sha1Hex)

  // Load inventory from JSON
  async loadInventory() {
    try {
      const response = await fetch(this.jsonPath);
      if (!response.ok) {
        throw new Error('Could not load inventory');
      }
      const data = await response.json();
      this.vehicles = data.vehicles || [];
      const sorted = this.getMostRecent(this.vehicles);
      this.renderVehicles(sorted);
      return this.vehicles;
    } catch (error) {
      console.error('Error loading inventory:', error);
      this.showError();
      return [];
    }
  }

  // Return vehicles sorted by dateAdded descending, optionally limited
  getMostRecent(vehicles) {
    const available = vehicles.filter(v => v.status === 'available' || !v.status);
    const sorted = [...available].sort((a, b) => {
      const dateA = a.dateAdded ? new Date(a.dateAdded) : new Date(0);
      const dateB = b.dateAdded ? new Date(b.dateAdded) : new Date(0);
      return dateB - dateA;
    });
    return isNaN(this.limit) ? sorted : sorted.slice(0, this.limit);
  }

  // Render vehicles to the grid
  renderVehicles(vehicles) {
    if (!this.grid) return;

    if (vehicles.length === 0) {
      this.grid.innerHTML = '<div class="col-12 text-center py-5"><p class="text-muted">No vehicles found matching your criteria.</p></div>';
      return;
    }

    this.grid.innerHTML = vehicles.map(vehicle => this.createVehicleCard(vehicle)).join('');
  }

  // Create vehicle card HTML
  createVehicleCard(v) {
    const priceRange = this.getPriceRange(v.price);
    const mainImage = v.images && v.images.length > 0 ? v.images[0] : '';
    const badgeClass = this.getBadgeClass(v.badge);
    const features = v.features || [];

    const vehicleLabel = `${v.year} ${v.make} ${v.model}${v.trim ? ' ' + v.trim : ''}`.trim();
    const applyHref = `financing.html?tab=financing&vehicle=${encodeURIComponent(vehicleLabel)}&vin=${encodeURIComponent(v.vin || '')}&price=${encodeURIComponent(String(v.price ?? ''))}#applications`;
    const inquireHref = `contact.html?vehicle=${encodeURIComponent(vehicleLabel)}&vin=${encodeURIComponent(v.vin || '')}#appointment`;

    const mpgDisplay = v.mpgCity && v.mpgHighway
      ? `<p class="text-muted small mb-2">⛽ ${v.mpgCity}/${v.mpgHighway} MPG${v.fuelType ? ' · ' + v.fuelType : ''}</p>`
      : (v.fuelType ? `<p class="text-muted small mb-2">${v.fuelType}</p>` : '');

    const stockDisplay = v.stockNumber
      ? `<span class="badge bg-secondary mb-2">Stock #${v.stockNumber}</span> `
      : '';

    return `
      <div class="col-md-6 col-lg-4" data-type="${v.type}" data-price="${priceRange}" data-vehicle-id="${this.vehicleId(v)}">
        <article class="card shadow-soft h-100 inventory-card">
          <div class="inventory-img-wrap">
            ${v.badge ? `<span class="inventory-badge ${badgeClass}">${v.badge}</span>` : ''}
            ${mainImage ? `
              <a href="${this.buildVDPUrl(v)}" aria-label="View ${v.year} ${v.make} ${v.model} details">
                <img src="assets/vehicles/${mainImage}"
                     alt="${v.year} ${v.make} ${v.model}"
                     class="card-img-top"
                     style="height:220px; object-fit:cover;"
                     loading="lazy">
              </a>
            ` : `
              <div class="inventory-placeholder d-flex align-items-center justify-content-center bg-light" style="height:220px;">
                <svg width="64" height="64" fill="var(--brand-text-muted)" viewBox="0 0 16 16" aria-hidden="true">
                  <rect x="1" y="3" width="15" height="13" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
                  <circle cx="5.5" cy="14.5" r="1.5" fill="currentColor"/>
                  <circle cx="12.5" cy="14.5" r="1.5" fill="currentColor"/>
                </svg>
              </div>
            `}
          </div>
          <div class="card-body d-flex flex-column">
            <div class="d-flex justify-content-between align-items-start mb-1">
              <h3 class="h6 fw-bold mb-0"><a href="${this.buildVDPUrl(v)}" class="text-dark text-decoration-none">${v.year} ${v.make} ${v.model}${v.trim ? ' ' + v.trim : ''}</a></h3>
              <span class="badge bg-danger ms-2 flex-shrink-0">$${Number(v.price).toLocaleString()}</span>
            </div>
            <p class="text-muted small mb-2">${v.description || ''}</p>
            ${v.mileage ? `<p class="text-muted small mb-2"><strong>${Number(v.mileage).toLocaleString()} miles</strong></p>` : ''}
            ${mpgDisplay}
            ${stockDisplay}
            ${features.length > 0 ? `
            <div class="d-flex flex-wrap gap-1 mb-3">
              ${features.slice(0, 3).map(f => `<span class="badge bg-light text-dark border">${f}</span>`).join('')}
            </div>
            ` : ''}
            <div class="d-grid gap-2 mt-auto">
              <a href="${this.buildVDPUrl(v)}" class="btn btn-sm btn-outline-danger w-100">View Details</a>
              <a href="${applyHref}" class="btn btn-sm btn-danger w-100">Apply for This Vehicle</a>
              <a href="${inquireHref}" class="btn btn-sm btn-outline-dark w-100">Inquire About This Vehicle</a>
            </div>
          </div>
        </article>
      </div>
    `;
  }

  // Get price range category
  getPriceRange(price) {
    if (price < 10000) return 'under10';
    if (price < 20000) return '10to20';
    if (price < 30000) return '20to30';
    return 'over30';
  }

  // Get badge CSS class
  getBadgeClass(badge) {
    if (!badge) return '';
    if (badge === 'Diesel') return 'bg-warning text-dark';
    if (badge === 'Low Miles') return 'bg-success';
    return 'bg-danger';
  }

  // Show error message
  showError() {
    if (!this.grid) return;
    this.grid.innerHTML = `
      <div class="col-12 text-center py-5">
        <p class="text-danger">Unable to load inventory. Please try again later.</p>
      </div>
    `;
  }

  // Filter vehicles (called by search/filter UI — operates on all vehicles, not just available)
  filterVehicles(searchQuery, type, priceRange) {
    const filtered = this.vehicles.filter(v => {
      const searchMatch = !searchQuery ||
        `${v.year} ${v.make} ${v.model} ${v.trim || ''} ${v.description || ''}`.toLowerCase()
          .includes(searchQuery.toLowerCase());

      const typeMatch = type === 'all' || v.type === type;

      const vehiclePriceRange = this.getPriceRange(v.price);
      const priceMatch = priceRange === 'all' || vehiclePriceRange === priceRange;

      const statusMatch = v.status === 'available' || !v.status;

      return searchMatch && typeMatch && priceMatch && statusMatch;
    });

    this.renderVehicles(filtered);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
  // Only run if an inventory grid exists on this page
  const grid = document.getElementById('inventoryGrid');
  if (!grid) return;

  const loader = new InventoryLoader();
  loader.loadInventory();

  // Set up filter functionality
  const searchInput = document.getElementById('searchVehicle');
  const filterType  = document.getElementById('filterType');
  const filterPrice = document.getElementById('filterPrice');
  const searchBtn   = document.getElementById('searchBtn');

  function applyFilters() {
    const query = searchInput ? searchInput.value.trim() : '';
    const type  = filterType  ? filterType.value  : 'all';
    const price = filterPrice ? filterPrice.value : 'all';
    loader.filterVehicles(query, type, price);
  }

  if (searchBtn)   searchBtn.addEventListener('click', applyFilters);
  if (searchInput) searchInput.addEventListener('keyup', function (e) {
    if (e.key === 'Enter') applyFilters();
  });
  if (filterType)  filterType.addEventListener('change', applyFilters);
  if (filterPrice) filterPrice.addEventListener('change', applyFilters);

  // Auto-fill financing form fields from URL params (used by "Apply for This Vehicle" links)
  const params = new URLSearchParams(window.location.search);
  const vehicleParam = params.get('vehicle');
  const vinParam     = params.get('vin');
  const priceParam   = params.get('price');

  if (vehicleParam) {
    const vehicleField = document.getElementById('vehicleInterest') || document.getElementById('vehicle');
    if (vehicleField) vehicleField.value = vehicleParam;
  }
  if (vinParam) {
    const vinField = document.getElementById('vinInterest') || document.getElementById('vin_interest');
    if (vinField) vinField.value = vinParam;
  }
  if (priceParam) {
    const priceField = document.getElementById('vehiclePrice');
    if (priceField) priceField.value = priceParam;
  }

  // Auto-scroll to form anchor if present
  if (window.location.hash === '#applications') {
    const target = document.getElementById('applications');
    if (target) setTimeout(() => target.scrollIntoView({ behavior: 'smooth' }), 300);
  }
});

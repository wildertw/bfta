// vehicle-manager.js
// Handles VIN decoding, form management, live preview, and inventory export.
// Used exclusively by admin.html.

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  loadInventoryTable();
  setupFormHandlers();
  setupImagePreview();
  setupLivePreview();
  setupVinUppercase();
});

// ─── VIN Decoder ─────────────────────────────────────────────────────────────
document.getElementById('decodeBtn').addEventListener('click', async function () {
  const vinInput = document.getElementById('vin');
  const vin      = vinInput.value.trim().toUpperCase();
  const btn      = this;
  const spinner  = document.getElementById('decodeSpinner');

  // Validate
  if (vin.length !== 17) {
    vinInput.classList.add('is-invalid');
    const err = document.getElementById('vinError');
    if (err) err.textContent = 'VIN must be exactly 17 characters.';
    return;
  }
  vinInput.classList.remove('is-invalid');
  const err = document.getElementById('vinError');
  if (err) err.textContent = '';

  // Loading state
  btn.disabled = true;
  if (spinner) spinner.classList.remove('d-none');
  btn.querySelector('.btn-label') && (btn.querySelector('.btn-label').textContent = 'Decoding…');

  try {
    const response = await fetch(
      `https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/${vin}?format=json`
    );
    if (!response.ok) throw new Error('Network error reaching VIN database.');

    const data = await response.json();
    if (!data.Results) throw new Error('Invalid response from VIN database.');

    const results = data.Results;

    // Helper
    const get = (name) => {
      const item = results.find(r => r.Variable === name);
      return item && item.Value && item.Value !== 'Not Applicable' ? item.Value : '';
    };

    const year         = get('Model Year');
    const make         = get('Make');
    const model        = get('Model');
    const trim         = get('Trim') || get('Trim2');
    const displacement = get('Displacement (L)');
    const cylinders    = get('Engine Number of Cylinders');
    const engineModel  = get('Engine Model');
    const transmission = get('Transmission Style');
    const driveType    = get('Drive Type');
    const bodyClass    = get('Body Class');
    const fuelType     = get('Fuel Type - Primary');
    const doors        = get('Doors');

    // Populate basic fields
    document.getElementById('year').value  = year;
    document.getElementById('make').value  = make;
    document.getElementById('model').value = model;
    document.getElementById('trim').value  = trim;

    // Engine string
    const engineStr = displacement && cylinders
      ? `${parseFloat(displacement).toFixed(1)}L ${cylinders}-Cyl`
      : engineModel || '';
    if (document.getElementById('engine')) {
      document.getElementById('engine').value = engineStr;
    }

    // Transmission
    if (document.getElementById('transmission')) {
      document.getElementById('transmission').value = transmission;
    }

    // Fuel type dropdown
    const fuelSelect = document.getElementById('fuelType');
    if (fuelSelect && fuelType) {
      const fuelMap = {
        'Gasoline': 'Gasoline',
        'Diesel':   'Diesel',
        'Electric': 'Electric',
        'Flexible Fuel Vehicle': 'Flex Fuel',
        'Hybrid':   'Hybrid'
      };
      const mapped = fuelMap[fuelType] || '';
      if (mapped) fuelSelect.value = mapped;
    }

    // Drivetrain dropdown
    const driveSelect = document.getElementById('drivetrain');
    if (driveSelect && driveType) {
      const driveMap = {
        'Four-Wheel Drive':          '4WD',
        '4WD/4-Wheel Drive/4x4':     '4WD',
        'All-Wheel Drive':           'AWD',
        'AWD/All-Wheel Drive':       'AWD',
        'Front-Wheel Drive':         'FWD',
        'FWD/Front-Wheel Drive':     'FWD',
        'Rear-Wheel Drive':          'RWD',
        'RWD/Rear-Wheel Drive':      'RWD'
      };
      const mapped = driveMap[driveType] || '';
      if (mapped) driveSelect.value = mapped;
    }

    // Vehicle type
    const typeSelect = document.getElementById('type');
    if (typeSelect) {
      const bl = bodyClass.toLowerCase();
      if      (bl.includes('truck') || bl.includes('pickup'))              typeSelect.value = 'truck';
      else if (bl.includes('suv') || bl.includes('sport utility'))         typeSelect.value = 'suv';
      else if (bl.includes('sedan') || bl.includes('coupe') || bl.includes('hatchback')) typeSelect.value = 'car';
      else if (bl.includes('van'))                                         typeSelect.value = 'van';

      if (fuelType && fuelType.toLowerCase().includes('diesel')) {
        typeSelect.value = 'diesel';
      }
    }

    // Auto-generate description only if blank
    const descField = document.getElementById('description');
    if (descField && !descField.value.trim()) {
      const parts = [];
      if (driveType)  parts.push(driveType);
      if (engineStr)  parts.push(engineStr);
      if (doors)      parts.push(`${doors} doors`);
      descField.value = parts.join(', ');
    }

    // Show decoded summary panel
    const panel = document.getElementById('decodedData');
    if (panel) {
      panel.classList.remove('d-none');
      const setField = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val || '–'; };
      setField('decodedYear',  year);
      setField('decodedMake',  make);
      setField('decodedModel', model);
      setField('decodedTrim',  trim);
      setField('decodedBody',  bodyClass);
      setField('decodedDrive', driveType);
      setField('decodedFuel',  fuelType);
    }

    updateLivePreview();

  } catch (error) {
    console.error('VIN Decode Error:', error);
    alert(`Could not decode VIN: ${error.message}\n\nPlease verify the VIN or enter details manually.`);
  } finally {
    btn.disabled = false;
    if (spinner) spinner.classList.add('d-none');
    const label = btn.querySelector('.btn-label');
    if (label) label.textContent = 'Decode VIN';
  }
});

// ─── Utility: Normalize ALL-CAPS text (e.g. NHTSA VIN API returns CHEVROLET) ──
function toTitleCase(str) {
  if (!str) return str;
  return str.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

// ─── Form Submission ──────────────────────────────────────────────────────────
function setupFormHandlers() {
  document.getElementById('vehicleForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const g = (id) => { const el = document.getElementById(id); return el ? el.value.trim() : ''; };

    const vehicle = {
      vin:          g('vin').toUpperCase(),
      stockNumber:  g('stockNumber'),
      year:         parseInt(g('year'), 10),
      make:         toTitleCase(g('make')),
      model:        g('model'),
      trim:         g('trim'),
      engine:       g('engine'),
      transmission: g('transmission'),
      drivetrain:   g('drivetrain'),
      fuelType:     g('fuelType'),
      mpgCity:      g('mpgCity')      ? parseInt(g('mpgCity'), 10)      : null,
      mpgHighway:   g('mpgHighway')   ? parseInt(g('mpgHighway'), 10)   : null,
      mileage:      parseInt(g('mileage'), 10),
      price:        parseInt(g('price'), 10),
      type:         g('type'),
      exteriorColor: g('exteriorColor'),
      interiorColor: g('interiorColor'),
      description:  g('description'),
      features:     g('features').split(',').map(f => f.trim()).filter(Boolean),
      status:       g('status') || 'available',
      badge:        g('badge'),
      images:       [],
      dateAdded:    new Date().toISOString()
    };

    // Auto-description if still empty
    if (!vehicle.description) {
      const parts = [];
      if (vehicle.drivetrain) parts.push(vehicle.drivetrain);
      if (vehicle.engine)     parts.push(vehicle.engine);
      if (vehicle.mileage)    parts.push(`${vehicle.mileage.toLocaleString()} miles`);
      vehicle.description = parts.join(', ');
    }

    saveVehicle(vehicle);

    const mpgInfo   = vehicle.mpgCity && vehicle.mpgHighway ? `\nMPG: ${vehicle.mpgCity} city / ${vehicle.mpgHighway} hwy` : '';
    const stockInfo = vehicle.stockNumber ? `\nStock #: ${vehicle.stockNumber}` : '';
    alert(`✓ Vehicle added!\n\n${vehicle.year} ${vehicle.make} ${vehicle.model}\nVIN: ${vehicle.vin}${stockInfo}${mpgInfo}\n\nInventory JSON has been downloaded.\n\nNEXT STEPS:\n1. Upload inventory.json to your server\n2. Run: python3 generate_vdp_pages.py\n3. Upload the new vdp/ folder to your server`);

    resetForm();
    loadInventoryTable();
  });
}

// ─── Storage & Export ─────────────────────────────────────────────────────────
function saveVehicle(vehicle) {
  let inventory;
  try {
    inventory = JSON.parse(localStorage.getItem('bellsfork_inventory') || '{"vehicles":[]}');
  } catch {
    inventory = { vehicles: [] };
  }
  inventory.vehicles.push(vehicle);
  inventory.lastUpdated = new Date().toISOString();
  localStorage.setItem('bellsfork_inventory', JSON.stringify(inventory));
  downloadInventoryJSON(inventory);
}

function downloadInventoryJSON(inventory) {
  const dataStr  = JSON.stringify(inventory, null, 2);
  const dataUri  = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
  const link     = document.createElement('a');
  link.setAttribute('href', dataUri);
  link.setAttribute('download', 'inventory.json');
  link.click();
}

// ─── Inventory Table ──────────────────────────────────────────────────────────
function loadInventoryTable() {
  const tbody = document.getElementById('inventoryTableBody');
  if (!tbody) return;

  let inventory;
  try {
    inventory = JSON.parse(localStorage.getItem('bellsfork_inventory') || '{"vehicles":[]}');
  } catch {
    inventory = { vehicles: [] };
  }

  if (!inventory.vehicles || inventory.vehicles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No vehicles in inventory. Add your first vehicle above.</td></tr>';
    return;
  }

  tbody.innerHTML = inventory.vehicles.map((v, idx) => `
    <tr>
      <td>
        <div style="width:80px;height:60px;background:#e9ecef;border-radius:4px;display:flex;align-items:center;justify-content:center;">
          <svg width="32" height="32" fill="#6c757d" viewBox="0 0 16 16" aria-hidden="true">
            <rect x="1" y="3" width="15" height="13" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
            <circle cx="5.5" cy="14.5" r="1.5" fill="none" stroke="currentColor"/>
            <circle cx="12.5" cy="14.5" r="1.5" fill="none" stroke="currentColor"/>
          </svg>
        </div>
      </td>
      <td>
        <strong>${v.year} ${v.make} ${v.model}</strong><br>
        <small class="text-muted">${v.trim || ''}</small>
        ${v.stockNumber ? `<br><span class="badge bg-secondary mt-1">Stock #${v.stockNumber}</span>` : ''}
      </td>
      <td><small class="font-monospace">${v.vin || '—'}</small></td>
      <td>
        ${v.mileage ? Number(v.mileage).toLocaleString() + ' mi' : '—'}
        ${v.mpgCity && v.mpgHighway ? `<br><small class="text-muted">${v.mpgCity}/${v.mpgHighway} MPG</small>` : ''}
      </td>
      <td class="fw-bold text-success">${v.price ? '$' + Number(v.price).toLocaleString() : '—'}</td>
      <td><span class="badge bg-${v.status === 'available' ? 'success' : 'secondary'}">${(v.status || 'available').toUpperCase()}</span></td>
      <td>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteVehicle(${idx})" aria-label="Delete vehicle">
          <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
            <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
          </svg>
        </button>
      </td>
    </tr>
  `).join('');
}

function deleteVehicle(idx) {
  if (!confirm('Delete this vehicle from local inventory?')) return;
  let inventory;
  try {
    inventory = JSON.parse(localStorage.getItem('bellsfork_inventory') || '{"vehicles":[]}');
  } catch {
    inventory = { vehicles: [] };
  }
  inventory.vehicles.splice(idx, 1);
  inventory.lastUpdated = new Date().toISOString();
  localStorage.setItem('bellsfork_inventory', JSON.stringify(inventory));
  loadInventoryTable();
}

// ─── Reset ────────────────────────────────────────────────────────────────────
function resetForm() {
  document.getElementById('vehicleForm').reset();
  const panel = document.getElementById('decodedData');
  if (panel) panel.classList.add('d-none');
  const preview = document.getElementById('imagePreview');
  if (preview) preview.innerHTML = '';
  updateLivePreview();
}

// ─── Image Preview ────────────────────────────────────────────────────────────
function setupImagePreview() {
  const photosInput = document.getElementById('photos');
  if (!photosInput) return;

  photosInput.addEventListener('change', function (e) {
    const preview = document.getElementById('imagePreview');
    if (!preview) return;
    preview.innerHTML = '';

    const files = Array.from(e.target.files);
    if (files.length > 10) {
      alert('Maximum 10 images allowed.');
      e.target.value = '';
      return;
    }

    files.forEach((file, index) => {
      const reader = new FileReader();
      reader.onload = function (ev) {
        const img = document.createElement('img');
        img.src   = ev.target.result;
        img.alt   = `Vehicle photo ${index + 1}`;
        img.title = index === 0 ? 'Main image' : `Photo ${index + 1}`;
        img.style.cssText = 'width:100px;height:100px;object-fit:cover;border-radius:4px;border:2px solid #dee2e6;cursor:pointer;';
        img.addEventListener('click', () => img.remove());
        preview.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
  });
}

// ─── Live Preview ─────────────────────────────────────────────────────────────
function setupLivePreview() {
  const watchIds = ['year','make','model','trim','price','mileage','type','badge','mpgCity','mpgHighway','fuelType','stockNumber','description'];
  watchIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input',  updateLivePreview);
      el.addEventListener('change', updateLivePreview);
    }
  });
}

function updateLivePreview() {
  const preview = document.getElementById('livePreview') || document.getElementById('preview');
  if (!preview) return;

  const year    = document.getElementById('year')?.value     || '';
  const make    = document.getElementById('make')?.value     || '';
  const model   = document.getElementById('model')?.value    || '';
  const trim    = document.getElementById('trim')?.value     || '';
  const price   = document.getElementById('price')?.value    || '';
  const mileage = document.getElementById('mileage')?.value  || '';
  const badge   = document.getElementById('badge')?.value    || '';
  const mpgCity = document.getElementById('mpgCity')?.value  || '';
  const mpgHwy  = document.getElementById('mpgHighway')?.value || '';
  const fuel    = document.getElementById('fuelType')?.value || '';
  const stock   = document.getElementById('stockNumber')?.value || '';
  const desc    = document.getElementById('description')?.value || '';

  if (!year || !make || !model) {
    preview.innerHTML = '<div class="text-center text-muted py-5"><small>Fill in Year, Make, and Model to see a live preview.</small></div>';
    return;
  }

  const badgeColor = badge === 'Diesel' ? 'warning text-dark' : badge === 'Low Miles' ? 'success' : 'danger';

  preview.innerHTML = `
    <article class="card shadow-sm h-100">
      <div style="position:relative;height:180px;background:#e9ecef;display:flex;align-items:center;justify-content:center;">
        ${badge ? `<span class="badge bg-${badgeColor}" style="position:absolute;top:.5rem;left:.5rem;">${badge}</span>` : ''}
        <svg width="48" height="48" fill="#adb5bd" viewBox="0 0 16 16" aria-hidden="true">
          <rect x="1" y="3" width="15" height="13" rx="1" fill="none" stroke="currentColor" stroke-width="1"/>
          <circle cx="5.5" cy="14.5" r="1.5" fill="none" stroke="currentColor"/>
          <circle cx="12.5" cy="14.5" r="1.5" fill="none" stroke="currentColor"/>
        </svg>
      </div>
      <div class="card-body">
        ${stock ? `<span class="badge bg-secondary mb-2">Stock #${stock}</span>` : ''}
        <div class="d-flex justify-content-between align-items-start mb-2">
          <h6 class="fw-bold mb-0">${year} ${make} ${model}${trim ? ' ' + trim : ''}</h6>
          ${price ? `<span class="badge bg-danger ms-1">$${parseInt(price).toLocaleString()}</span>` : ''}
        </div>
        ${desc ? `<p class="text-muted small mb-2">${desc}</p>` : ''}
        <p class="text-muted small mb-2">
          ${mileage ? `<strong>${parseInt(mileage).toLocaleString()} miles</strong>` : ''}
          ${fuel ? ` · ${fuel}` : ''}
          ${mpgCity && mpgHwy ? ` · ${mpgCity}/${mpgHwy} MPG` : ''}
        </p>
        <a href="#" class="btn btn-sm btn-outline-dark w-100" onclick="return false;">Inquire About This Vehicle</a>
      </div>
    </article>
  `;
}

// ─── VIN Uppercase ────────────────────────────────────────────────────────────
function setupVinUppercase() {
  const vinInput = document.getElementById('vin');
  if (vinInput) {
    vinInput.addEventListener('input', function () {
      const pos = this.selectionStart;
      this.value = this.value.toUpperCase();
      this.setSelectionRange(pos, pos);
    });
    vinInput.addEventListener('keypress', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('decodeBtn')?.click();
      }
    });
  }
}

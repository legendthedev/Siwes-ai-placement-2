/**
 * main.js — SIWES Placement Portal
 * Alpine.js components + HTMX helpers + utilities
 */

/* ── Geolocation → State detector ───────────────────────────────────────── */
const STATE_COORDS = {
  Lagos:   { lat: 6.5244,  lng: 3.3792,  label: "Lagos" },
  Abuja:   { lat: 9.0765,  lng: 7.3986,  label: "Abuja (FCT)" },
  Ibadan:  { lat: 7.3775,  lng: 3.9470,  label: "Ibadan, Oyo" },
  Calabar: { lat: 4.9517,  lng: 8.3220,  label: "Calabar, Cross River" },
  Kwara:   { lat: 8.4966,  lng: 4.5426,  label: "Ilorin, Kwara" },
};

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function detectNearestState(lat, lng) {
  let best = null, bestDist = Infinity;
  for (const [key, data] of Object.entries(STATE_COORDS)) {
    const d = haversine(lat, lng, data.lat, data.lng);
    if (d < bestDist) { bestDist = d; best = key; }
  }
  return best;
}

window.geoDetect = function (onDetected, onError) {
  if (!navigator.geolocation) { onError("Geolocation not supported"); return; }
  navigator.geolocation.getCurrentPosition(
    pos => onDetected(detectNearestState(pos.coords.latitude, pos.coords.longitude)),
    err => onError(err.message),
    { timeout: 8000, maximumAge: 60000 }
  );
};

/* ── Alpine.js: location cascade (state → suburb) ───────────────────────── */
document.addEventListener('alpine:init', () => {

  /* Auth geo widget */
  Alpine.data('geoWidget', () => ({
    status: 'idle',     // idle | detecting | found | error
    stateLabel: '',
    init() {
      // auto-detect on mount (non-blocking)
      this.detect();
    },
    detect() {
      this.status = 'detecting';
      window.geoDetect(
        state => {
          this.status    = 'found';
          this.stateLabel = STATE_COORDS[state]?.label || state;
          // Pre-fill the state select if it exists on the same page
          const sel = document.getElementById('state-select');
          if (sel) {
            sel.value = state;
            sel.dispatchEvent(new Event('change'));
          }
        },
        () => { this.status = 'error'; }
      );
    },
  }));

  /* Cascading state→location selector */
  Alpine.data('locationCascade', (initialState = '', initialLocation = '') => ({
    state: initialState,
    location: initialLocation,
    locations: [],
    init() {
      if (this.state) this.loadLocations(this.state);
    },
    async loadLocations(state) {
      if (!state) { this.locations = []; return; }
      const res  = await fetch(`/api/locations/${state}`);
      const html = await res.text();
      // Parse option values from HTML string
      const tmp  = document.createElement('select');
      tmp.innerHTML = html;
      this.locations = [...tmp.options].map(o => ({ value: o.value, label: o.text }));
    },
    onStateChange() {
      this.location = '';
      this.loadLocations(this.state);
    },
  }));

  /* Skill tag input (comma-separated → removable chips) */
  Alpine.data('skillInput', (initial = '') => ({
    raw: '',
    tags: initial ? initial.split(',').map(s => s.trim()).filter(Boolean) : [],
    suggestions: [],
    allSkills: [
      'python','javascript','typescript','java','go','rust','c++','c#','php','kotlin','swift','r','scala',
      'react','vue','angular','nextjs','nodejs','express','django','flask','fastapi','spring boot','laravel',
      'postgresql','mysql','mongodb','sqlite','redis','firebase','oracle','cassandra','sql server',
      'docker','kubernetes','aws','gcp','azure','linux','git','ci/cd','terraform','nginx','bash',
      'machine learning','deep learning','tensorflow','pytorch','scikit-learn','pandas','numpy',
      'natural language processing','data analysis','tableau','power bi','excel',
      'android','ios','flutter','react native','dart','kotlin',
      'networking','cybersecurity','penetration testing','ethical hacking','cisco','wireshark',
      'rest api','graphql','microservices','agile','scrum','object oriented programming',
      'data structures','algorithms','system design','technical writing','figma','ui/ux design',
    ],
    addFromInput() {
      const parts = this.raw.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
      parts.forEach(p => { if (!this.tags.includes(p)) this.tags.push(p); });
      this.raw = ''; this.suggestions = [];
      this.syncHidden();
    },
    addTag(tag) {
      if (!this.tags.includes(tag)) this.tags.push(tag);
      this.raw = ''; this.suggestions = [];
      this.syncHidden();
    },
    removeTag(i) { this.tags.splice(i, 1); this.syncHidden(); },
    onInput() {
      const q = this.raw.toLowerCase().trim();
      this.suggestions = q.length > 1
        ? this.allSkills.filter(s => s.includes(q) && !this.tags.includes(s)).slice(0, 8)
        : [];
    },
    syncHidden() {
      const h = document.getElementById('skills-hidden');
      if (h) h.value = this.tags.join(', ');
    },
    get hidden() { return this.tags.join(', '); },
  }));

  /* Password strength */
  Alpine.data('passwordStrength', () => ({
    password: '',
    get strength() {
      let s = 0;
      if (this.password.length >= 8) s++;
      if (/[A-Z]/.test(this.password)) s++;
      if (/[0-9]/.test(this.password)) s++;
      if (/[^A-Za-z0-9]/.test(this.password)) s++;
      return s;
    },
    get label() {
      return ['', 'Weak', 'Fair', 'Good', 'Strong'][this.strength] || '';
    },
  }));

  /* Quota stepper */
  Alpine.data('quotaStepper', (initial = 1) => ({
    value: initial,
    inc() { if (this.value < 20) this.value++; this.sync(); },
    dec() { if (this.value > 1)  this.value--; this.sync(); },
    sync() {
      const h = document.getElementById('quota-hidden');
      if (h) h.value = this.value;
    },
  }));

  /* Preliminary test timer + navigator */
  Alpine.data('testEngine', (totalQuestions = 0, timeLimitMins = 20) => ({
    current:   0,
    answered:  {},
    timeLeft:  timeLimitMins * 60,
    timer:     null,
    init() {
      this.timer = setInterval(() => {
        if (this.timeLeft > 0) { this.timeLeft--; }
        else { clearInterval(this.timer); this.submit(); }
      }, 1000);
    },
    get minutes()  { return String(Math.floor(this.timeLeft / 60)).padStart(2,'0'); },
    get seconds()  { return String(this.timeLeft % 60).padStart(2,'0'); },
    get isWarning(){ return this.timeLeft < 180; },
    get progress() { return Object.keys(this.answered).length / totalQuestions * 100; },
    go(i)  { this.current = i; },
    answer(qIndex, val) { this.answered[qIndex] = val; },
    isAnswered(i) { return i in this.answered; },
    submit() {
      clearInterval(this.timer);
      const unanswered = totalQuestions - Object.keys(this.answered).length;
      if (unanswered > 0) {
        if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
      }
      document.getElementById('test-form').submit();
    },
    destroy() { clearInterval(this.timer); },
  }));

  /* Admin dashboard search */
  Alpine.data('tableSearch', () => ({
    query: '',
    filter(rows) {
      if (!this.query) return rows;
      const q = this.query.toLowerCase();
      return rows.filter(r => JSON.stringify(r).toLowerCase().includes(q));
    },
  }));

  /* Notification toaster (for HTMX responses) */
  Alpine.data('toaster', () => ({
    messages: [],
    add(msg, type = 'info') {
      const id = Date.now();
      this.messages.push({ id, msg, type });
      setTimeout(() => this.remove(id), 5000);
    },
    remove(id) { this.messages = this.messages.filter(m => m.id !== id); },
  }));
});

/* ── HTMX event listeners ────────────────────────────────────────────────── */
document.addEventListener('htmx:afterSwap', () => {
  // re-init Alpine on HTMX-swapped content
  if (window.Alpine) Alpine.initTree(document.body);
});

/* ── Upload zone drag & drop (non-Alpine) ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.upload-zone').forEach(zone => {
    const input = zone.querySelector('input[type=file]');
    const label = zone.querySelector('.filename');

    zone.addEventListener('click', () => input?.click());
    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('drag-over');
      if (e.dataTransfer.files[0] && input) {
        input.files = e.dataTransfer.files;
        if (label) label.textContent = e.dataTransfer.files[0].name;
      }
    });
    input?.addEventListener('change', () => {
      if (label && input.files[0]) label.textContent = input.files[0].name;
    });
  });

  /* Score bar animation on result page */
  document.querySelectorAll('.shap-bar[data-width]').forEach(bar => {
    requestAnimationFrame(() => { bar.style.width = bar.dataset.width; });
  });
});

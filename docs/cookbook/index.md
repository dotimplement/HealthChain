# Cookbook

Hands-on, production-ready examples for building healthcare AI applications with HealthChain.

<div class="tag-legend">
  <span class="tag-legend-title">Filter:</span>
  <span class="tag tag-filter tag-healthtech" data-tag="healthtech">HealthTech</span>
  <span class="tag tag-filter tag-genai" data-tag="genai">GenAI</span>
  <span class="tag tag-filter tag-ml" data-tag="ml">ML Research</span>
  <span class="tag tag-filter tag-gateway" data-tag="gateway">Gateway</span>
  <span class="tag tag-filter tag-pipeline" data-tag="pipeline">Pipeline</span>
  <span class="tag tag-filter tag-interop" data-tag="interop">Interop</span>
  <span class="tag tag-filter tag-fhir" data-tag="fhir">FHIR</span>
  <span class="tag tag-filter tag-cdshooks" data-tag="cdshooks">CDS Hooks</span>
  <span class="tag tag-filter tag-sandbox" data-tag="sandbox">Sandbox</span>
  <span class="tag-clear hidden" id="clearFilters">Clear</span>
</div>

<div class="cookbook-wrapper">
<div class="cookbook-grid" id="cookbookGrid">

<a href="setup_fhir_sandboxes/" class="cookbook-card" data-tags="fhir sandbox">
  <div class="cookbook-card-icon">🚦</div>
  <div class="cookbook-card-title">Working with FHIR Sandboxes</div>
  <div class="cookbook-card-description">
    Spin up and access free Epic, Medplum, and other FHIR sandboxes for safe experimentation. Recommended first step before the other tutorials.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-fhir">FHIR</span>
    <span class="tag tag-sandbox">Sandbox</span>
  </div>
</a>

<a href="ml_model_deployment/" class="cookbook-card" data-tags="ml gateway cdshooks">
  <div class="cookbook-card-icon">🔬</div>
  <div class="cookbook-card-title">Deploy ML Models: Real-Time Alerts & Batch Screening</div>
  <div class="cookbook-card-description">
    Deploy the same ML model two ways: CDS Hooks for point-of-care sepsis alerts, and FHIR Gateway for population-level batch screening with RiskAssessment resources.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-ml">ML Research</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-cdshooks">CDS Hooks</span>
  </div>
</a>

<a href="multi_ehr_aggregation/" class="cookbook-card" data-tags="genai gateway fhir">
  <div class="cookbook-card-icon">🔗</div>
  <div class="cookbook-card-title">Multi-Source Patient Data Aggregation</div>
  <div class="cookbook-card-description">
    Merge patient data from multiple FHIR sources (Epic, Cerner, etc.), deduplicate conditions, prove provenance, and handle cross-vendor errors. Foundation for RAG and analytics workflows.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-genai">GenAI</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-fhir">FHIR</span>
  </div>
</a>

<a href="clinical_coding/" class="cookbook-card" data-tags="healthtech pipeline interop">
  <div class="cookbook-card-icon">🧾</div>
  <div class="cookbook-card-title">Automate Clinical Coding & FHIR Integration</div>
  <div class="cookbook-card-description">
    Extract medical conditions from clinical documentation using AI, map to SNOMED CT codes, and sync as FHIR Condition resources for billing, analytics, and interoperability.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-healthtech">HealthTech</span>
    <span class="tag tag-pipeline">Pipeline</span>
    <span class="tag tag-interop">Interop</span>
  </div>
</a>

<a href="discharge_summarizer/" class="cookbook-card" data-tags="healthtech gateway cdshooks">
  <div class="cookbook-card-icon">📝</div>
  <div class="cookbook-card-title">Summarize Discharge Notes with CDS Hooks</div>
  <div class="cookbook-card-description">
    Deploy a CDS Hooks-compliant service that listens for discharge events, auto-generates concise plain-language summaries, and delivers actionable clinical cards directly into the EHR workflow.
  </div>
  <div class="cookbook-tags">
    <span class="tag tag-healthtech">HealthTech</span>
    <span class="tag tag-gateway">Gateway</span>
    <span class="tag tag-cdshooks">CDS Hooks</span>
  </div>
</a>

<div class="no-results hidden" id="noResults">
  No cookbooks match the selected filters. <a href="#" onclick="clearAllFilters(); return false;">Clear filters</a>
</div>

</div>
</div>

<script>
(function() {
  const activeFilters = new Set();
  const filterTags = document.querySelectorAll('.tag-filter');
  const cards = document.querySelectorAll('.cookbook-card');
  const clearBtn = document.getElementById('clearFilters');
  const noResults = document.getElementById('noResults');

  function updateCards() {
    let visibleCount = 0;

    cards.forEach(card => {
      const cardTags = card.dataset.tags.split(' ');
      const matches = activeFilters.size === 0 ||
        [...activeFilters].some(filter => cardTags.includes(filter));

      if (matches) {
        card.classList.remove('filtered-out');
        card.classList.add('filtered-in');
        visibleCount++;
      } else {
        card.classList.add('filtered-out');
        card.classList.remove('filtered-in');
      }
    });

    // Show/hide no results message
    if (visibleCount === 0 && activeFilters.size > 0) {
      noResults.classList.remove('hidden');
    } else {
      noResults.classList.add('hidden');
    }

    // Show/hide clear button
    if (activeFilters.size > 0) {
      clearBtn.classList.remove('hidden');
    } else {
      clearBtn.classList.add('hidden');
    }
  }

  filterTags.forEach(tag => {
    tag.addEventListener('click', () => {
      const filterValue = tag.dataset.tag;

      if (activeFilters.has(filterValue)) {
        activeFilters.delete(filterValue);
        tag.classList.remove('active');
      } else {
        activeFilters.add(filterValue);
        tag.classList.add('active');
      }

      updateCards();
    });
  });

  function clearAllFilters() {
    activeFilters.clear();
    filterTags.forEach(tag => tag.classList.remove('active'));
    updateCards();
  }

  clearBtn.addEventListener('click', clearAllFilters);
  window.clearAllFilters = clearAllFilters;
})();
</script>

---

!!! tip "What next?"
    See the source code for each recipe, experiment with the sandboxes, and adapt the patterns for your projects!

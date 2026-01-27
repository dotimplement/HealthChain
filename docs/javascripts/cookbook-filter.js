/**
 * Cookbook Filter - Tag-based filtering for cookbook cards
 * Compatible with MkDocs Material's instant loading feature
 */
function initCookbookFilter() {
  const filterTags = document.querySelectorAll('.tag-filter');
  const cards = document.querySelectorAll('.cookbook-card');
  const clearBtn = document.getElementById('clearFilters');
  const noResults = document.getElementById('noResults');

  // Exit early if elements don't exist (not on cookbook page)
  if (!filterTags.length || !cards.length) {
    return;
  }

  // Prevent duplicate initialization by checking for marker
  if (filterTags[0].dataset.initialized === 'true') {
    return;
  }
  filterTags[0].dataset.initialized = 'true';

  const activeFilters = new Set();

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
    if (noResults) {
      if (visibleCount === 0 && activeFilters.size > 0) {
        noResults.classList.remove('hidden');
      } else {
        noResults.classList.add('hidden');
      }
    }

    // Show/hide clear button
    if (clearBtn) {
      if (activeFilters.size > 0) {
        clearBtn.classList.remove('hidden');
      } else {
        clearBtn.classList.add('hidden');
      }
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

  if (clearBtn) {
    clearBtn.addEventListener('click', clearAllFilters);
  }

  // Expose globally for inline onclick handlers
  window.clearAllFilters = clearAllFilters;
}

// Run immediately since extra_javascript loads after DOM is ready
initCookbookFilter();

// Also handle MkDocs Material instant navigation if available
// This uses a polling approach to wait for document$ to be defined
(function waitForInstantNav() {
  if (typeof document$ !== 'undefined') {
    document$.subscribe(function() {
      initCookbookFilter();
    });
  } else {
    // Fallback: use location hash change as a proxy for navigation
    window.addEventListener('hashchange', initCookbookFilter);
    // Also try again after a short delay in case document$ loads later
    setTimeout(function() {
      if (typeof document$ !== 'undefined') {
        document$.subscribe(function() {
          initCookbookFilter();
        });
      }
    }, 1000);
  }
})();

const list = document.querySelector('#scheme-list');
const search = document.querySelector('#search');
const category = document.querySelector('#category');

const escapeHtml = value =>
  String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));

const normalizeCategory = value => {
  const normalized = String(value ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
  return normalized === 'seniorcitizen' || normalized === 'seniorcitizens'
    ? 'seniorcitizens'
    : normalized;
};

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`Server error: ${response.status}`);
  }

  return response.json();
}

// Load categories
async function loadCategories() {
  const categories = await fetchJSON('/api/categories');
  if (!category) return;

  category.innerHTML = '<option value="">All categories</option>';

  categories.forEach(name => {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name;
    category.append(option);
  });
}

// Load schemes
let schemeController;
let categoriesReady = Promise.resolve();

async function loadSchemes() {
  if (!list) return;

  if (schemeController) schemeController.abort();
  schemeController = new AbortController();

  const params = new URLSearchParams({
    q: search?.value || '',
    category: category?.value || ''
  });

  try {
    const schemes = await fetchJSON(
      `/api/schemes?${params}`,
      { signal: schemeController.signal }
    );

    const resultCount = document.querySelector('#result-count');
    if (resultCount) {
      resultCount.textContent = `${schemes.length} starting point${schemes.length === 1 ? '' : 's'}`;
    }

    if (!schemes.length) {
      list.innerHTML =
        '<div class="empty-state">No matches found. Try another search or explore all schemes.</div>';
      return;
    }

    list.innerHTML = schemes.map(s => {
      const linkCandidates = Array.isArray(s.official_links) && s.official_links.length
        ? s.official_links
        : (s.official_url ? [{ label: 'Official website', url: s.official_url }] : []);
      const officialLinks = linkCandidates.flatMap(link => {
        try {
          const parsedUrl = new URL(link.url);
          if (parsedUrl.protocol !== 'https:') return [];
          return [{ label: link.label || 'Official website', url: parsedUrl.href }];
        } catch (_) {
          return [];
        }
      });

      return `
        <article class="scheme-item">
          <div class="scheme-item-main">
            <span class="scheme-category">${escapeHtml(s.category)}</span>
            <h4>${escapeHtml(s.name)}</h4>
            <p>${escapeHtml(s.summary)}</p>
            ${s.benefits ? `<p><strong>Benefits:</strong> ${escapeHtml(s.benefits)}</p>` : ''}
            ${s.eligibility ? `<p><strong>Eligibility:</strong> ${escapeHtml(s.eligibility)}</p>` : ''}
            ${s.documents ? `<p><strong>Required documents:</strong> ${escapeHtml(s.documents)}</p>` : ''}
            <small class="unverified-tag">Starter information &mdash; confirm current details</small>
            ${officialLinks.length ? '' : '<small class="scheme-link-note">Official website link is currently unavailable.</small>'}
          </div>
          ${officialLinks.length
            ? `<nav class="official-links" aria-label="Official links for ${escapeHtml(s.name)}">${officialLinks.map(link => `<a class="official-link" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(link.label)} &#8599;</a>`).join('')}</nav>`
            : ''}
        </article>
      `;
    }).join('');

  } catch (error) {
    if (error.name === 'AbortError') return;

    console.error('Scheme loading error:', error);
    list.innerHTML =
      '<div class="empty-state">Unable to load schemes. Please refresh and try again.</div>';
  }
}

// Initialize application
async function initializeApp() {
  try {
    categoriesReady = loadCategories();
    await categoriesReady;
    await loadSchemes();
  } catch (error) {
    console.error('Application initialization error:', error);

    if (list) {
      list.innerHTML =
        '<div class="empty-state">Unable to connect to the server. Please refresh the page.</div>';
    }
  }
}

search?.addEventListener('input', loadSchemes);
category?.addEventListener('change', loadSchemes);

// Quick category filters
document.querySelectorAll('[data-filter]').forEach(link => {
  link.addEventListener('click', async event => {
    event.preventDefault();
    document.querySelector('#finder')?.scrollIntoView({ behavior: 'smooth' });

    try {
      await categoriesReady;
      const requested = normalizeCategory(link.dataset.filter);
      const option = [...(category?.options || [])].find(item =>
        normalizeCategory(item.value) === requested
      );
      if (!option) return;
      category.value = option.value;
      await loadSchemes();
    } catch (error) {
      console.error('Category filter error:', error);
    }
  });
});

// Language translation
const translations = {
  kn: {
    'Explore services': 'à²¸à³‡à²µà³†à²—à²³à³',
    'How it works': 'à²¹à³‡à²—à³† à²•à³†à²²à²¸ à²®à²¾à²¡à³à²¤à³à²¤à²¦à³†',
    'About': 'à²¨à²®à³à²® à²¬à²—à³à²—à³†',
    'Find a scheme': 'à²¯à³‹à²œà²¨à³† à²¹à³à²¡à³à²•à²¿',
    'Government support,': 'à²¸à²°à³à²•à²¾à²°à²¿ à²¨à³†à²°à²µà³,',
    'within reach.': 'à²¨à²¿à²®à³à²® à²•à³ˆà²—à³†à²Ÿà³à²•à³à²µà²‚à²¤à³†.',
    'Explore schemes': 'à²¯à³‹à²œà²¨à³†à²—à²³à²¨à³à²¨à³ à²…à²¨à³à²µà³‡à²·à²¿à²¸à²¿',
    'What can we help with?': 'à²¨à²¾à²µà³ à²¹à³‡à²—à³† à²¸à²¹à²¾à²¯ à²®à²¾à²¡à²¬à²¹à³à²¦à³?',
    'Find support': 'à²¨à³†à²°à²µà³ à²¹à³à²¡à³à²•à²¿',
    'that fits your life.': 'à²¨à²¿à²®à³à²® à²œà³€à²µà²¨à²•à³à²•à³† à²¹à³Šà²‚à²¦à³à²µà²‚à²¤à³†.'
  },

  hi: {
    'Explore services': 'à¤¸à¥‡à¤µà¤¾à¤à¤ à¤¦à¥‡à¤–à¥‡à¤‚',
    'How it works': 'à¤¯à¤¹ à¤•à¥ˆà¤¸à¥‡ à¤•à¤¾à¤® à¤•à¤°à¤¤à¤¾ à¤¹à¥ˆ',
    'About': 'à¤¹à¤®à¤¾à¤°à¥‡ à¤¬à¤¾à¤°à¥‡ à¤®à¥‡à¤‚',
    'Find a scheme': 'à¤¯à¥‹à¤œà¤¨à¤¾ à¤–à¥‹à¤œà¥‡à¤‚',
    'Government support,': 'à¤¸à¤°à¤•à¤¾à¤°à¥€ à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾,',
    'within reach.': 'à¤…à¤¬ à¤†à¤ªà¤•à¥€ à¤ªà¤¹à¥à¤à¤š à¤®à¥‡à¤‚à¥¤',
    'Explore schemes': 'à¤¯à¥‹à¤œà¤¨à¤¾à¤à¤ à¤¦à¥‡à¤–à¥‡à¤‚',
    'What can we help with?': 'à¤¹à¤® à¤†à¤ªà¤•à¥€ à¤•à¥ˆà¤¸à¥‡ à¤®à¤¦à¤¦ à¤•à¤°à¥‡à¤‚?',
    'Find support': 'à¤¸à¤¹à¤¾à¤¯à¤¤à¤¾ à¤–à¥‹à¤œà¥‡à¤‚',
    'that fits your life.': 'à¤œà¥‹ à¤†à¤ªà¤•à¥‡ à¤œà¥€à¤µà¤¨ à¤•à¥‡ à¤…à¤¨à¥à¤•à¥‚à¤² à¤¹à¥‹à¥¤'
  }
};

const originalText = new Map(
  [...document.querySelectorAll('a, h1, h2')].map(el => [
    el,
    el.innerHTML
  ])
);

document.querySelector('#language')?.addEventListener('change', event => {
  const lang = event.target.value;

  originalText.forEach((original, element) => {
    element.innerHTML = original;
  });

  const dictionary = translations[lang];

  if (dictionary) {
    originalText.forEach((original, element) => {
      let updated = original;

      for (const [english, translated] of Object.entries(dictionary)) {
        updated = updated.replaceAll(english, translated);
      }

      element.innerHTML = updated;
    });
  }

  document.documentElement.lang = lang;
});

// Eligibility form
document.querySelector('#eligibility-form')?.addEventListener(
  'submit',
  async event => {
    event.preventDefault();

    const form = new FormData(event.currentTarget);
    const target = document.querySelector('#eligibility-results');

    target.textContent = 'Checking eligibility...';

    try {
      const result = await fetchJSON('/api/eligibility', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          age: form.get('age'),
          occupation: form.get('occupation')
        })
      });

      target.innerHTML =
        `<p class="eligibility-caveat">${escapeHtml(result.message)}</p>` +
        (result.suggestions || []).map(s =>
          `<a href="${escapeHtml(s.official_url)}"
              target="_blank"
              rel="noopener noreferrer">
             ${escapeHtml(s.name)} <span>â†—</span>
           </a>`
        ).join('') +
        (!(result.suggestions || []).length
          ? '<p>Choose an age range or occupation to see relevant places to start.</p>'
          : '');

    } catch (error) {
      console.error('Eligibility error:', error);
      target.textContent = 'Unable to check eligibility. Please try again.';
    }
  }
);

// AI Chat
document.querySelector('#chat-form')?.addEventListener(
  'submit',
  async event => {
    event.preventDefault();

    const input = document.querySelector('#chat-input');
    const message = input.value.trim();

    if (!message) return;

    const messages = document.querySelector('#chat-messages');

    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = message;
    messages.append(userMessage);

    input.value = '';

    const pending = document.createElement('div');
    pending.className = 'message bot-message';
    pending.textContent = 'One moment...';

    messages.append(pending);
    messages.scrollTop = messages.scrollHeight;

    try {
      const result = await fetchJSON('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });

      pending.textContent = result.reply || 'No response received.';

    } catch (error) {
      console.error('Chat error:', error);
      pending.textContent =
        'I could not connect just now. Please try again.';
    }

    messages.scrollTop = messages.scrollHeight;
  }
);

// Mobile navigation
document.querySelector('.menu-toggle')?.addEventListener(
  'click',
  event => {
    const nav = document.querySelector('.main-nav');

    if (!nav) return;

    const open = nav.classList.toggle('nav-open');

    event.currentTarget.setAttribute(
      'aria-expanded',
      String(open)
    );
  }
);

// Start application
initializeApp();

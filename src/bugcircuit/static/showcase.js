'use strict';
/* Showcase never requests project, report archive, settings, or user-specific APIs. */
const scenarioCopy = {
  oauth: {title:'Authentication callback',description:'A fictional callback returned HTTP 400 and explicitly reported a state mismatch.'},
  api: {title:'API degradation',description:'Synthetic HTTP events returned rate limiting and a server error.'},
  workflow: {title:'Workflow interruption',description:'Synthetic order-sync runs were marked failed and timed out.'}
};
const byId = id => document.getElementById(id);
const create = (tag, content, className) => {
  const element = document.createElement(tag);
  if (content !== undefined) element.textContent = String(content);
  if (className) element.className = className;
  return element;
};
let sampleReports = {};
function renderScenario(name) {
  const data = sampleReports[name];
  if (!data) return;
  const description = scenarioCopy[name];
  document.querySelectorAll('[data-scenario]').forEach(button => {
    const active = button.dataset.scenario === name;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  byId('sample-state').textContent = 'RULE ENGINE · SYNTHETIC';
  byId('sample-title').textContent = description.title;
  byId('sample-description').textContent = description.description;
  byId('sample-events').textContent = String(data.events.length);
  byId('sample-findings').textContent = String(data.findings.length);
  byId('sample-high').textContent = String(data.findings.filter(item => item.severity === 'high').length);

  const results = byId('sample-results');
  results.replaceChildren();
  if (!data.findings.length) results.appendChild(create('p', 'No findings matched these sample events.', 'loading'));
  for (const finding of data.findings) {
    const card = create('article', undefined, 'finding');
    const top = create('div', undefined, 'finding-top');
    const severity = ['high', 'medium', 'low'].includes(finding.severity) ? finding.severity : 'low';
    top.appendChild(create('span', severity, 'severity ' + severity));
    top.appendChild(create('code', finding.code));
    card.appendChild(top);
    card.appendChild(create('h5', finding.title));
    card.appendChild(create('p', finding.explanation));
    const details = create('details');
    details.appendChild(create('summary', 'Suggested verification steps · ' + (finding.evidence_ids || []).join(', ')));
    const list = create('ul');
    for (const check of finding.recommendations || []) list.appendChild(create('li', check));
    details.appendChild(list);
    card.appendChild(details);
    results.appendChild(card);
  }

  const timeline = byId('sample-timeline');
  timeline.replaceChildren();
  for (const event of data.events) {
    const row = create('div', undefined, 'timeline-item');
    row.appendChild(create('code', event.id));
    row.appendChild(create('span', [event.kind, event.status || event.method || '', event.url || event.error || ''].filter(Boolean).join(' · ')));
    timeline.appendChild(row);
  }
}
async function boot() {
  document.querySelectorAll('[data-scenario]').forEach(button =>
    button.addEventListener('click', () => renderScenario(button.dataset.scenario)));
  try {
    const response = await fetch('/api/showcase', {cache:'no-store', credentials:'same-origin'});
    if (!response.ok) throw new Error('Could not retrieve synthetic cases');
    const data = await response.json();
    if (!data || data.synthetic !== true || !data.examples) throw new Error('Invalid demo response');
    sampleReports = data.examples;
    renderScenario('oauth');
  } catch (_error) {
    byId('sample-state').textContent = 'DEMO UNAVAILABLE';
    byId('sample-results').replaceChildren(create('p', 'The sample could not load. Run BugCircuit locally and refresh this page.', 'loading'));
  }
}
boot();

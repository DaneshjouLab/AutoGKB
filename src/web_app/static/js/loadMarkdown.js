const markdownPane = document.querySelector('[data-pane="left"]');
const selectionBox = document.querySelector('[data-annotation="selection"]');
const tableWrapper = document.querySelector('[data-annotation="table"]');

// --- Table Data ---
const tableData = [
  {
    gene: {
      text: 'EGFR',
      evidence: [
        'EGFR mutations are commonly found in non-smoking patients with lung adenocarcinoma.',
        'EGFR L858R is a well-characterized sensitizing mutation associated with response to tyrosine kinase inhibitors.'
      ]
    },
    variant: {
      text: 'L858R',
      evidence: [
        'EGFR L858R is a well-characterized sensitizing mutation associated with response to tyrosine kinase inhibitors.',
        'The patient’s tumor harbored an EGFR L858R mutation identified via next-generation sequencing.'
      ]
    },
    interpretation: {
      text: 'Sensitizing',
      evidence: [
        'EGFR L858R is a well-characterized sensitizing mutation associated with response to tyrosine kinase inhibitors.',
        'Sensitizing mutations in EGFR typically respond well to osimertinib.'
      ]
    }
  },
  {
    gene: {
      text: 'TP53',
      evidence: [
        'TP53 mutations are frequent in smokers and often co-occur with other driver mutations.',
        'Loss-of-function variants in TP53, such as R175H, are associated with genomic instability.'
      ]
    },
    variant: {
      text: 'R175H',
      evidence: [
        'Loss-of-function variants in TP53, such as R175H, are associated with genomic instability.',
        'TP53 R175H was detected by immunohistochemistry and confirmed with sequencing.'
      ]
    },
    interpretation: {
      text: 'Pathogenic',
      evidence: [
        'TP53 R175H is classified as a pathogenic variant in COSMIC and ClinVar.',
        'Pathogenic mutations in TP53 are known to negatively impact prognosis.'
      ]
    }
  }
];

// --- Raw Markdown ---
let markdownText = `
# Clinical Case Summary

A 63-year-old Asian female with no smoking history presented with a persistent cough and mild dyspnea. Chest CT revealed a 2.3 cm spiculated lesion in the left upper lobe.
blabalbblas
EGFR mutations are commonly found in non-smoking patients with lung adenocarcinoma.
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>

EGFR L858R is a well-characterized sensitizing mutation associated with response to tyrosine kinase inhibitors.

The patient’s tumor harbored an EGFR L858R mutation identified via next-generation sequencing.

Sensitizing mutations in EGFR typically respond well to osimertinib.

TP53 mutations are frequent in smokers and often co-occur with other driver mutations.
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>
<br><br><br>

Loss-of-function variants in TP53, such as R175H, are associated with genomic instability.

TP53 R175H was detected by immunohistochemistry and confirmed with sequencing.

TP53 R175H is classified as a pathogenic variant in COSMIC and ClinVar.

Pathogenic mutations in TP53 are known to negatively impact prognosis.
`;

// --- Inject Evidence Anchors ---
const evidenceMap = {};
let evidenceIdCounter = 0;

tableData.forEach(row => {
  Object.values(row).forEach(cell => {
    cell.evidence.forEach(evidence => {
      if (!(evidence in evidenceMap)) {
        const id = `evidence-${evidenceIdCounter++}`;
        evidenceMap[evidence] = id;

        const safe = evidence.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(safe);
        const span = `<span id="${id}" class="evidence-anchor">${evidence}</span>`;
        markdownText = markdownText.replace(regex, span);
      }
    });
  });
});

// --- Render Markdown ---
markdownPane.innerHTML = marked.parse(markdownText);

// --- Build Table ---
const headers = ['Gene', 'Variant', 'Interpretation'];
const table = document.createElement('table');

const headerRow = document.createElement('tr');
headers.forEach(header => {
  const th = document.createElement('th');
  th.textContent = header;
  headerRow.appendChild(th);
});
table.appendChild(headerRow);

tableData.forEach(row => {
  const tr = document.createElement('tr');

  headers.forEach(header => {
    const key = header.toLowerCase();
    const cell = row[key];

    const td = document.createElement('td');
    td.textContent = cell.text;
    td.classList.add('clickable');

    td.addEventListener('click', () => {
      renderEvidence(cell.evidence, cell.text);
    });

    tr.appendChild(td);
  });

  table.appendChild(tr);
});

tableWrapper.appendChild(table);

// --- Render Evidence in Right Pane ---
function renderEvidence(evidenceList, entity = "Entity") {
  const rows = evidenceList.map(e => {
    const anchorId = evidenceMap[e];
    return `
      <tr>
        <td>
          <a href="#${anchorId}" onclick="scrollToEvidence('${anchorId}', \`${e}\`); return false;">
            ${e}
          </a>
        </td>
        <td>
          <button onclick="copyToClipboard(\`${e}\`)">📋</button>
        </td>
      </tr>
    `;
  }).join('');

  selectionBox.innerHTML = `
    <h3>Entity: ${entity}</h3>
    <table>
      <thead><tr><th>Evidence</th><th>Copy</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// --- Scroll + Highlight + Floating Copy ---
window.scrollToEvidence = function(anchorId, text) {
  const el = document.getElementById(anchorId);
  if (!el) return;

  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  highlight(anchorId, text);
};

window.highlight = function(id, text) {
  const el = document.getElementById(id);
  if (!el) return;

  const existing = document.getElementById('floating-clipboard');
  if (existing) existing.remove();

  el.classList.add('highlighted');
  setTimeout(() => el.classList.remove('highlighted'), 2000);

  const button = document.createElement('button');
  button.textContent = '📋';
  button.id = 'floating-clipboard';
  button.style.position = 'absolute';
  button.style.zIndex = 1000;
  button.style.padding = '4px';
  button.style.fontSize = '14px';

  const rect = el.getBoundingClientRect();
  button.style.top = `${window.scrollY + rect.top}px`;
  button.style.left = `${window.scrollX + rect.right + 10}px`;

  button.onclick = () => copyToClipboard(text);
  document.body.appendChild(button);

  setTimeout(() => button.remove(), 5000);
};

// --- Clipboard Copy ---
window.copyToClipboard = function(text) {
  navigator.clipboard.writeText(text)
    .then(() => console.log('Copied:', text))
    .catch(err => console.error('Clipboard copy failed', err));
};

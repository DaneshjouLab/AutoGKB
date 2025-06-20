const markdownPane = document.querySelector('[data-pane="left"]');
const selectionBox = document.querySelector('[data-annotation="selection"]');
const tableWrapper = document.querySelector('[data-annotation="table"]');

const tableData = [
  {
    gene: {
      text: 'EGFR',
      evidence: [
        '2 μM of VX-445',
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

let markdownText = `
# Clinical Case Summary

A 63-year-old Asian female with no smoking history presented with a persistent cough and mild dyspnea. Chest CT revealed a 2.3 cm spiculated lesion in the left upper lobe.

EGFR mutations are commonly found in non-smoking patients with lung adenocarcinoma.

EGFR L858R is a well-characterized sensitizing mutation associated with response to tyrosine kinase inhibitors.

The patient’s tumor harbored an EGFR L858R mutation identified via next-generation sequencing.

Sensitizing mutations in EGFR typically respond well to osimertinib.

TP53 mutations are frequent in smokers and often co-occur with other driver mutations.

Loss-of-function variants in TP53, such as R175H, are associated with genomic instability.

TP53 R175H was detected by immunohistochemistry and confirmed with sequencing.

TP53 R175H is classified as a pathogenic variant in COSMIC and ClinVar.

Pathogenic mutations in TP53 are known to negatively impact prognosis.
`;

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

async function loadAndRenderMarkdown() {
  const mdValue = document.body.dataset.md;
  const markdownPane = document.querySelector('[data-pane="left"]');
  let contentHTML = "";

  if (mdValue === "3") {
    try {
      const response = await fetch("/markdown/nih");
      const fetchedMarkdown = await response.text();
      contentHTML = marked.parse(fetchedMarkdown);

      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = contentHTML;

      let titleNode = null;
      let startFound = false;
      const finalContent = [];

      for (const node of tempDiv.childNodes) {
        if (!titleNode && node.nodeType === Node.ELEMENT_NODE && node.tagName === "H1") {
          titleNode = node.cloneNode(true);
        }

        if (!startFound && node.textContent.includes("PMID")) {
          startFound = true;
        }

        if (startFound) {
          finalContent.push(node.cloneNode(true));
        }
      }

      markdownPane.innerHTML = "";
      if (titleNode) {
        markdownPane.appendChild(titleNode);
      }
      finalContent.forEach(el => markdownPane.appendChild(el));

    } catch (err) {
      console.error("NIH Markdown load error:", err);
      markdownPane.innerHTML = "<p style='color: red;'>Failed to load NIH article.</p>";
      return;
    }
  } else {
    contentHTML = marked.parse(markdownText);
    markdownPane.innerHTML = contentHTML;
  }

  // --- Insert evidence spans into the rendered DOM
  Object.keys(evidenceMap).forEach(evidence => {
    const id = evidenceMap[evidence];
    const walker = document.createTreeWalker(markdownPane, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];

    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (node.nodeValue.includes(evidence)) {
        textNodes.push(node);
      }
    }

    textNodes.forEach(node => {
      const parts = node.nodeValue.split(evidence);
      if (parts.length < 2) return;

      const fragment = document.createDocumentFragment();

      for (let i = 0; i < parts.length; i++) {
        if (parts[i]) {
          fragment.appendChild(document.createTextNode(parts[i]));
        }

        if (i < parts.length - 1) {
          const span = document.createElement('span');
          span.id = id;
          span.className = 'evidence-anchor';
          span.textContent = evidence;
          fragment.appendChild(span);
        }
      }

      node.replaceWith(fragment);
    });
  });

  buildEvidenceTable();
}


// --- Build Table ---
function buildEvidenceTable() {
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

  tableWrapper.innerHTML = '';
  tableWrapper.appendChild(table);
}

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

document.addEventListener("DOMContentLoaded", () => {
  loadAndRenderMarkdown();
});
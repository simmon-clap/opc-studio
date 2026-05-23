/** Minimal SF-style stroke icons */

const WR_ICONS = {
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>',
  chevronDown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  diff: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M21 3 10 14"/><path d="M3 21l11-11"/></svg>',
  link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
  attach: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>',
  more: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>',
};

const ACTION_ICON = { approve: "check", reject: "x", submit_review: "send", edit: "check" };
const ACTION_TITLE = {
  approve: "批准",
  reject: "驳回",
  submit_review: "提交评审",
  edit: "编辑",
};

function iconBtn(name, onclick, title, extraClass = "", id = "") {
  const svg = WR_ICONS[name] || WR_ICONS.more;
  const cls = `icon-btn${extraClass ? ` ${extraClass}` : ""}`;
  const idAttr = id ? ` id="${id}"` : "";
  return `<button type="button" class="${cls}"${idAttr} title="${title || ""}" aria-label="${title || ""}" onclick="${onclick}">${svg}</button>`;
}

function microBtn(name, onclick, title, extraClass = "") {
  const svg = WR_ICONS[name] || WR_ICONS.more;
  const cls = `micro-btn${extraClass ? ` ${extraClass}` : ""}`;
  return `<button type="button" class="${cls}" title="${title || ""}" aria-label="${title || ""}" onclick="${onclick}">${svg}</button>`;
}

function iconDropdown(id, iconName, title, menuHtml) {
  return `
    <div class="wr-dropdown" id="${id}">
      <button type="button" class="icon-btn icon-btn-sm" title="${title}" aria-label="${title}" onclick="toggleDropdown('${id}', event)">${WR_ICONS[iconName] || WR_ICONS.download}</button>
      <div class="wr-dropdown-menu" onclick="event.stopPropagation()">${menuHtml}</div>
    </div>`;
}

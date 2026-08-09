(() => {
  const tabs = [...document.querySelectorAll("[data-home-tab]")];
  const panels = [...document.querySelectorAll("[data-home-panel]")];
  if (!tabs.length || !panels.length) return;

  const activate = (name, focus = false) => {
    tabs.forEach((tab) => {
      const active = tab.dataset.homeTab === name;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    });
    panels.forEach((panel) => {
      const active = panel.dataset.homePanel === name;
      panel.classList.toggle("is-active", active);
      panel.setAttribute("aria-hidden", String(!active));
    });
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab.dataset.homeTab));
    tab.addEventListener("keydown", (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      activate(tabs[next].dataset.homeTab, true);
    });
  });

  activate("issues");
})();

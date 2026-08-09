(() => {
  const dialog = document.querySelector("#news-lightbox");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const image = dialog.querySelector(".news-lightbox-image");
  const stage = dialog.querySelector(".news-lightbox-stage");
  const caption = dialog.querySelector(".news-lightbox-caption");
  const scaleOutput = dialog.querySelector(".news-lightbox-scale");
  const closeButton = dialog.querySelector("[data-lightbox-close]");
  const zoomInButton = dialog.querySelector("[data-lightbox-zoom-in]");
  const zoomOutButton = dialog.querySelector("[data-lightbox-zoom-out]");
  const resetButton = dialog.querySelector("[data-lightbox-reset]");

  let zoom = 1;
  let baseWidth = 0;
  let baseHeight = 0;
  let opener = null;

  const render = () => {
    image.style.width = `${Math.round(baseWidth * zoom)}px`;
    image.style.height = `${Math.round(baseHeight * zoom)}px`;
    scaleOutput.value = `${Math.round(zoom * 100)}%`;
    zoomOutButton.disabled = zoom <= 1;
    zoomInButton.disabled = zoom >= 4;
  };

  const fit = () => {
    if (!image.naturalWidth || !image.naturalHeight) return;
    const availableWidth = Math.max(stage.clientWidth - 48, 240);
    const availableHeight = Math.max(stage.clientHeight - 48, 240);
    const fitScale = Math.min(
      availableWidth / image.naturalWidth,
      availableHeight / image.naturalHeight,
      1,
    );
    baseWidth = image.naturalWidth * fitScale;
    baseHeight = image.naturalHeight * fitScale;
    zoom = 1;
    render();
    stage.scrollTo({ top: 0, left: 0 });
  };

  const changeZoom = (nextZoom) => {
    zoom = Math.min(4, Math.max(1, nextZoom));
    render();
  };

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-lightbox]");
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    opener = link;
    image.src = link.href;
    image.alt = link.querySelector("img")?.alt || "";
    caption.textContent = link.dataset.caption || image.alt;
    document.body.classList.add("has-open-lightbox");
    dialog.showModal();
    closeButton.focus();
    if (image.complete) fit();
  });

  image.addEventListener("load", fit);
  zoomInButton.addEventListener("click", () => changeZoom(zoom + 0.25));
  zoomOutButton.addEventListener("click", () => changeZoom(zoom - 0.25));
  resetButton.addEventListener("click", fit);
  closeButton.addEventListener("click", () => dialog.close());
  image.addEventListener("dblclick", () => changeZoom(zoom === 1 ? 2 : 1));

  stage.addEventListener("wheel", (event) => {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    changeZoom(zoom + (event.deltaY < 0 ? 0.25 : -0.25));
  }, { passive: false });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  dialog.addEventListener("close", () => {
    document.body.classList.remove("has-open-lightbox");
    image.removeAttribute("src");
    opener?.focus();
  });

  window.addEventListener("resize", () => {
    if (dialog.open) fit();
  });

  document.addEventListener("keydown", (event) => {
    if (!dialog.open) return;
    if (event.key === "+" || event.key === "=") changeZoom(zoom + 0.25);
    if (event.key === "-") changeZoom(zoom - 0.25);
    if (event.key === "0") fit();
  });
})();

const searchInput = document.querySelector("#brapi-search");

if (searchInput) {
  const results = document.querySelector("#brapi-results");
  const status = document.querySelector("#brapi-search-status");
  const form = document.querySelector("#asset-form");
  let timer;
  let controller;

  searchInput.addEventListener("input", () => {
    clearTimeout(timer);
    controller?.abort();
    results.replaceChildren();
    const query = searchInput.value.trim();
    if (query.length < 2) {
      status.textContent = "Digite ao menos dois caracteres para buscar.";
      return;
    }

    status.textContent = "";
    timer = setTimeout(async () => {
      controller = new AbortController();
      status.textContent = "Buscando no catálogo da B3…";
      try {
        const response = await fetch(
          `${searchInput.dataset.searchUrl}?q=${encodeURIComponent(query)}`,
          { headers: { Accept: "application/json" }, signal: controller.signal },
        );
        const payload = await response.json();
        if (!response.ok) throw new Error("Busca indisponível");
        if (searchInput.value.trim() !== query) return;

        for (const asset of payload.results) {
          const item = document.createElement("li");
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = `${asset.symbol} · ${asset.name}`;
          button.addEventListener("click", () => {
            for (const field of ["name", "market", "ticker", "asset_class", "subtype", "currency"]) {
              form.elements[field].value = asset[field];
            }
            searchInput.value = asset.symbol;
            results.replaceChildren();
            status.textContent = `${asset.symbol} selecionado. Revise os campos e salve o ativo.`;
            form.elements.name.focus();
          });
          item.append(button);
          results.append(item);
        }
        status.textContent = results.childElementCount
          ? `${results.childElementCount} resultado(s). Selecione um para preencher o cadastro.`
          : "Nenhum ativo encontrado; você ainda pode preencher o cadastro manualmente.";
      } catch (error) {
        if (error.name !== "AbortError") {
          status.textContent = "Catálogo indisponível. Você ainda pode preencher o cadastro manualmente.";
        }
      }
    }, 300);
  });
}

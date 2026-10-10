document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.querySelector("#portfolio-chart");
  const source = document.querySelector("#snapshot-data");
  if (!canvas || !source || !window.Chart) return;

  const snapshots = JSON.parse(source.textContent);
  new Chart(canvas, {
    type: "line",
    data: {
      labels: snapshots.map((item) => item.date),
      datasets: [{
        label: "Patrimônio total (BRL)",
        data: snapshots.map((item) => ({ y: Number(item.value), exact: item.value })),
        borderColor: "#3566c4",
        backgroundColor: "rgba(53, 102, 196, .12)",
        fill: true,
        tension: 0.2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { ticks: { callback: (value) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value) } },
      },
      plugins: {
        tooltip: { callbacks: { label: (context) => `BRL ${context.raw.exact}` } },
      },
    },
  });
});

const todayButton = document.querySelector("#set-transaction-today");
todayButton?.addEventListener("click", () => {
  const now = new Date();
  const today = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  document.querySelector("#id_transaction_date").value = today;
});

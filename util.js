export const fmtData = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
};
export const fmtDataOra = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const ora = iso.length > 10 ? " " + d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" }) : "";
  return fmtData(iso) + ora;
};
export const giorniLabel = (g) => (g == null ? "" : g < 0 ? `scaduta da ${-g} g` : g === 0 ? "oggi" : g === 1 ? "domani" : `${g} giorni`);
export const classeSettore = (s) => (s === "Cultura" ? "cultura" : s === "Sociale" ? "sociale" : "altro");

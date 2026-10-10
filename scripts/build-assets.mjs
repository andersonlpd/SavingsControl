import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("static/vendor", { recursive: true });
copyFileSync("node_modules/chart.js/dist/chart.umd.js", "static/vendor/chart.umd.js");

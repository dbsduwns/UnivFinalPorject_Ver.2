import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
const { FileBlob, PresentationFile } = await import(pathToFileURL("C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs").href);
const finalPath = "D:/coding/YunGit/UnivFinalProject/Ver.2/output/KNU-Campus_A4_시안_1-2장.pptx";
const outDir = "D:/coding/YunGit/UnivFinalProject/Ver.2/.codex-build/final-previews";
await fs.mkdir(outDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(finalPath));
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1.4 });
  await fs.writeFile(path.join(outDir, `slide-${index + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({ slides: presentation.slides.items.length, outDir }));


import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const workspaceDir = "D:/coding/YunGit/UnivFinalProject/Ver.2";
const skillDir = "C:/Users/윤여준/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/Presentations";
const stagingDir = path.join(workspaceDir, ".codex-finalizer");
const candidatePath = path.join(workspaceDir, ".codex-build", "KNU-Campus_A4_시안_1-2장_candidate.pptx");
const finalPath = path.join(workspaceDir, "output", "KNU-Campus_A4_시안_1-2장.pptx");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(finalPath), { recursive: true });

const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href);

const result = await finalizePresentation({
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe",
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "7562850,10696575", "--validate-bullet-geometry", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: ["Arial"], scriptFonts: { ea: "Arial" } },
  explicitTotalSlideCount: 2,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "KNU-Campus_A4_시안_1-2장.validation.json"),
});
console.log(JSON.stringify(result));


import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
const { Presentation, PresentationFile } = await import(pathToFileURL("C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs").href);

const workspaceDir = "D:/coding/YunGit/UnivFinalProject/Ver.2";
const buildDir = path.join(workspaceDir, ".codex-build");
const outputDir = path.join(workspaceDir, "output");
const previewDir = path.join(buildDir, "previews");
const candidatePath = path.join(buildDir, "KNU-Campus_A4_시안_1-2장_candidate.pptx");

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const W = 794;
const H = 1123;
const colors = {
  bg: "#F5F7FB",
  ink: "#121826",
  muted: "#5B6475",
  blue: "#3E5BE8",
  blueDark: "#2443C8",
  yellow: "#F4C63D",
  line: "#D8DEEA",
  white: "#FFFFFF",
};
const font = "Aptos";

function addText(slide, name, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = { fontFamily: font, color: colors.ink, ...style };
  return shape;
}

function addRect(slide, name, position, fill, lineFill = fill, radius = null) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    name,
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: 0 },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function addLine(slide, name, position, fill = colors.line, width = 2) {
  return slide.shapes.add({
    geometry: "rect",
    name,
    position,
    fill,
    line: { style: "solid", fill, width: 0 },
  });
}

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

// Slide 1: cover
{
  const slide = presentation.slides.add();
  slide.background.fill = colors.bg;
  addRect(slide, "left-accent", { left: 0, top: 0, width: 16, height: H }, colors.blue);
  addRect(slide, "top-tag", { left: 86, top: 116, width: 622, height: 66 }, colors.blue, colors.blue, "rounded-2xl");
  addText(slide, "top-tag-text", "KNU-Campus", { left: 86, top: 124, width: 622, height: 48 }, {
    fontSize: 26, bold: true, color: colors.white, alignment: "center",
  });
  addText(slide, "cover-description", "학교 생활에 필요한 정보를 한곳에서 확인하는\n대학생활 통합 앱", { left: 88, top: 276, width: 618, height: 136 }, {
    fontSize: 28, bold: true, color: colors.blueDark, alignment: "center", breakLine: true,
  });
  addText(slide, "app-title", "KNU-Campus", { left: 54, top: 445, width: 686, height: 116 }, {
    fontSize: 58, bold: true, color: colors.ink, alignment: "center",
  });
  addLine(slide, "title-rule", { left: 245, top: 601, width: 304, height: 4 }, colors.yellow);
  addText(slide, "cover-experience", "공지사항과 학사일정부터 시간표, 커뮤니티까지\n대학생활의 흐름을 하나의 앱으로 연결합니다", { left: 92, top: 666, width: 610, height: 104 }, {
    fontSize: 22, color: colors.muted, alignment: "center", breakLine: true,
  });
  addLine(slide, "footer-rule", { left: 86, top: 959, width: 622, height: 2 }, colors.line);
  addText(slide, "student-id", "202104255", { left: 86, top: 984, width: 220, height: 36 }, {
    fontSize: 20, bold: true, color: colors.blue,
  });
  addText(slide, "student-name", "윤여준", { left: 486, top: 984, width: 222, height: 36 }, {
    fontSize: 20, bold: true, color: colors.ink, alignment: "right",
  });
  slide.speakerNotes.text = "Visual direction referenced from the supplied SeoulMate exhibition PDF: pale blue-gray background, blue accent, yellow highlight, simple editorial layout.";
}

// Slide 2: background
{
  const slide = presentation.slides.add();
  slide.background.fill = colors.bg;
  addRect(slide, "left-accent", { left: 0, top: 0, width: 16, height: H }, colors.blue);
  addText(slide, "section-number", "02", { left: 72, top: 54, width: 88, height: 62 }, {
    fontSize: 42, bold: true, color: colors.blue,
  });
  addLine(slide, "header-rule", { left: 176, top: 53, width: 2, height: 62 }, colors.line);
  addText(slide, "slide-title", "앱 제작 배경", { left: 208, top: 48, width: 500, height: 72 }, {
    fontSize: 38, bold: true, color: colors.ink,
  });
  addText(slide, "slide-kicker", "학교생활 정보와 학생 간 소통이 한 흐름으로 이어지도록", { left: 74, top: 151, width: 640, height: 42 }, {
    fontSize: 18, color: colors.muted,
  });

  addText(slide, "current-label", "현재 학교 앱", { left: 74, top: 246, width: 270, height: 42 }, {
    fontSize: 28, bold: true, color: colors.blueDark,
  });
  addText(slide, "current-headline", "학교생활에 필요한 공지와\n학사 정보를 확인할 수 있습니다", { left: 74, top: 304, width: 620, height: 86 }, {
    fontSize: 27, bold: true, color: colors.ink, breakLine: true,
  });
  addText(slide, "current-body", "학교 공지사항, 학사일정 등 공식 정보를 빠르게 확인할 수 있다는 점은 강점입니다.", { left: 74, top: 420, width: 610, height: 70 }, {
    fontSize: 20, color: colors.muted,
  });
  addLine(slide, "section-rule-1", { left: 74, top: 542, width: 646, height: 2 }, colors.line);

  addText(slide, "gap-label", "아쉬운 점", { left: 74, top: 590, width: 270, height: 42 }, {
    fontSize: 28, bold: true, color: colors.blueDark,
  });
  addText(slide, "gap-headline", "학생들이 자주 사용하는 기능은\n한곳에 모여 있지 않습니다", { left: 74, top: 648, width: 620, height: 86 }, {
    fontSize: 27, bold: true, color: colors.ink, breakLine: true,
  });
  addText(slide, "gap-body", "시간표 확인, 커뮤니티, 채팅, 시간표 공유 같은 기능을 이용하기 어렵습니다.", { left: 74, top: 762, width: 610, height: 64 }, {
    fontSize: 20, color: colors.muted,
  });

  addRect(slide, "direction-band", { left: 54, top: 882, width: 686, height: 176 }, colors.blue, colors.blue, "rounded-2xl");
  addText(slide, "direction-label", "KNU-Campus의 방향", { left: 82, top: 910, width: 620, height: 34 }, {
    fontSize: 18, bold: true, color: colors.yellow,
  });
  addText(slide, "direction-body", "학교 앱의 공식 정보와 대학생 커뮤니티 기능을\n하나로 연결해, 필요한 정보를 찾고 사람들과 소통하는 경험을 이어갑니다.", { left: 82, top: 952, width: 620, height: 80 }, {
    fontSize: 21, bold: true, color: colors.white, breakLine: true,
  });
  slide.speakerNotes.text = "Content based on the user's brief: school app strengths are official notices and academic schedules; gaps are timetable, community, chat, and timetable sharing; KNU-Campus combines both for a continuous campus-life experience.";
}

for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1.4 });
  await fs.writeFile(path.join(previewDir, `slide-${index + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(candidatePath);
console.log(JSON.stringify({ candidatePath, previewDir, slideSize: `${W},${H}`, slides: presentation.slides.items.length }));


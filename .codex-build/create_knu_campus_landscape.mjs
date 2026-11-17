import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
const { Presentation, PresentationFile } = await import(pathToFileURL("C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs").href);

const workspaceDir = "D:/coding/YunGit/UnivFinalProject/Ver.2";
const buildDir = path.join(workspaceDir, ".codex-build");
const previewDir = path.join(buildDir, "landscape-previews");
const candidatePath = path.join(buildDir, "KNU-Campus_A4_가로형_시안_1-2장_candidate.pptx");
await fs.mkdir(previewDir, { recursive: true });

const W = 1123, H = 794;
const colors = { bg: "#F5F7FB", ink: "#121826", muted: "#5B6475", blue: "#3E5BE8", blueDark: "#2443C8", yellow: "#F4C63D", line: "#D8DEEA", white: "#FFFFFF" };
const font = "Arial";

function text(slide, name, value, position, style = {}) {
  const shape = slide.shapes.add({ geometry: "textbox", name, position, fill: "none", line: { style: "solid", fill: "none", width: 0 } });
  shape.text = value;
  shape.text.style = { fontFamily: font, color: colors.ink, ...style };
  return shape;
}
function rect(slide, name, position, fill, radius = null) {
  return slide.shapes.add({ geometry: radius ? "roundRect" : "rect", name, position, fill, line: { style: "solid", fill, width: 0 }, ...(radius ? { borderRadius: radius } : {}) });
}

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = colors.bg;
  rect(slide, "left-accent", { left: 0, top: 0, width: 16, height: H }, colors.blue);
  rect(slide, "right-color-field", { left: 902, top: 0, width: 221, height: H }, colors.blue);
  rect(slide, "right-yellow-accent", { left: 820, top: 626, width: 240, height: 14 }, colors.yellow);
  rect(slide, "top-tag", { left: 72, top: 66, width: 440, height: 54 }, colors.blue, "rounded-2xl");
  text(slide, "top-tag-text", "KNU-Campus", { left: 72, top: 73, width: 440, height: 40 }, { fontSize: 23, bold: true, color: colors.white, alignment: "center" });
  text(slide, "cover-description", "학교 생활에 필요한 정보를 한곳에서 확인하는\n대학생활 통합 앱", { left: 72, top: 182, width: 640, height: 88 }, { fontSize: 28, bold: true, color: colors.blueDark, breakLine: true });
  text(slide, "app-title", "KNU-Campus", { left: 68, top: 298, width: 760, height: 90 }, { fontSize: 56, bold: true, color: colors.ink });
  rect(slide, "title-rule", { left: 72, top: 416, width: 270, height: 5 }, colors.yellow);
  text(slide, "cover-experience", "공지사항과 학사일정부터 시간표, 커뮤니티까지\n대학생활의 흐름을 하나의 앱으로 연결합니다", { left: 72, top: 468, width: 680, height: 68 }, { fontSize: 21, color: colors.muted, breakLine: true });
  rect(slide, "footer-rule", { left: 72, top: 690, width: 770, height: 2 }, colors.line);
  text(slide, "student-id", "202104255", { left: 72, top: 716, width: 220, height: 30 }, { fontSize: 18, bold: true, color: colors.blue });
  text(slide, "student-name", "윤여준", { left: 650, top: 716, width: 192, height: 30 }, { fontSize: 18, bold: true, color: colors.ink, alignment: "right" });
  slide.speakerNotes.text = "A4 landscape exhibition-panel draft. Visual direction referenced from the supplied SeoulMate exhibition PDF: pale blue-gray background, blue accent, yellow highlight, simple editorial layout.";
}

// 2. Background
{
  const slide = presentation.slides.add();
  slide.background.fill = colors.bg;
  rect(slide, "left-accent", { left: 0, top: 0, width: 16, height: H }, colors.blue);
  text(slide, "section-number", "02", { left: 70, top: 42, width: 72, height: 54 }, { fontSize: 38, bold: true, color: colors.blue });
  rect(slide, "header-rule", { left: 158, top: 43, width: 2, height: 52 }, colors.line);
  text(slide, "slide-title", "앱 제작 배경", { left: 186, top: 39, width: 420, height: 58 }, { fontSize: 35, bold: true, color: colors.ink });
  text(slide, "slide-kicker", "학교생활 정보와 학생 간 소통이 한 흐름으로 이어지도록", { left: 70, top: 126, width: 800, height: 34 }, { fontSize: 18, color: colors.muted });

  text(slide, "current-label", "현재 학교 앱", { left: 70, top: 220, width: 300, height: 36 }, { fontSize: 25, bold: true, color: colors.blueDark });
  text(slide, "current-headline", "학교생활에 필요한 공지와\n학사 정보를 확인할 수 있습니다", { left: 70, top: 270, width: 460, height: 76 }, { fontSize: 25, bold: true, color: colors.ink, breakLine: true });
  text(slide, "current-body", "학교 공지사항과 학사일정 등 공식 정보를 빠르게 확인할 수 있다는 점은 강점입니다.", { left: 70, top: 370, width: 445, height: 80 }, { fontSize: 19, color: colors.muted });
  rect(slide, "middle-rule", { left: 562, top: 208, width: 2, height: 254 }, colors.line);
  text(slide, "gap-label", "아쉬운 점", { left: 620, top: 220, width: 260, height: 36 }, { fontSize: 25, bold: true, color: colors.blueDark });
  text(slide, "gap-headline", "학생들이 자주 사용하는 기능은\n한곳에 모여 있지 않습니다", { left: 620, top: 270, width: 430, height: 76 }, { fontSize: 25, bold: true, color: colors.ink, breakLine: true });
  text(slide, "gap-body", "시간표 확인, 커뮤니티, 채팅, 시간표 공유 같은 기능을 이용하기 어렵습니다.", { left: 620, top: 370, width: 425, height: 80 }, { fontSize: 19, color: colors.muted });

  rect(slide, "direction-band", { left: 70, top: 548, width: 975, height: 174 }, colors.blue, "rounded-2xl");
  text(slide, "direction-label", "KNU-Campus의 방향", { left: 104, top: 578, width: 260, height: 30 }, { fontSize: 18, bold: true, color: colors.yellow });
  text(slide, "direction-body", "학교 앱의 공식 정보와 대학생 커뮤니티 기능을 하나로 연결해,\n필요한 정보를 찾고 사람들과 소통하는 경험을 이어갑니다.", { left: 104, top: 620, width: 850, height: 64 }, { fontSize: 23, bold: true, color: colors.white, breakLine: true });
  slide.speakerNotes.text = "Content based on the user's brief: school app strengths are official notices and academic schedules; gaps are timetable, community, chat, and timetable sharing; KNU-Campus combines both for a continuous campus-life experience.";
}

for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1.4 });
  await fs.writeFile(path.join(previewDir, `slide-${index + 1}.png`), new Uint8Array(await png.arrayBuffer()));
}
const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(candidatePath);
console.log(JSON.stringify({ candidatePath, previewDir, slideSize: `${W},${H}`, slides: presentation.slides.items.length }));


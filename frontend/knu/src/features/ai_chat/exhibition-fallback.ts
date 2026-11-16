export function buildExhibitionReply(question: string): string {
  const normalized = question.trim().toLowerCase();

  if (normalized.includes("학사일정") || normalized.includes("학사 일정")) {
    return "학사일정은 학사일정 메뉴에서 확인할 수 있습니다. 전시용 데이터에는 이번 학기 주요 일정이 미리 등록되어 있습니다.";
  }

  if (normalized.includes("취업") || normalized.includes("공지")) {
    return "취업 및 학교 공지는 공지사항 메뉴에서 최신 목록과 상세 내용을 확인할 수 있습니다.";
  }

  if (
    normalized.includes("오늘") &&
    (normalized.includes("수업") || normalized.includes("시간표"))
  ) {
    return "오늘 수업 일정은 시간표 메뉴에서 확인할 수 있습니다. 로그인한 계정의 전시용 시간표가 표시됩니다.";
  }

  if (
    normalized.includes("학식") ||
    normalized.includes("식단") ||
    normalized.includes("메뉴")
  ) {
    return "오늘의 학식 메뉴는 식단 메뉴에서 확인할 수 있습니다.";
  }

  if (normalized.includes("셔틀") || normalized.includes("버스")) {
    return "셔틀버스 운행 정보는 셔틀 메뉴에서 학기별 시간표와 노선을 확인할 수 있습니다.";
  }

  return "학사일정, 공지사항, 오늘 수업, 학식, 셔틀버스와 관련된 질문은 각 메뉴에서 직접 확인할 수 있습니다.";
}

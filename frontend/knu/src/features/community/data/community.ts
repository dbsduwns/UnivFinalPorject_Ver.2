export type CommunityBoard = {
  slug: string;
  title: string;
  description: string;
};

export const COMMUNITY_BOARDS: CommunityBoard[] = [
  {
    slug: "free",
    title: "자유게시판",
    description: "학교생활과 일상 이야기를 자유롭게 나눠요.",
  },
  {
    slug: "freshman",
    title: "새내기게시판",
    description: "새내기를 위한 질문과 정보를 나눠요.",
  },
  {
    slug: "graduate",
    title: "졸업생게시판",
    description: "졸업생과 재학생이 경험을 나눠요.",
  },
  {
    slug: "market",
    title: "장터 (중고거래)",
    description: "필요한 물건을 안전하게 거래해요.",
  },
  {
    slug: "club",
    title: "동아리/학회",
    description: "동아리와 학회 소식을 확인해요.",
  },
  {
    slug: "career",
    title: "취업/진로",
    description: "취업 정보와 진로 고민을 나눠요.",
  },
];

export const getCommunityBoard = (slug?: string) =>
  COMMUNITY_BOARDS.find((board) => board.slug === slug);

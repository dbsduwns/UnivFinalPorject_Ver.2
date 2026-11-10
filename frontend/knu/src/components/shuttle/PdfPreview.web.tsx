import { Text } from "react-native";

type PdfPreviewProps = {
  sourceUrl: string | null;
};

export default function PdfPreview({ sourceUrl }: PdfPreviewProps) {
  if (!sourceUrl) return null;
  return (
    <Text className="flex-1 px-5 text-center text-gray-500">
      웹에서는 아래 버튼으로 PDF를 엽니다.
    </Text>
  );
}

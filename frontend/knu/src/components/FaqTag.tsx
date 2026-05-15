import { Text, View } from "react-native";

export const FaqTag = () => {
    return (
        // Faq Recommendation
        <View 
            className="FaqWrapper flex-row w-full px-5 mt-2 justify-start items-center">
            <View 
                className="mr-3 bg-white"
                style={{ 
                    borderWidth:3,
                    borderRadius: 20,
                    borderColor: '#E5E7EB',
                }}>
                <Text
                    className="p-2"
                    style={{ fontSize: 12}}>
                    오늘 시간표</Text>
            </View>
            <View
                className="mr-3 bg-white"
                style={{
                    borderWidth:3,
                    borderRadius: 20,
                    borderColor: '#E5E7EB',
                }}>
                <Text 
                    className="p-2"
                    style={{ fontSize: 12 }}>
                    중간고사 기간 알려줘
                </Text>
            </View>
            <View
                className="mr-3 bg-white"
                style={{
                    borderWidth:3,
                    borderRadius: 20,
                    borderColor: '#E5E7EB',
                }}>
                <Text 
                    className="p-2"
                    style={{ fontSize: 12 }}>
                    디자인 인턴 공고 찾아줘
                </Text>
            </View>
        </View>
    )
}
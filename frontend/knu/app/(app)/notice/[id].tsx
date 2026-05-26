import { useLocalSearchParams, router } from "expo-router";
import { View, Text, TouchableOpacity, ScrollView, Linking, Image, Dimensions, Platform, StatusBar } from "react-native";
import * as WebBrowser from 'expo-web-browser';
import { useState, useEffect } from "react";
import { ChevronLeft } from "lucide-react-native";

import { useNotice } from "@/features/notice/hooks/use_notices";

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 이미지 정보를 관리하기 위한 타입
interface ImageItem {
    url: string;
    height: number;
}

export default function NoticeDetail() {
    const { id } = useLocalSearchParams();
    const noticeId = typeof id === "string" ? parseInt(id, 10) : null;

    const { data: notice, isLoading } = useNotice(noticeId);    
    const [imageItems, setImageItems] = useState<ImageItem[]>([]);
    
    const handleOpenURL = async (url: string | null | undefined) => {
        if (!url) return;
        
        try {
            await WebBrowser.openBrowserAsync(url, {
                readerMode: false,
                dismissButtonStyle: 'close',
                toolbarColor: '#ffffff',
            });
        } catch (error) {
            try {
                await Linking.openURL(url);
            } catch (linkError) {
                console.error("URL 열기 실패:", linkError);
            }
        }
    };

    useEffect(() => {
        if (notice?.content) {
            // [이미지 공지] 또는 [이미지] 패턴 모두 추출
            const imagePattern = /\[(?:이미지 공지|이미지)\]\s+(https?:\/\/\S+)/g;
            const matches = Array.from(notice.content.matchAll(imagePattern));
            const urls = matches.map(match => match[1]);

            if (urls.length > 0) {
                // 모든 이미지의 크기를 가져와서 상태 업데이트
                const newItems: ImageItem[] = [];
                let loadedCount = 0;

                urls.forEach((url, index) => {
                    Image.getSize(url, (width, height) => {
                        const ratio = height / width;
                        newItems[index] = { 
                            url, 
                            height: (SCREEN_WIDTH - 32) * ratio 
                        };
                        loadedCount++;
                        
                        if (loadedCount === urls.length) {
                            setImageItems(newItems.filter(item => item !== undefined));
                        }
                    }, (error) => {
                        console.warn(`이미지 크기 가져오기 실패 (${url}):`, error);
                        loadedCount++;
                        if (loadedCount === urls.length) {
                            setImageItems(newItems.filter(item => item !== undefined));
                        }
                    });
                });
            } else {
                setImageItems([]);
            }
        }
    }, [notice?.content]);

    // 이미지 태그들을 제외한 순수 텍스트 내용
    const cleanContent = notice?.content
        ?.replace(/\[(?:이미지 공지|이미지)\]\s+https?:\/\/\S+/g, "")
        .trim();

    if (isLoading) {
        return (
            <View className="flex-1 justify-center items-center bg-white">
                <Text className="text-gray-500">로딩 중...</Text>
            </View>
        );
    }

    if (!notice) {
        return (
            <View className="flex-1 justify-center items-center bg-white">
                <Text className="text-gray-500">공지사항을 찾을 수 없습니다.</Text>
            </View>
        );
    }

    return (
        <View 
            className="flex-1 bg-white" 
            style={{ 
                paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0 
            }}
        >
            {/* 상단 고정 헤더 영역 */}
            <View className="bg-white px-4 pb-4 pt-2 border-b border-gray-100 shadow-sm">
                <TouchableOpacity 
                    onPress={() => router.back()}
                    className="w-10 h-10 -ml-2 items-center justify-center rounded-full"
                >
                    <ChevronLeft size={28} color="#374151" />
                </TouchableOpacity>
                
                <Text className="text-xl font-bold text-gray-900 mt-1" numberOfLines={2}>
                    {notice.title}
                </Text>
                
                <View className="flex-row mt-3 items-center">
                    <View className="bg-blue-50 px-2 py-1 rounded">
                        <Text className="text-xs text-blue-600 font-bold">{notice.category}</Text>
                    </View>
                    <Text className="ml-3 text-sm text-gray-400">
                        {notice.published_at ? new Date(notice.published_at).toLocaleDateString('ko-KR') : "날짜 정보 없음"}
                    </Text>
                </View>
            </View>

            {/* 스크롤 가능한 본문 영역 */}
            <ScrollView 
                className="flex-1"
                showsVerticalScrollIndicator={true}
                contentContainerStyle={{ paddingBottom: 40 }}
            >
                <View className="p-4">
                    {/* 여러 개의 이미지 렌더링 */}
                    {imageItems.map((item, index) => (
                        <View key={index} className="mb-6 items-center shadow-sm">
                            <Image 
                                source={{ uri: item.url }}
                                style={{ 
                                    width: SCREEN_WIDTH - 32, 
                                    height: item.height,
                                    borderRadius: 12,
                                    backgroundColor: '#F9FAFB'
                                }}
                                resizeMode="contain"
                            />
                            {index === 0 && imageItems.length === 1 && (
                                <Text className="mt-2 text-xs text-gray-400 italic">이미지 공지사항입니다.</Text>
                            )}
                        </View>
                    ))}

                    {cleanContent ? (
                        <Text className="text-base text-gray-800 leading-7">
                            {cleanContent}
                        </Text>
                    ) : imageItems.length === 0 && (
                        <View className="py-10 items-center">
                            <Text className="text-gray-400 italic">상세 내용이 없습니다.</Text>
                        </View>
                    )}

                    {(notice.attachment_url || notice.source_url) && (
                        <View className="mt-10 pt-6 border-t border-gray-100">
                            <Text className="text-sm font-bold text-gray-400 mb-3 ml-1">관련 링크</Text>
                            {notice.attachment_url && (
                                <TouchableOpacity 
                                    className="bg-blue-600 p-4 rounded-xl flex-row items-center mb-3 shadow-sm"
                                    onPress={() => handleOpenURL(notice.attachment_url)}
                                >
                                    <Text className="flex-1 text-white font-bold text-center">첨부파일 확인하기</Text>
                                </TouchableOpacity>
                            )}
                            {notice.source_url && (
                                <TouchableOpacity 
                                    className="bg-gray-100 p-4 rounded-xl flex-row items-center shadow-sm"
                                    onPress={() => handleOpenURL(notice.source_url)}
                                >
                                    <Text className="flex-1 text-gray-600 font-bold text-center">원문 공지 보기</Text>
                                </TouchableOpacity>
                            )}
                        </View>
                    )}
                </View>
            </ScrollView>
        </View>
    );
}

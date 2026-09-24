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
    isAttachment?: boolean;
}

// 학교 홈페이지 크롤링시 상대 경로 
// 절대 URL 시 변환해서 상대 경로로
const NOTICE_BASE_URL = "https://web.kangnam.ac.kr/";

const trimImageUrl = (value: string) =>
    value
        .trim()
        .replace(/^['"`<]+|['"`>]+$/g, "")
        // 본문 문장에 붙은 괄호·문장부호는 URL에서 제외합니다.
        .replace(/[),.;!?]+$/g, "");

const normalizeImageUrl = (value: string): string | null => {
    const raw = trimImageUrl(value);
    if (!raw) return null;

    try {
        // http(s)는 그대로, /comm/...·../comm/...·comm/...은 기준 주소로 변환합니다.
        return new URL(raw, NOTICE_BASE_URL).toString();
    } catch {
        return null;
    }
};

const isLikelyImageUrl = (url: string) => {
    try {
        const parsed = new URL(url);
        return (
            /\/comm\/cmnFile\//i.test(parsed.pathname) ||
            /\.(?:png|jpe?g|gif|webp|svg|bmp|heic)(?:$|[?#])/i.test(
                `${parsed.pathname}${parsed.search}`
            )
        );
    } catch {
        return false;
    }
};

/**
 * 크롤러 버전별로 저장된 이미지 표현을 모두 URL 배열로 변환합니다.
 * - [이미지] https://...
 * - [이미지 공지] /comm/cmnFile/image.do?...
 * - <img src="...">
 * - ![설명](...)
 * - 본문에 단독으로 저장된 http(s) 또는 /comm/cmnFile URL
 */
const extractImageUrls = (content: string): string[] => {
    const urls: string[] = [];
    const add = (value: string | undefined) => {
        if (!value) return;
        const normalized = normalizeImageUrl(value);
        if (normalized && !urls.includes(normalized)) urls.push(normalized);
    };

    // HTML img 태그
    const htmlImagePattern = /<img\b[^>]*\bsrc\s*=\s*(["'])(.*?)\1[^>]*>/gi;
    for (const match of content.matchAll(htmlImagePattern)) add(match[2]);

    // 마크다운 이미지: ![설명](주소)
    const markdownImagePattern = /!\[[^\]]*\]\(\s*([^\s)]+(?:\([^)]*\)[^)]*)?)\s*\)/gi;
    for (const match of content.matchAll(markdownImagePattern)) add(match[1]);

    // 현재 크롤러가 저장하는 [이미지], [이미지 공지] 형식
    const markedImagePattern = /\[(?:이미지 공지|이미지)\]\s*([^\s<>'"`]+)/gi;
    for (const match of content.matchAll(markedImagePattern)) add(match[1]);

    // 마커가 사라졌거나 예전 데이터가 단독 URL만 저장한 경우
    const absoluteUrlPattern = /https?:\/\/[^\s<>'"`\])}]+/gi;
    for (const match of content.matchAll(absoluteUrlPattern)) {
        const normalized = normalizeImageUrl(match[0]);
        // 본문에 포함된 일반 원문 링크를 이미지로 오인하지 않습니다.
        if (normalized && isLikelyImageUrl(normalized)) add(match[0]);
    }

    // 강남대 이미지 엔드포인트의 루트 상대 경로
    const relativeImagePattern = /(?:^|[\s"'(])((?:\/|\.\.\/|\.\/)?comm\/cmnFile\/[^\s<>'"`\])}]+)/gi;
    for (const match of content.matchAll(relativeImagePattern)) add(match[1]);

    return urls;
};

const removeImageReferences = (content: string, imageUrls: string[]) => {
    let result = content
        .replace(/<img\b[^>]*\bsrc\s*=\s*(["']).*?\1[^>]*>/gis, "")
        .replace(/!\[[^\]]*\]\(\s*[^)]+\s*\)/g, "")
        .replace(/\[(?:이미지 공지|이미지)\]\s*[^\s<>'"`]+/gi, "");

    // 추출에 성공한 URL은 본문 텍스트에서 제거합니다.
    for (const url of imageUrls) {
        result = result.replaceAll(url, "");

        // 상대 경로 원문도 함께 제거합니다. (정규화 전 DB 값 대응)
        try {
            const parsed = new URL(url);
            result = result.replaceAll(`${parsed.pathname}${parsed.search}`, "");
        } catch {
            // 잘못된 URL은 위의 정규식 제거 결과만 사용합니다.
        }
    }

    return result.replace(/\n\s*\n\s*\n/g, "\n\n").trim();
};

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
        if (!notice) {
            setImageItems([]);
            return;
        }

        const urls = notice.content ? extractImageUrls(notice.content) : [];
        const attachmentUrl = notice.attachment_url
            ? normalizeImageUrl(notice.attachment_url)
            : null;
        // 첨부 이미지도 본문 이미지처럼 즉시 표시합니다.
        // 본문에서 이미 추출된 URL과 중복되는 경우에는 한 번만 표시합니다.
        const displayItems = [
            ...urls.map((url) => ({ url, isAttachment: false })),
            ...(attachmentUrl && !urls.includes(attachmentUrl)
                ? [{ url: attachmentUrl, isAttachment: true }]
                : []),
        ];

        if (displayItems.length > 0) {
                // 모든 이미지의 크기를 가져와서 상태 업데이트
                const newItems: ImageItem[] = [];
                let loadedCount = 0;

                displayItems.forEach(({ url, isAttachment }, index) => {
                    Image.getSize(url, (width, height) => {
                        const ratio = height / width;
                        newItems[index] = { 
                            url, 
                            height: (SCREEN_WIDTH - 32) * ratio,
                            isAttachment,
                        };
                        loadedCount++;
                        
                        if (loadedCount === displayItems.length) {
                            setImageItems(newItems.filter(item => item !== undefined));
                        }
                    }, (error) => {
                        console.warn(`이미지 크기 가져오기 실패 (${url}):`, error);
                        // 서버가 크기 조회를 차단하더라도 실제 Image 렌더링은 시도합니다.
                        newItems[index] = {
                            url,
                            height: Math.max(240, SCREEN_WIDTH * 0.75),
                            isAttachment,
                        };
                        loadedCount++;
                        if (loadedCount === displayItems.length) {
                            setImageItems(newItems.filter(item => item !== undefined));
                        }
                    });
                });
        } else {
            setImageItems([]);
        }
    }, [notice?.content, notice?.attachment_url]);

    // 이미지 태그들을 제외한 순수 텍스트 내용
    const imageUrls = notice?.content ? extractImageUrls(notice.content) : [];
    const cleanContent = notice?.content
        ? removeImageReferences(notice.content, imageUrls)
        : "";

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
                                onError={(error) => {
                                    console.warn("공지 이미지 표시 실패:", item.url, error.nativeEvent.error);
                                }}
                            />
                            {item.isAttachment && (
                                <Text className="mt-2 text-xs text-gray-400 italic">첨부파일</Text>
                            )}
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

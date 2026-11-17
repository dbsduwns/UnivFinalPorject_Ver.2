import { useState } from "react";
import { router, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react-native";
import * as ImagePicker from "expo-image-picker";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import { createCommunityPost } from "@/features/community/api/community";
import { getCommunityBoard } from "@/features/community/data/community";
import { communityQueryKeys } from "@/features/community/hooks/use-community";
import type { CommunityImageAsset } from "@/features/community/api/types";

export default function CreateCommunityPostScreen() {
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{ board?: string | string[] }>();
  const boardSlug = Array.isArray(params.board) ? params.board[0] : params.board;
  const board = getCommunityBoard(boardSlug);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [image, setImage] = useState<CommunityImageAsset | null>(null);

  const pickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "사진 권한 필요",
        "게시물에 사진을 첨부하려면 사진 접근 권한이 필요합니다.",
        [
          { text: "취소", style: "cancel" },
          { text: "설정 열기", onPress: () => { void Linking.openSettings(); } },
        ],
      );
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: false,
      quality: 1,
      selectionLimit: 1,
    });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    if (asset.fileSize && asset.fileSize > 10 * 1024 * 1024) {
      Alert.alert("파일이 너무 커요", "이미지 파일은 10MB 이하만 첨부할 수 있습니다.");
      return;
    }
    const type = asset.mimeType ?? "image/jpeg";
    if (!["image/jpeg", "image/png", "image/webp"].includes(type)) {
      Alert.alert("지원하지 않는 형식", "JPG, PNG, WEBP 이미지만 첨부할 수 있습니다.");
      return;
    }
    setImage({
      uri: asset.uri,
      name: asset.fileName ?? `community-${Date.now()}.jpg`,
      type,
    });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createCommunityPost(boardSlug!, {
        title: title.trim(),
        content: content.trim(),
        is_anonymous: isAnonymous,
      }, image),
    onSuccess: (post) => {
      void queryClient.invalidateQueries({ queryKey: communityQueryKeys.all });
      router.replace({
        pathname: "/(app)/community/post/[slug]",
        params: { slug: post.slug },
      } as never);
    },
    onError: (error) => Alert.alert("게시물 작성 실패", getAxiosErrorMessage(error)),
  });

  const canSubmit = Boolean(boardSlug && title.trim() && content.trim());

  return (
    <View className="flex-1 bg-[#F4F6F8]">
      <View
        className="bg-white border-b border-gray-200 px-4 flex-row items-end pb-4"
        style={{ paddingTop: insets.top, height: insets.top + 76 }}
      >
        <Pressable
          accessibilityLabel="작성 취소"
          onPress={() => router.back()}
          className="w-11 h-11 rounded-full items-center justify-center active:bg-gray-100"
        >
          <ArrowLeft size={24} color="#1F2937" />
        </Pressable>
        <View className="flex-1 ml-1 justify-center h-11">
          <Text className="text-xl font-extrabold text-gray-900">게시물 작성</Text>
          <Text className="text-xs text-gray-400 mt-0.5">{board?.title ?? "커뮤니티"}</Text>
        </View>
        <Pressable
          onPress={() => createMutation.mutate()}
          disabled={!canSubmit || createMutation.isPending}
          className="h-10 px-4 rounded-xl bg-[#13708D] items-center justify-center disabled:opacity-40"
        >
          {createMutation.isPending ? (
            <ActivityIndicator color="white" size="small" />
          ) : (
            <Text className="text-sm font-extrabold text-white">등록</Text>
          )}
        </Pressable>
      </View>

      <ScrollView
        className="flex-1"
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "on-drag"}
        automaticallyAdjustKeyboardInsets={Platform.OS === "ios"}
        contentContainerStyle={{ padding: 20, paddingBottom: Math.max(insets.bottom, 24) }}
      >
        <Text className="text-sm font-extrabold text-gray-700 mb-2">제목</Text>
        <KeyboardAvoidingView behavior="padding">
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="제목을 입력하세요"
            placeholderTextColor="#94A3B8"
            maxLength={255}
            className="h-14 rounded-2xl bg-white border border-gray-200 px-4 text-base text-gray-900"
          />
        </KeyboardAvoidingView>

        <Text className="text-sm font-extrabold text-gray-700 mt-6 mb-2">내용</Text>
        <KeyboardAvoidingView behavior="padding">
          <TextInput
            value={content}
            onChangeText={setContent}
            placeholder="함께 나누고 싶은 이야기를 작성해보세요."
            placeholderTextColor="#94A3B8"
            multiline
            textAlignVertical="top"
            className="min-h-[260px] rounded-2xl bg-white border border-gray-200 px-4 py-4 text-[15px] leading-6 text-gray-900"
          />
        </KeyboardAvoidingView>

        <Text className="text-sm font-extrabold text-gray-700 mt-6 mb-2">첨부파일</Text>
        <View className="rounded-2xl bg-white border border-gray-200 p-4">
          <View className="flex-row items-center">
            <Pressable
              onPress={() => void pickImage()}
              disabled={createMutation.isPending}
              className="px-4 py-3 rounded-xl bg-cyan-50 active:bg-cyan-100 disabled:opacity-50"
            >
              <Text className="text-sm font-extrabold text-[#13708D]">사진 선택</Text>
            </Pressable>
            {image && (
              <Pressable onPress={() => setImage(null)} className="ml-3 flex-1">
                <Text className="text-sm text-gray-700" numberOfLines={1}>{image.name}</Text>
                <Text className="text-xs text-gray-400 mt-1">탭해서 첨부 취소</Text>
              </Pressable>
            )}
          </View>
          <Text className="text-xs text-gray-400 mt-3">사진 파일만 첨부할 수 있어요. 최대 10MB</Text>
          <Text className="text-[11px] text-gray-400 mt-1">지원 형식: JPG, JPEG, PNG, WEBP</Text>
        </View>

        <Pressable
          onPress={() => setIsAnonymous((value) => !value)}
          className="mt-5 bg-white border border-gray-200 rounded-2xl px-4 py-4 flex-row items-center"
        >
          <View
            className={`w-11 h-6 rounded-full px-1 justify-center ${
              isAnonymous ? "bg-[#13708D] items-end" : "bg-gray-300 items-start"
            }`}
          >
            <View className="w-4 h-4 rounded-full bg-white" />
          </View>
          <View className="ml-3 flex-1">
            <Text className="text-sm font-extrabold text-gray-800">익명으로 작성</Text>
            <Text className="text-xs text-gray-400 mt-1">다른 사용자에게 작성자 이름을 숨겨요.</Text>
          </View>
        </Pressable>
      </ScrollView>
    </View>
  );
}

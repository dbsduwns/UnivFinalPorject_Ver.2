import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, ScrollView, Alert, ActivityIndicator, KeyboardAvoidingView, Platform } from "react-native";
import { X, User, BookOpen, GraduationCap, Hash } from "lucide-react-native";
import { useAuthStore } from "@/features/auth/store/auth-store";

interface ChangeUserInfoProps {
  onClose: () => void;
}

export default function ChangeUserInfo({ onClose }: ChangeUserInfoProps) {
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);

  const [name, setName] = useState(user?.name || "");
  const [department, setDepartment] = useState(user?.department || "");
  const [grade, setGrade] = useState(user?.grade?.toString() || "");
  const [studentId, setStudentId] = useState(user?.student_id || "");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert("알림", "닉네임(이름)을 입력해주세요.");
      return;
    }

    try {
      setLoading(true);
      await updateProfile({
        name,
        department,
        grade: grade ? parseInt(grade, 10) : undefined,
        student_id: studentId,
      });
      Alert.alert("성공", "회원 정보가 수정되었습니다.");
      onClose();
    } catch (error: any) {
      const message = error.response?.data?.detail || "정보 수정 중 오류가 발생했습니다.";
      Alert.alert("오류", message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-white">
      {/* 헤더 */}
      <View className="flex-row items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
        <Text className="text-xl font-bold text-gray-900">회원 정보 수정</Text>
        <TouchableOpacity onPress={onClose} className="p-2">
          <X size={24} color="#374151" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView 
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
      >
        <ScrollView className="flex-1 px-6 pt-6">
          {/* 닉네임 / 이름 */}
          <View className="mb-6">
            <View className="flex-row items-center mb-2">
              <User size={18} color="#4B5563" />
              <Text className="ml-2 font-bold text-gray-700">닉네임 (이름)</Text>
            </View>
            <TextInput
              value={name}
              onChangeText={setName}
              placeholder="이름을 입력하세요"
              className="bg-gray-50 px-4 py-4 rounded-2xl border border-gray-200 text-gray-900"
            />
          </View>

          {/* 학과 */}
          <View className="mb-6">
            <View className="flex-row items-center mb-2">
              <BookOpen size={18} color="#4B5563" />
              <Text className="ml-2 font-bold text-gray-700">학과</Text>
            </View>
            <TextInput
              value={department}
              onChangeText={setDepartment}
              placeholder="예: 소프트웨어전공"
              className="bg-gray-50 px-4 py-4 rounded-2xl border border-gray-200 text-gray-900"
            />
          </View>

          {/* 학년 */}
          <View className="mb-6">
            <View className="flex-row items-center mb-2">
              <GraduationCap size={18} color="#4B5563" />
              <Text className="ml-2 font-bold text-gray-700">학년</Text>
            </View>
            <TextInput
              value={grade}
              onChangeText={setGrade}
              placeholder="예: 3"
              keyboardType="number-pad"
              className="bg-gray-50 px-4 py-4 rounded-2xl border border-gray-200 text-gray-900"
            />
          </View>

          {/* 학번 */}
          <View className="mb-6">
            <View className="flex-row items-center mb-2">
              <Hash size={18} color="#4B5563" />
              <Text className="ml-2 font-bold text-gray-700">학번</Text>
            </View>
            <TextInput
              value={studentId}
              onChangeText={setStudentId}
              placeholder="예: 202100000"
              keyboardType="number-pad"
              className="bg-gray-50 px-4 py-4 rounded-2xl border border-gray-200 text-gray-900"
            />
            <Text className="text-gray-400 text-xs mt-2 ml-1">
              학번은 중복 등록이 불가능합니다.
            </Text>
          </View>

          <View className="h-20" />
        </ScrollView>
      </KeyboardAvoidingView>

      {/* 저장 버튼 */}
      <View className="px-6 py-6 border-t border-gray-100">
        <TouchableOpacity
          onPress={handleSave}
          disabled={loading}
          className={`py-4 rounded-2xl items-center justify-center ${loading ? 'bg-blue-300' : 'bg-blue-600'}`}
        >
          {loading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text className="text-white font-bold text-lg">저장하기</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

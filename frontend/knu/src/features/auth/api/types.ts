export type User = {
  id: number;
  email: string;
  name: string;
  department: string | null;
  grade: number | null;
  student_id: string | null;
  is_admin: boolean;
};

export type UserUpdateBody = {
  name?: string;
  department?: string;
  grade?: number;
  student_id?: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
};

export type UserLoginBody = {
  email: string;
  password: string;
};

export type UserSignupBody = {
  email: string;
  password: string;
  name: string;
  student_id: string;
};

export type PasswordVerifyRequest = {
  password: string;
}

export type PasswordChangeRequest = {
  current_password: string;
  new_password: string;
  confirm_password: string;
};

export type NotificationSettings = {
  notice_alert: boolean;
  shuttle_alert: boolean;
  cafeteria_alert: boolean;
  message_alert: boolean;
};

export interface PasswordResetRequestPayload {
  email: string;
}

export interface PasswordResetConfirmPayload {
  token: string;
  new_password: string;
  confirm_password: string;
}

export type NotificationSettingsUpdateBody = Partial<NotificationSettings>;

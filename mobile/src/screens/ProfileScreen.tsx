import React, { useState, useLayoutEffect } from "react";
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from "react-native";
import { Text, Avatar, TextInput, IconButton } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import { useAuth } from "../contexts/AuthContext";
import { useCalendarAPI } from "../services/api";
import { showSuccessToast, showErrorToast } from "../common/toast/toast-message";
import { Colors, Radius, Shadow } from "../theme";
import { useNavigation } from "@react-navigation/native";
import type { StackNavigationProp } from "@react-navigation/stack";
import type { RootStackParamList } from "../navigation/types";

export default function ProfileScreen() {
  const navigation = useNavigation<StackNavigationProp<RootStackParamList, "Profile">>();
  const { user, logout } = useAuth();

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <IconButton
          icon="chat-outline"
          iconColor="#6366F1"
          size={24}
          onPress={() => navigation.navigate("Home")}
          accessibilityLabel="Open assistant"
        />
      ),
    });
  }, [navigation]);
  const { changePassword } = useCalendarAPI();
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      showErrorToast("Please fill in all fields");
      return;
    }
    if (newPassword !== confirmPassword) {
      showErrorToast("New passwords do not match");
      return;
    }
    if (newPassword.length < 6) {
      showErrorToast("New password must be at least 6 characters");
      return;
    }
    setIsChangingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowPasswordForm(false);
      showSuccessToast("Password changed successfully");
    } catch {
      showErrorToast("Password could not be changed. Please try again.");
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleLogout = () => {
    Alert.alert("Log Out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log Out",
        style: "destructive",
        onPress: async () => {
          try {
            await logout();
          } catch {
            showErrorToast("An error occurred while logging out. Please try again.");
          }
        },
      },
    ]);
  };

  const togglePasswordForm = () => {
    setShowPasswordForm(!showPasswordForm);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  const initials = user?.name?.charAt(0)?.toUpperCase() || "U";

  return (
    <View style={styles.container}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Profile card */}
          <View style={styles.profileCard}>
            <Avatar.Text
              size={80}
              label={initials}
              style={styles.avatar}
              labelStyle={styles.avatarLabel}
            />
            <Text style={styles.userName}>{user?.name || "User"}</Text>
            {user?.email ? (
              <Text style={styles.userEmail}>{user.email}</Text>
            ) : null}
          </View>

          {/* Security section */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>SECURITY</Text>

            <View style={styles.card}>
              <TouchableOpacity style={styles.row} onPress={togglePasswordForm} activeOpacity={0.7}>
                <View style={styles.rowLeft}>
                  <View style={styles.rowIcon}>
                    <MaterialIcons name="lock-outline" size={18} color={Colors.primary} />
                  </View>
                  <Text style={styles.rowTitle}>Change Password</Text>
                </View>
                <MaterialIcons
                  name={showPasswordForm ? "keyboard-arrow-up" : "keyboard-arrow-right"}
                  size={20}
                  color={Colors.textTertiary}
                />
              </TouchableOpacity>

              {showPasswordForm && (
                <View style={styles.passwordForm}>
                  <View style={styles.formDivider} />
                  <TextInput
                    label="Current Password"
                    value={currentPassword}
                    onChangeText={setCurrentPassword}
                    mode="outlined"
                    secureTextEntry
                    style={styles.formInput}
                    outlineColor={Colors.border}
                    activeOutlineColor={Colors.primary}
                    textColor={Colors.textPrimary}
                    theme={{ roundness: Radius.md }}
                  />
                  <TextInput
                    label="New Password"
                    value={newPassword}
                    onChangeText={setNewPassword}
                    mode="outlined"
                    secureTextEntry
                    style={styles.formInput}
                    outlineColor={Colors.border}
                    activeOutlineColor={Colors.primary}
                    textColor={Colors.textPrimary}
                    theme={{ roundness: Radius.md }}
                  />
                  <TextInput
                    label="Confirm New Password"
                    value={confirmPassword}
                    onChangeText={setConfirmPassword}
                    mode="outlined"
                    secureTextEntry
                    style={styles.formInput}
                    outlineColor={Colors.border}
                    activeOutlineColor={Colors.primary}
                    textColor={Colors.textPrimary}
                    theme={{ roundness: Radius.md }}
                  />
                  <TouchableOpacity
                    style={[styles.saveBtn, isChangingPassword && styles.btnDisabled]}
                    onPress={handleChangePassword}
                    disabled={isChangingPassword}
                    activeOpacity={0.85}
                  >
                    <Text style={styles.saveBtnText}>
                      {isChangingPassword ? "Saving..." : "Save Password"}
                    </Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          </View>

          {/* Account section */}
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>ACCOUNT</Text>
            <View style={styles.card}>
              <TouchableOpacity style={styles.row} onPress={handleLogout} activeOpacity={0.7}>
                <View style={styles.rowLeft}>
                  <View style={[styles.rowIcon, styles.rowIconDanger]}>
                    <MaterialIcons name="logout" size={18} color={Colors.error} />
                  </View>
                  <Text style={[styles.rowTitle, styles.rowTitleDanger]}>Log Out</Text>
                </View>
                <MaterialIcons name="keyboard-arrow-right" size={20} color={Colors.textTertiary} />
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 48,
  },
  // Profile card
  profileCard: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.xl,
    alignItems: "center",
    paddingVertical: 32,
    paddingHorizontal: 20,
    marginBottom: 28,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.sm,
  },
  avatar: {
    backgroundColor: Colors.primary,
    marginBottom: 16,
  },
  avatarLabel: {
    color: Colors.surface,
    fontWeight: "700",
    fontSize: 32,
  },
  userName: {
    fontSize: 20,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  // Sections
  section: {
    marginBottom: 24,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: "600",
    color: Colors.textTertiary,
    letterSpacing: 1,
    marginBottom: 8,
    marginLeft: 4,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: "hidden",
    ...Shadow.sm,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 16,
  },
  rowLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  rowIcon: {
    width: 34,
    height: 34,
    borderRadius: Radius.sm,
    backgroundColor: Colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  rowIconDanger: {
    backgroundColor: "#FEF2F2",
  },
  rowTitle: {
    fontSize: 15,
    fontWeight: "500",
    color: Colors.textPrimary,
  },
  rowTitleDanger: {
    color: Colors.error,
  },
  // Password form
  passwordForm: {
    paddingHorizontal: 16,
    paddingBottom: 16,
    gap: 12,
  },
  formDivider: {
    height: 1,
    backgroundColor: Colors.border,
    marginBottom: 4,
  },
  formInput: {
    backgroundColor: Colors.surface,
  },
  saveBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 4,
  },
  btnDisabled: {
    opacity: 0.7,
  },
  saveBtnText: {
    color: Colors.surface,
    fontSize: 15,
    fontWeight: "600",
  },
});

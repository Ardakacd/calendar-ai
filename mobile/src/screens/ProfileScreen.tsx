import React, { useState, useEffect } from "react";
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Text, Button, Avatar, TextInput } from "react-native-paper";
import { LinearGradient } from "expo-linear-gradient";
import { useAuth } from "../contexts/AuthContext";
import { useCalendarAPI } from "../services/api";
import {
  showSuccessToast,
  showErrorToast,
} from "../common/toast/toast-message";

export default function ProfileScreen() {
  const { user, logout } = useAuth();
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
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowPasswordForm(false);
      showSuccessToast("Password changed successfully");
    } catch (error) {
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
          } catch (error) {
            showErrorToast(
              "An error occurred while logging out. Please try again later."
            );
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

  return (
    <LinearGradient colors={["#667eea", "#764ba2"]} style={styles.container}>
      <KeyboardAvoidingView
        style={styles.content}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.profileSection}>
            <View style={styles.avatarContainer}>
              <Avatar.Text
                size={100}
                label={user?.name?.charAt(0)?.toUpperCase() || "U"}
                style={styles.profileAvatar}
              />
              <Text style={styles.userName}>{user?.name || "User"}</Text>
            </View>
          </View>

          <View style={styles.actionSection}>
            <Text style={styles.sectionTitle}>Security</Text>

            <Button
              mode="contained"
              onPress={togglePasswordForm}
              style={styles.actionButton}
              buttonColor="rgba(255, 255, 255, 0.2)"
              labelStyle={styles.actionButtonLabel}
              icon="lock-outline"
              contentStyle={styles.buttonContent}
            >
              {showPasswordForm ? "Cancel" : "Change Password"}
            </Button>

            {showPasswordForm && (
              <View style={styles.passwordForm}>
                <TextInput
                  label="Current Password"
                  value={currentPassword}
                  onChangeText={setCurrentPassword}
                  mode="flat"
                  secureTextEntry
                  style={styles.passwordInput}
                  textColor="white"
                  theme={{
                    colors: {
                      primary: "white",
                      onSurface: "white",
                      onSurfaceVariant: "rgba(255, 255, 255, 0.7)",
                      surface: "rgba(255, 255, 255, 0.15)",
                      backdrop: "transparent",
                    },
                  }}
                />

                <TextInput
                  label="New Password"
                  value={newPassword}
                  onChangeText={setNewPassword}
                  mode="flat"
                  secureTextEntry
                  style={styles.passwordInput}
                  textColor="white"
                  theme={{
                    colors: {
                      primary: "white",
                      onSurface: "white",
                      onSurfaceVariant: "rgba(255, 255, 255, 0.7)",
                      surface: "rgba(255, 255, 255, 0.15)",
                      backdrop: "transparent",
                    },
                  }}
                />

                <TextInput
                  label="Password Confirmation"
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  mode="flat"
                  secureTextEntry
                  style={styles.passwordInput}
                  textColor="white"
                  theme={{
                    colors: {
                      primary: "white",
                      onSurface: "white",
                      onSurfaceVariant: "rgba(255, 255, 255, 0.7)",
                      surface: "rgba(255, 255, 255, 0.15)",
                      backdrop: "transparent",
                    },
                  }}
                />

                <Button
                  mode="contained"
                  onPress={handleChangePassword}
                  loading={isChangingPassword}
                  disabled={isChangingPassword}
                  style={styles.savePasswordButton}
                  buttonColor="white"
                  textColor="#667eea"
                  contentStyle={styles.buttonContent}
                >
                  Save Password
                </Button>
              </View>
            )}
          </View>

          {/* Logout Section */}
          <View style={styles.actionSection}>
            <Text style={styles.sectionTitle}>Account</Text>

            <Button
              mode="contained"
              onPress={handleLogout}
              style={styles.logoutButton}
              buttonColor="rgba(231, 76, 60, 0.8)"
              labelStyle={styles.actionButtonLabel}
              icon="logout"
              contentStyle={styles.buttonContent}
            >
              Log Out
            </Button>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "bold",
    color: "white",
  },
  content: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    color: "white",
    fontSize: 16,
  },
  profileSection: {
    alignItems: "center",
    marginBottom: 20,
  },
  avatarContainer: {
    alignItems: "center",
    marginBottom: 10,
  },
  profileAvatar: {
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    borderRadius: 50,
  },
  userName: {
    fontSize: 20,
    fontWeight: "bold",
    color: "white",
    marginTop: 10,
  },
  actionSection: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "bold",
    color: "white",
    marginBottom: 15,
  },
  actionButton: {
    borderColor: "rgba(255, 255, 255, 0.5)",
    borderWidth: 1,
    borderRadius: 12,
  },
  actionButtonLabel: {
    color: "white",
  },
  buttonContent: {
    paddingVertical: 8,
  },
  passwordForm: {
    marginTop: 15,
  },
  passwordInput: {
    marginBottom: 16,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 8,
    overflow: "hidden",
  },
  savePasswordButton: {
    marginTop: 10,
    borderRadius: 12,
  },
  logoutButton: {
    width: "100%",
    borderRadius: 12,
  },
});

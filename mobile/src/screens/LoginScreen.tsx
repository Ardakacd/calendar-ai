import React, { useState } from "react";
import {
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  View,
  TouchableOpacity,
} from "react-native";
import { TextInput, Text } from "react-native-paper";
import { MaterialIcons } from "@expo/vector-icons";
import { useAuth } from "../contexts/AuthContext";
import { showErrorToast } from "../common/toast/toast-message";
import { Colors, Radius, Shadow } from "../theme";

interface LoginScreenProps {
  setShowSignup: (show: boolean) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ setShowSignup }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async () => {
    if (!email || !password) {
      showErrorToast("Please fill in all fields");
      return;
    }
    setIsLoading(true);
    try {
      await login(email, password);
    } catch (error: any) {
      showErrorToast(error.response?.data?.detail || "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Logo */}
        <View style={styles.logoSection}>
          <View style={styles.logoBox}>
            <MaterialIcons name="calendar-today" size={32} color={Colors.surface} />
          </View>
          <Text style={styles.appName}>Calendar AI</Text>
          <Text style={styles.tagline}>Smart scheduling, simplified</Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <TextInput
            label="Email"
            value={email}
            onChangeText={setEmail}
            mode="outlined"
            style={styles.input}
            keyboardType="email-address"
            autoCapitalize="none"
            left={<TextInput.Icon icon="email-outline" color={Colors.textTertiary} />}
            outlineColor={Colors.border}
            activeOutlineColor={Colors.primary}
            textColor={Colors.textPrimary}
            theme={{ roundness: Radius.md }}
          />

          <TextInput
            label="Password"
            value={password}
            onChangeText={setPassword}
            mode="outlined"
            style={styles.input}
            secureTextEntry
            left={<TextInput.Icon icon="lock-outline" color={Colors.textTertiary} />}
            outlineColor={Colors.border}
            activeOutlineColor={Colors.primary}
            textColor={Colors.textPrimary}
            theme={{ roundness: Radius.md }}
          />

          <TouchableOpacity
            style={[styles.signInBtn, isLoading && styles.signInBtnDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
            activeOpacity={0.85}
          >
            <Text style={styles.signInBtnText}>
              {isLoading ? "Signing in..." : "Sign In"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Switch to signup */}
        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Don't have an account? </Text>
          <TouchableOpacity onPress={() => setShowSignup(true)}>
            <Text style={styles.switchLink}>Sign Up</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 28,
    paddingVertical: 48,
  },
  // Logo section
  logoSection: {
    alignItems: "center",
    marginBottom: 48,
  },
  logoBox: {
    width: 72,
    height: 72,
    borderRadius: Radius.xl,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 20,
    ...Shadow.md,
  },
  appName: {
    fontSize: 28,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 6,
    letterSpacing: -0.5,
  },
  tagline: {
    fontSize: 15,
    color: Colors.textSecondary,
  },
  // Form
  form: {
    gap: 16,
    marginBottom: 32,
  },
  input: {
    backgroundColor: Colors.surface,
  },
  signInBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 4,
    ...Shadow.sm,
  },
  signInBtnDisabled: {
    opacity: 0.7,
  },
  signInBtnText: {
    color: Colors.surface,
    fontSize: 16,
    fontWeight: "600",
    letterSpacing: 0.2,
  },
  // Switch
  switchRow: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  switchText: {
    fontSize: 14,
    color: Colors.textSecondary,
  },
  switchLink: {
    fontSize: 14,
    color: Colors.primary,
    fontWeight: "600",
  },
});

export default LoginScreen;

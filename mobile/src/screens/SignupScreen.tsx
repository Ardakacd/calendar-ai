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

interface SignupScreenProps {
  setShowSignup: (show: boolean) => void;
}

const SignupScreen: React.FC<SignupScreenProps> = ({ setShowSignup }) => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();

  const handleSignup = async () => {
    if (!name || !email || !password) {
      showErrorToast("Please fill in all fields");
      return;
    }
    setIsLoading(true);
    try {
      await register(name, email, password);
    } catch (error: any) {
      showErrorToast(error.response?.data?.detail || "An error occurred during registration");
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
          <Text style={styles.appName}>Create Account</Text>
          <Text style={styles.tagline}>Join to manage your schedule</Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <TextInput
            label="Name"
            value={name}
            onChangeText={setName}
            mode="outlined"
            style={styles.input}
            autoCapitalize="words"
            left={<TextInput.Icon icon="account-outline" color={Colors.textTertiary} />}
            outlineColor={Colors.border}
            activeOutlineColor={Colors.primary}
            textColor={Colors.textPrimary}
            theme={{ roundness: Radius.md }}
          />

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
            style={[styles.signUpBtn, isLoading && styles.btnDisabled]}
            onPress={handleSignup}
            disabled={isLoading}
            activeOpacity={0.85}
          >
            <Text style={styles.signUpBtnText}>
              {isLoading ? "Creating account..." : "Create Account"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Switch to login */}
        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Already have an account? </Text>
          <TouchableOpacity onPress={() => setShowSignup(false)}>
            <Text style={styles.switchLink}>Sign In</Text>
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
  form: {
    gap: 16,
    marginBottom: 32,
  },
  input: {
    backgroundColor: Colors.surface,
  },
  signUpBtn: {
    backgroundColor: Colors.primary,
    borderRadius: Radius.md,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 4,
    ...Shadow.sm,
  },
  btnDisabled: {
    opacity: 0.7,
  },
  signUpBtnText: {
    color: Colors.surface,
    fontSize: 16,
    fontWeight: "600",
    letterSpacing: 0.2,
  },
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

export default SignupScreen;

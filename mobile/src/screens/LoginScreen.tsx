import React, { useState } from "react";
import {
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  View,
} from "react-native";
import { TextInput, Button, Card, Title, Paragraph } from "react-native-paper";
import { useAuth } from "../contexts/AuthContext";
import { showErrorToast } from "../common/toast/toast-message";

interface LoginScreenProps {
  setShowSignup: (show: boolean) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ setShowSignup }) => {
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
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
      // No navigation - user stays on login screen with their data
    } finally {
      setIsLoading(false);
    }
  };

  const handleNavigateToSignup = () => {
    setShowSignup(true);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.header}>
          <Title style={styles.title}>Welcome Back</Title>
          <Paragraph style={styles.subtitle}>
            Sign in to your Calen account
          </Paragraph>
        </View>

        <Card style={styles.card}>
          <Card.Content>
            <TextInput
              label="E-Mail"
              value={email}
              onChangeText={setEmail}
              mode="outlined"
              style={styles.input}
              keyboardType="email-address"
              autoCapitalize="none"
              left={<TextInput.Icon icon="email" />}
            />

            <TextInput
              label="Password"
              value={password}
              onChangeText={setPassword}
              mode="outlined"
              style={styles.input}
              secureTextEntry
              left={<TextInput.Icon icon="lock" />}
            />

            <Button
              mode="contained"
              onPress={handleLogin}
              style={styles.button}
              loading={isLoading}
              disabled={isLoading}
              contentStyle={styles.buttonContent}
            >
              Sign In
            </Button>

            <Button
              mode="text"
              onPress={handleNavigateToSignup}
              style={styles.switchButton}
            >
              Don't have an account? Sign Up
            </Button>
          </Card.Content>
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f8f9fa",
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 24,
  },
  header: {
    alignItems: "center",
    marginBottom: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: "bold",
    color: "#1a237e",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#666",
    textAlign: "center",
    lineHeight: 22,
  },
  card: {
    borderRadius: 16,
    elevation: 8,
    shadowColor: "#000",
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  input: {
    marginBottom: 20,
    backgroundColor: "#fff",
  },
  button: {
    marginTop: 8,
    marginBottom: 20,
    borderRadius: 12,
    elevation: 4,
  },
  buttonContent: {
    paddingVertical: 8,
  },
  switchButton: {
    marginTop: 8,
  },
});

export default LoginScreen;

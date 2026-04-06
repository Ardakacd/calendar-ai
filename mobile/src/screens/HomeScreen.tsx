import React, { useState, useRef, useEffect } from "react";
import {
  View,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  TextInput,
  Platform,
  TouchableOpacity,
  Alert,
} from "react-native";
import { Text, Avatar, IconButton } from "react-native-paper";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation } from "@react-navigation/native";
import MicButton from "../components/MicButton";
import ListComponent from "../components/ListComponent";
import ConflictComponent, { ConflictSuggestion } from "../components/ConflictComponent";
import { useCalendarAPI } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { Event } from "../models/event";

// Animated thinking dots component
const ThinkingDots = () => {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => {
        if (prev === "...") return "";
        if (prev === "..") return "...";
        if (prev === ".") return "..";
        return ".";
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <Text
      style={{
        fontSize: 16,
        lineHeight: 22,
        color: "rgba(255, 255, 255, 0.9)",
      }}
    >
      {dots}
    </Text>
  );
};

interface ChatMessage {
  id: string;
  type: "user" | "ai";
  content: string;
  timestamp: Date;
  events?: Event[];
  hasConflict?: boolean;
  suggestions?: ConflictSuggestion[];
}

export default function HomeScreen() {
  const navigation = useNavigation();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: Date.now().toString(),
      type: "ai",
      content: "Hello, I am your AI calendar assistant. How can I help you?",
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const { transcribeAudio, processText, resetMemory, deleteAllEvents } = useCalendarAPI();
  const { user } = useAuth();
  const scrollViewRef = useRef<ScrollView>(null);
  const inputRef = useRef<TextInput>(null);

  const handleClearMemory = async () => {
    try {
      await resetMemory();
      setMessages([
        {
          id: Date.now().toString(),
          type: "ai",
          content: "Conversation cleared. How can I help you?",
          timestamp: new Date(),
        },
      ]);
    } catch {
      // silently ignore
    }
  };

  const handleDeleteAllEvents = () => {
    Alert.alert(
      "Delete All Events",
      "This will permanently delete all your calendar events. Are you sure?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete All",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteAllEvents();
              await resetMemory();
              setMessages([
                {
                  id: Date.now().toString(),
                  type: "ai",
                  content: "All events deleted. How can I help you?",
                  timestamp: new Date(),
                },
              ]);
            } catch {
              // silently ignore
            }
          },
        },
      ]
    );
  };

  const addMessage = (
    type: "user" | "ai",
    content: string,
    events?: Event[],
    hasConflict?: boolean,
    suggestions?: ConflictSuggestion[]
  ) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type,
      content: content ? content.trim() : "",
      timestamp: new Date(),
      events,
      hasConflict,
      suggestions,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = inputText.trim();
    addMessage("user", userMessage);
    setInputText("");
    scrollToBottom();
    await handleProcessText(userMessage);

    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  const handleProcessText = async (text: string) => {
    setIsThinking(true);
    try {
      const response = await processText(text);

      const message =
        typeof response === "string"
          ? response
          : response?.message || "Done.";

      const events: Event[] | undefined =
        response?.events?.length > 0 && !response?.needs_clarification
          ? response.events
          : undefined;
      const hasConflict: boolean = response?.has_conflict === true;
      const suggestions: ConflictSuggestion[] = response?.suggestions ?? [];

      addMessage("ai", message, events, hasConflict, suggestions);
      scrollToBottom();
    } catch (error) {
      addMessage("ai", "Sorry, I couldn't process your command. Please try again.");
      scrollToBottom();
    } finally {
      setIsThinking(false);
    }
  };

  const handleVoiceCommand = async (audioUri: string) => {
    setIsProcessing(true);
    try {
      const response = await transcribeAudio(audioUri);
      const userMessage = response.message || "Voice command processed";
      addMessage("user", userMessage);
      scrollToBottom();
      await handleProcessText(userMessage);
    } catch (error) {
      addMessage("ai", "Sorry, I couldn't process your voice command. Please try again.");
      scrollToBottom();
    } finally {
      setIsProcessing(false);
    }
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === "user";

    return (
      <View
        key={message.id}
        style={[
          styles.messageContainer,
          isUser ? styles.userMessage : styles.aiMessage,
        ]}
      >
        {message.events && message.events.length > 0 ? (
          <View style={styles.eventsContainer}>
            <ListComponent events={message.events} />
          </View>
        ) : message.hasConflict ? (
          <View style={[styles.messageBubble, styles.aiBubble, styles.eventsContainer]}>
            <ConflictComponent
              conflictMessage={message.content}
              suggestions={message.suggestions ?? []}
            />
          </View>
        ) : (
          <View
            style={[
              styles.messageBubble,
              isUser ? styles.userBubble : styles.aiBubble,
            ]}
          >
            <Text
              style={[
                styles.messageText,
                isUser ? styles.userMessageText : styles.aiMessageText,
              ]}
            >
              {message.content}
            </Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <LinearGradient colors={["#667eea", "#764ba2"]} style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.navigate("Profile" as never)}
        >
          <View style={styles.userInfo}>
            <Avatar.Text
              size={40}
              label={user?.name?.charAt(0)?.toUpperCase() || "U"}
              style={styles.avatar}
            />
            <View style={styles.userText}>
              <Text style={styles.userName}>{user?.name || "User"}</Text>
            </View>
          </View>
        </TouchableOpacity>
        <IconButton
          icon="trash-can-outline"
          iconColor="white"
          size={24}
          onPress={handleDeleteAllEvents}
          style={styles.logoutButton}
        />
        <IconButton
          icon="delete-sweep"
          iconColor="white"
          size={24}
          onPress={handleClearMemory}
          style={styles.logoutButton}
        />
        <IconButton
          icon="calendar"
          iconColor="white"
          size={24}
          onPress={() => navigation.navigate("Calendar" as never)}
          style={styles.logoutButton}
        />
      </View>

      <KeyboardAvoidingView
        style={styles.chatContainer}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}
          {isThinking && (
            <View style={[styles.messageContainer, styles.aiMessage]}>
              <View style={[styles.messageBubble, styles.aiBubble]}>
                <ThinkingDots />
              </View>
            </View>
          )}
        </ScrollView>

        <View style={styles.inputContainer}>
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            placeholder="Write your command..."
            placeholderTextColor="rgba(255, 255, 255, 0.6)"
            onSubmitEditing={handleSendMessage}
            returnKeyType="send"
            style={styles.textInput}
            contextMenuHidden={false}
            selectTextOnFocus={false}
            autoCorrect={false}
            autoCapitalize="none"
            ref={inputRef}
          />
          <View>
            {inputText.trim() ? (
              <IconButton
                icon="send"
                iconColor="white"
                size={20}
                onPress={handleSendMessage}
                style={styles.sendButton}
              />
            ) : (
              <MicButton
                onRecordingComplete={handleVoiceCommand}
                isProcessing={isProcessing}
              />
            )}
          </View>
        </View>
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
    paddingTop: 80,
    paddingBottom: 20,
  },
  userInfo: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },
  avatar: {
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    marginRight: 12,
  },
  userText: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: "bold",
    color: "white",
  },
  logoutButton: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    marginLeft: 10,
  },
  chatContainer: {
    flex: 1,
    borderTopWidth: 3,
    borderTopColor: "rgba(255, 255, 255, 0.1)",
    paddingTop: 12,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 8,
    paddingBottom: 20,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 32,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderTopWidth: 1,
    borderTopColor: "rgba(255, 255, 255, 0.1)",
    gap: 8,
  },
  textInput: {
    flex: 1,
    backgroundColor: "rgba(255, 255, 255, 0.15)",
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 18,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
    color: "white",
    borderWidth: 0,
    borderColor: "transparent",
  },
  sendButton: {
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    borderRadius: 20,
    width: 40,
    height: 40,
    margin: 0,
    padding: 0,
  },
  messageContainer: {
    marginVertical: 8,
    paddingHorizontal: 8,
  },
  eventsContainer: {
    alignSelf: "stretch",
  },
  userMessage: {
    alignItems: "flex-end",
  },
  aiMessage: {
    alignItems: "flex-start",
  },
  messageBubble: {
    maxWidth: "90%",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: "#667eea",
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: "rgba(255, 255, 255, 0.15)",
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: "white",
  },
  aiMessageText: {
    color: "rgba(255, 255, 255, 0.9)",
  },
});

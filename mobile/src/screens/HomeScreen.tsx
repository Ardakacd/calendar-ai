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
import { useNavigation } from "@react-navigation/native";
import MicButton from "../components/MicButton";
import ListComponent from "../components/ListComponent";
import ConflictComponent, { ConflictSuggestion } from "../components/ConflictComponent";
import { useCalendarAPI } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { Event } from "../models/event";
import { Colors, Radius, Shadow } from "../theme";

const ThinkingDots = () => {
  const [count, setCount] = useState(1);
  useEffect(() => {
    const interval = setInterval(() => setCount((c) => (c === 3 ? 1 : c + 1)), 450);
    return () => clearInterval(interval);
  }, []);
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 5, paddingVertical: 4 }}>
      {[1, 2, 3].map((i) => (
        <View
          key={i}
          style={{
            width: 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: i <= count ? Colors.primary : Colors.border,
          }}
        />
      ))}
    </View>
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
      content: "Hello! I'm your AI calendar assistant. How can I help you today?",
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
        typeof response === "string" ? response : response?.message || "Done.";
      const events: Event[] | undefined =
        response?.events?.length > 0 && !response?.needs_clarification
          ? response.events
          : undefined;
      const hasConflict: boolean = response?.has_conflict === true;
      const suggestions: ConflictSuggestion[] = response?.suggestions ?? [];
      addMessage("ai", message, events, hasConflict, suggestions);
      scrollToBottom();
    } catch {
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
    } catch {
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
        style={[styles.messageRow, isUser ? styles.messageRowUser : styles.messageRowAi]}
      >
        {message.events && message.events.length > 0 ? (
          <View style={styles.fullWidthMessage}>
            <ListComponent events={message.events} />
          </View>
        ) : message.hasConflict ? (
          <View style={[styles.aiBubble, styles.fullWidthMessage]}>
            <ConflictComponent
              conflictMessage={message.content}
              suggestions={message.suggestions ?? []}
            />
          </View>
        ) : (
          <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
            <Text style={[styles.messageText, isUser ? styles.userText : styles.aiText]}>
              {message.content}
            </Text>
          </View>
        )}
      </View>
    );
  };

  const initials = user?.name?.charAt(0)?.toUpperCase() || "U";

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.navigate("Profile" as never)}>
          <View style={styles.userInfo}>
            <Avatar.Text size={38} label={initials} style={styles.avatar} labelStyle={styles.avatarLabel} />
            <View>
              <Text style={styles.greeting}>Good day,</Text>
              <Text style={styles.userName}>{user?.name || "User"}</Text>
            </View>
          </View>
        </TouchableOpacity>
        <View style={styles.headerActions}>
          <IconButton
            icon="trash-can-outline"
            iconColor={Colors.textSecondary}
            size={20}
            onPress={handleDeleteAllEvents}
            style={styles.headerBtn}
          />
          <IconButton
            icon="delete-sweep"
            iconColor={Colors.textSecondary}
            size={20}
            onPress={handleClearMemory}
            style={styles.headerBtn}
          />
          <IconButton
            icon="calendar-month-outline"
            iconColor={Colors.primary}
            size={20}
            onPress={() => navigation.navigate("Calendar" as never)}
            style={[styles.headerBtn, styles.headerBtnPrimary]}
          />
        </View>
      </View>

      {/* Chat */}
      <KeyboardAvoidingView
        style={styles.chatWrapper}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesList}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}
          {isThinking && (
            <View style={[styles.messageRow, styles.messageRowAi]}>
              <View style={styles.aiBubble}>
                <ThinkingDots />
              </View>
            </View>
          )}
        </ScrollView>

        {/* Input bar */}
        <View style={styles.inputBar}>
          <TextInput
            ref={inputRef}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Message your assistant..."
            placeholderTextColor={Colors.textTertiary}
            onSubmitEditing={handleSendMessage}
            returnKeyType="send"
            style={styles.input}
            autoCorrect={false}
            autoCapitalize="none"
          />
          {inputText.trim() ? (
            <TouchableOpacity onPress={handleSendMessage} style={styles.sendBtn}>
              <Text style={styles.sendBtnText}>↑</Text>
            </TouchableOpacity>
          ) : (
            <MicButton onRecordingComplete={handleVoiceCommand} isProcessing={isProcessing} />
          )}
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.surface,
  },
  // Header
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    ...Shadow.sm,
  },
  userInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  avatar: {
    backgroundColor: Colors.primary,
  },
  avatarLabel: {
    color: Colors.surface,
    fontWeight: "700",
  },
  greeting: {
    fontSize: 12,
    color: Colors.textTertiary,
    fontWeight: "400",
  },
  userName: {
    fontSize: 16,
    fontWeight: "600",
    color: Colors.textPrimary,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  headerBtn: {
    backgroundColor: Colors.borderLight,
    borderRadius: Radius.md,
    margin: 0,
    width: 36,
    height: 36,
  },
  headerBtnPrimary: {
    backgroundColor: Colors.primaryLight,
  },
  // Chat
  chatWrapper: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  messagesList: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 16,
    gap: 8,
  },
  messageRow: {
    flexDirection: "row",
    marginVertical: 2,
  },
  messageRowUser: {
    justifyContent: "flex-end",
  },
  messageRowAi: {
    justifyContent: "flex-start",
  },
  fullWidthMessage: {
    flex: 1,
  },
  bubble: {
    maxWidth: "80%",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: Radius.xl,
  },
  userBubble: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
    borderBottomLeftRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: Radius.xl,
    ...Shadow.sm,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userText: {
    color: Colors.surface,
  },
  aiText: {
    color: Colors.textPrimary,
  },
  // Input bar
  inputBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 36,
    backgroundColor: Colors.surface,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    gap: 10,
  },
  input: {
    flex: 1,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.full,
    paddingHorizontal: 18,
    paddingVertical: 11,
    fontSize: 15,
    color: Colors.textPrimary,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnText: {
    color: Colors.surface,
    fontSize: 18,
    fontWeight: "700",
    marginTop: -2,
  },
});

import React, { useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  TextInput,
} from 'react-native';
import { Text, Button, Card, Avatar, IconButton } from 'react-native-paper';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';

import MicButton from '../components/MicButton';
import ConfirmationModal from '../components/ConfirmationModal';
import { useCalendarAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { EventConfirmationData } from '../models/event';

interface ChatMessage {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  eventData?: EventConfirmationData;
}

export default function HomeScreen() {
  const navigation = useNavigation();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: Date.now().toString(),
      type: 'ai',
      content: 'Hello, how can I help you today?  ',
      timestamp: new Date(),
      eventData: undefined,
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [confirmationData, setConfirmationData] = useState<{
    action: 'create' | 'update' | 'delete';
    eventData: EventConfirmationData;
  } | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const { transcribeAudio, confirmAction } = useCalendarAPI();
  const { user, logout } = useAuth();
  const scrollViewRef = useRef<ScrollView>(null);
  const inputRef = useRef<TextInput>(null);

  const addMessage = (type: 'user' | 'ai', content: string, eventData?: EventConfirmationData) => {
    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      type,
      content,
      timestamp: new Date(),
      eventData,
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage = inputText.trim();
    addMessage('user', userMessage);
    setInputText('');
    scrollToBottom();

    // Maintain focus on the input
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);

    // await processCommand(userMessage);
  };

  const handleVoiceCommand = async (audioUri: string) => {
    setIsProcessing(true);

    try {
      // const response = await transcribeAudio(audioUri);
      // const userMessage = response.message || 'Voice command processed';
      //addMessage('user', userMessage);
      // scrollToBottom();

      //await processCommand(userMessage);
    } catch (error) {
      console.error('Error processing voice command:', error);
      addMessage('ai', 'Sorry, I couldn\'t process your voice command. Please try again.');
      scrollToBottom();
    } finally {
      setIsProcessing(false);
    }
  };

  const processCommand = async (command: string) => {
    try {
      const response = await transcribeAudio(''); // This will need to be updated to handle text commands

      if (response.requires_confirmation && response.confirmation_data) {
        addMessage('ai', 'Do you confirm an event with the following attributes:', response.confirmation_data);
        setConfirmationData({
          action: response.action as 'create' | 'update' | 'delete',
          eventData: response.confirmation_data,
        });
        setShowConfirmationModal(true);
      } else {
        addMessage('ai', response.message || 'Command processed successfully.');
      }

      scrollToBottom();
    } catch (error) {
      console.error('Error processing command:', error);
      addMessage('ai', 'Sorry, I couldn\'t process your command. Please try again.');
      scrollToBottom();
    }
  };

  const handleConfirmAction = async (eventData: EventConfirmationData) => {
    if (!confirmationData) return;

    setIsConfirming(true);
    try {
      const result = await confirmAction({
        action: confirmationData.action,
        event_data: eventData,
      });

      addMessage('ai', result.message);
      setShowConfirmationModal(false);
      setConfirmationData(null);
      scrollToBottom();

    } catch (error) {
      console.error('Error confirming action:', error);
      addMessage('ai', 'Failed to confirm action. Please try again.');
      scrollToBottom();
    } finally {
      setIsConfirming(false);
    }
  };

  const handleDismissModal = () => {
    setShowConfirmationModal(false);
    setConfirmationData(null);
  };

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            try {
              await logout();
            } catch (error) {
              console.error('Logout error:', error);
            }
          },
        },
      ]
    );
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.type === 'user';

    return (
      <View key={message.id} style={[styles.messageContainer, isUser ? styles.userMessage : styles.aiMessage]}>
        <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.aiBubble]}>
          <Text style={[styles.messageText, isUser ? styles.userMessageText : styles.aiMessageText]}>
            {message.content}
          </Text>

          {message.eventData && (
            <Card style={styles.eventCard}>
              <Card.Content>
                <Text style={styles.eventTitle}>Event Details:</Text>
                <Text style={styles.eventDetail}>Title: {message.eventData.title}</Text>
                <Text style={styles.eventDetail}>Date: {new Date(message.eventData.startDate).toLocaleString()}</Text>
                {message.eventData.duration && (
                  <Text style={styles.eventDetail}>Duration: {message.eventData.duration} minutes</Text>
                )}
                {message.eventData.location && (
                  <Text style={styles.eventDetail}>Location: {message.eventData.location}</Text>
                )}
              </Card.Content>
            </Card>
          )}
        </View>
      </View>
    );
  };

  return (
    <LinearGradient
      colors={['#667eea', '#764ba2']}
      style={styles.container}
    >
      <View style={styles.header}>
        <View style={styles.userInfo}>
          <Avatar.Text
            size={40}
            label={user?.name?.charAt(0)?.toUpperCase() || 'U'}
            style={styles.avatar}
          />
          <View style={styles.userText}>
            <Text style={styles.userName}>{user?.name || 'User'}</Text>
          </View>
        </View>
        <IconButton
          icon="calendar"
          iconColor="white"
          size={24}
          onPress={() => navigation.navigate('Calendar' as never)}
          style={styles.logoutButton}
        />
      </View>

      <KeyboardAvoidingView
        style={styles.chatContainer}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(renderMessage)}
        </ScrollView>

        <View style={styles.inputContainer}>
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            placeholder="Type your command..."
            placeholderTextColor="rgba(255, 255, 255, 0.6)"
            onSubmitEditing={handleSendMessage}
            returnKeyType="send"
            style={styles.textInput}
            contextMenuHidden={true}
            selectTextOnFocus={false}
            autoCorrect={false}
            autoCapitalize="none"
            editable={true}
            pointerEvents="auto"
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

      {confirmationData && (
        <ConfirmationModal
          visible={showConfirmationModal}
          onDismiss={handleDismissModal}
          action={confirmationData.action}
          eventData={confirmationData.eventData}
          onConfirm={handleConfirmAction}
          isLoading={isConfirming}
        />
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 80,
    paddingBottom: 20,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatar: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    marginRight: 12,
  },
  userText: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: 'white',
  },
  logoutButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginLeft: 10,
  },
  chatContainer: {
    flex: 1,
    borderTopWidth:3,
    borderTopColor:'rgba(255, 255, 255, 0.1)',
    paddingTop: 12
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop:20,
    paddingBottom: 28,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
    gap: 8
  },
  textInput: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 18,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
    color: 'white',
    borderWidth: 0,
    borderColor: 'transparent',
  },
  inputButtons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sendButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    width: 40,
    height: 40,
    margin: 0,
    padding:0
  },
  messageContainer: {
    marginVertical: 8,
    paddingHorizontal: 8,
  },
  userMessage: {
    alignItems: 'flex-end',
  },
  aiMessage: {
    alignItems: 'flex-start',
  },
  messageBubble: {
    maxWidth: '80%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  userBubble: {
    backgroundColor: '#667eea',
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderBottomLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userMessageText: {
    color: 'white',
  },
  aiMessageText: {
    color: 'rgba(255, 255, 255, 0.9)',
  },
  eventCard: {
    marginTop: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: 'white',
  },
  eventDetail: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 4,
  },
}); 